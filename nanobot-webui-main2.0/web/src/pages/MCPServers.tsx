import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useMCPServers,
  useMCPRuntime,
  useToggleMCPServer,
  useCreateMCPServer,
  useUpdateMCPServer,
  useDeleteMCPServer,
  type MCPServer,
  type MCPToolInfo,
} from "../hooks/useMCP";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import { Badge } from "../components/ui/badge";
import { ConfirmDialog } from "../components/shared/ConfirmDialog";
import { Skeleton } from "../components/ui/skeleton";
import { Plus, Pencil, Trash2, Terminal, Globe, Upload, Wrench, Power, Loader2 } from "lucide-react";
import { toast } from "sonner";

type McpType = "stdio" | "http" | "sse";
type DialogMode = "manual" | "json";

// ── JSON import helpers ──────────────────────────────────────────────────────

interface ParsedServer {
  name: string;
  type: McpType;
  url: string;
  headers: Record<string, string>;
  command: string;
  args: string[];
  env: Record<string, string>;
  timeout: number;
}

function inferType(entry: Record<string, unknown>): McpType {
  if (entry.type === "stdio" || entry.command) return "stdio";
  if (entry.type === "sse") return "sse";
  if (entry.type === "http" || entry.type === "streamable-http") return "http";
  // infer from URL
  const url = (entry.url as string) || "";
  if (url.endsWith("/sse") || url.includes("/sse?")) return "sse";
  return "http";
}

function parseMCPJson(raw: string): ParsedServer[] {
  let obj: Record<string, unknown>;
  try {
    obj = JSON.parse(raw);
  } catch {
    throw new Error("Invalid JSON");
  }

  // Support { mcpServers: {...} } or { servers: {...} } or bare { name: {...} }
  const dict =
    (obj.mcpServers as Record<string, unknown>) ??
    (obj.servers as Record<string, unknown>) ??
    obj;

  return Object.entries(dict).map(([name, val]) => {
    const entry = val as Record<string, unknown>;
    const type = inferType(entry);
    return {
      name,
      type,
      url: (entry.url as string) ?? "",
      headers: (entry.headers as Record<string, string>) ?? {},
      command: (entry.command as string) ?? "",
      args: (entry.args as string[]) ?? [],
      env: (entry.env as Record<string, string>) ?? {},
      timeout: (entry.timeout as number) ?? 30,
    };
  });
}

// ── Component ────────────────────────────────────────────────────────────────

export default function MCPServers({ hideTitle }: { hideTitle?: boolean } = {}) {
  const { t } = useTranslation();
  const { data: servers, isLoading } = useMCPServers();
  const { data: runtime } = useMCPRuntime();
  const create = useCreateMCPServer();
  const update = useUpdateMCPServer();
  const del = useDeleteMCPServer();
  const toggle = useToggleMCPServer();

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<MCPServer | null>(null);
  const [delTarget, setDelTarget] = useState<string | null>(null);
  const [dialogMode, setDialogMode] = useState<DialogMode>("manual");

  // Manual form state
  const [name, setName] = useState("");
  const [mcpType, setMcpType] = useState<McpType>("stdio");
  const [command, setCommand] = useState("");
  const [argsStr, setArgsStr] = useState("");
  const [envStr, setEnvStr] = useState("");
  const [url, setUrl] = useState("");
  const [headersStr, setHeadersStr] = useState("");
  const [timeout, setTimeout_] = useState("30");

  // JSON import state
  const [jsonText, setJsonText] = useState("");
  const [jsonError, setJsonError] = useState("");
  const [jsonPreview, setJsonPreview] = useState<ParsedServer[]>([]);

  // Tool expand / detail
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());
  const [activeTool, setActiveTool] = useState<MCPToolInfo | null>(null);

  const isRemote = mcpType !== "stdio";

  const openCreate = (mode: DialogMode = "json") => {
    setEditing(null);
    setDialogMode(mode);
    setName(""); setMcpType("stdio"); setCommand(""); setArgsStr("");
    setEnvStr(""); setUrl(""); setHeadersStr(""); setTimeout_("30");
    setJsonText(""); setJsonError(""); setJsonPreview([]);
    setOpen(true);
  };

  const openEdit = (s: MCPServer) => {
    setEditing(s);
    setDialogMode("manual");
    setName(s.name);
    const tp = (s.type as McpType) || "stdio";
    setMcpType(tp);
    setCommand(s.command ?? "");
    setArgsStr((s.args ?? []).join(" "));
    setEnvStr(Object.entries(s.env ?? {}).map(([k, v]) => `${k}=${v}`).join("\n"));
    setUrl(s.url ?? "");
    setHeadersStr(Object.entries(s.headers ?? {}).map(([k, v]) => `${k}: ${v}`).join("\n"));
    setTimeout_(String(s.timeout ?? 30));
    setJsonText(""); setJsonError(""); setJsonPreview([]);
    setOpen(true);
  };

  const parseEnv = (raw: string): Record<string, string> => {
    const result: Record<string, string> = {};
    for (const line of raw.split("\n")) {
      const eq = line.indexOf("=");
      if (eq > 0) result[line.slice(0, eq).trim()] = line.slice(eq + 1).trim();
    }
    return result;
  };

  const parseHeaders = (raw: string): Record<string, string> => {
    const result: Record<string, string> = {};
    for (const line of raw.split("\n")) {
      const idx = line.indexOf(":");
      if (idx > 0) result[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
    }
    return result;
  };

  const handleJsonChange = (val: string) => {
    setJsonText(val);
    if (!val.trim()) { setJsonError(""); setJsonPreview([]); return; }
    try {
      const parsed = parseMCPJson(val);
      setJsonPreview(parsed);
      setJsonError("");
    } catch (e: unknown) {
      setJsonPreview([]);
      setJsonError(String(e));
    }
  };

  const handleSaveManual = () => {
    const data: MCPServer = {
      name,
      type: mcpType,
      command: isRemote ? "" : command,
      args: isRemote ? [] : argsStr.split(/\s+/).filter(Boolean),
      env: isRemote ? {} : parseEnv(envStr),
      url: isRemote ? url : "",
      headers: isRemote ? parseHeaders(headersStr) : {},
      timeout: Number(timeout) || 30,
    };
    if (editing) {
      update.mutate({ name: editing.name, data });
    } else {
      create.mutate(data);
    }
    setOpen(false);
  };

  const handleSaveJson = async () => {
    if (!jsonPreview.length) return;
    let ok = 0;
    for (const s of jsonPreview) {
      try {
        await create.mutateAsync({
          name: s.name,
          type: s.type,
          url: s.url,
          headers: s.headers,
          command: s.command,
          args: s.args,
          env: s.env,
          timeout: s.timeout,
        });
        ok++;
      } catch {
        // toast shown by mutation onError; continue remaining
      }
    }
    if (ok > 0) toast.success(t("mcp.serversAdded", { count: ok }));
    setOpen(false);
  };

  const canSaveManual = !!name && (isRemote ? !!url : !!command);
  const canSaveJson = jsonPreview.length > 0 && !jsonError;

  const toggleExpand = (serverName: string) => {
    setExpandedTools(prev => {
      const next = new Set(prev);
      if (next.has(serverName)) next.delete(serverName);
      else next.add(serverName);
      return next;
    });
  };

  // Runtime lookup helper
  const getRuntimeInfo = (serverName: string) =>
    runtime?.find((r) => r.name === serverName);

  const totalCount = servers?.length ?? 0;
  const runningCount = servers?.filter((s) => !!getRuntimeInfo(s.name)?.running).length ?? 0;
  const stoppedCount = totalCount - runningCount;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className={hideTitle ? "flex items-center justify-between" : "flex items-center justify-between"}>
        {!hideTitle && <h1 className="text-2xl font-semibold">{t("mcp.title")}</h1>}
        <div className="flex items-center gap-2 ml-auto">
          <Button size="sm" variant="outline" onClick={() => openCreate("json")}>
            <Upload className="mr-2 h-4 w-4" />
            {t("mcp.importConfig")}
          </Button>
          <Button size="sm" onClick={() => openCreate("manual")}>
            <Plus className="mr-2 h-4 w-4" />
            {t("mcp.add")}
          </Button>
        </div>
      </div>

      {/* Summary bar */}
      {(servers && servers.length > 0) && (
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>
            <span className="inline-block h-2 w-2 rounded-full bg-muted-foreground/50 mr-1.5" />
            {t("mcp.totalCount")}: <span className="font-medium text-foreground">{totalCount}</span>
          </span>
          <span>
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 mr-1.5" />
            {t("mcp.runningCount")}: <span className="font-medium text-foreground">{runningCount}</span>
          </span>
          <span>
            <span className="inline-block h-2 w-2 rounded-full bg-muted-foreground/30 mr-1.5" />
            {t("mcp.stoppedCount")}: <span className="font-medium text-foreground">{stoppedCount}</span>
          </span>
        </div>
      )}

      {/* Server cards */}
      {isLoading ? (
        <div className="space-y-3">{[...Array(2)].map((_, i) => <Skeleton key={i} className="h-28 w-full" />)}</div>
      ) : (
        <div className="space-y-3">
          {servers?.map((s) => {
            const rt = getRuntimeInfo(s.name);
            const isRunning = rt?.running ?? false;
            const isEnabled = s.enabled !== false;
            const remote = s.type && s.type !== "stdio";
            const SHOW_TOOLS = 8;
            const isExpanded = expandedTools.has(s.name);
            return (
              <div
                key={s.name}
                className={`rounded-lg border bg-card relative overflow-hidden transition-colors hover:bg-muted/30${!isEnabled ? " opacity-60" : ""}`}
              >
                {/* left accent bar */}
                <div className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-lg ${!isEnabled ? "bg-muted-foreground/20" : isRunning ? "bg-emerald-500" : "bg-muted-foreground/20"}`} />
                <div className="pl-5 pr-4 py-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0 space-y-1.5">
                      {/* Name row */}
                      <div className="flex items-center gap-2 flex-wrap">
                        {remote
                          ? <Globe className="h-4 w-4 shrink-0 text-muted-foreground" />
                          : <Terminal className="h-4 w-4 shrink-0 text-muted-foreground" />}
                        <span className="font-semibold font-mono text-sm">{s.name}</span>
                        <Badge
                          variant="outline"
                          className={`text-xs gap-1 ${
                            isRunning
                              ? "border-emerald-500/40 text-emerald-600 bg-emerald-500/10"
                              : "border-muted-foreground/30 text-muted-foreground"
                          }`}
                        >
                          <span className={`inline-block h-1.5 w-1.5 rounded-full ${
                            isRunning ? "bg-emerald-500" : "bg-muted-foreground/50"
                          }`} />
                          {isRunning ? t("mcp.running") : t("mcp.stopped")}
                        </Badge>
                      </div>
                      {/* Command / URL */}
                      <p className="text-xs text-muted-foreground font-mono truncate">
                        {remote ? s.url : `${s.command ?? ""} ${(s.args ?? []).join(" ")}`}
                      </p>
                      {/* Tools */}
                      {rt && rt.tools.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1 pt-1">
                          <Wrench className="h-3 w-3 text-muted-foreground shrink-0" />
                          <span className="text-xs text-muted-foreground mr-0.5">{t("mcp.toolCount")}: {rt.tool_count}</span>
                          {(isExpanded ? rt.tools : rt.tools.slice(0, SHOW_TOOLS)).map((tool) => (
                            <Badge
                              key={tool.name}
                              variant="secondary"
                              className="text-xs px-1.5 py-0 font-mono cursor-pointer hover:bg-primary/15 transition-colors"
                              onClick={() => setActiveTool(tool)}
                            >
                              {tool.name}
                            </Badge>
                          ))}
                          {rt.tools.length > SHOW_TOOLS && (
                            <Badge
                              variant="outline"
                              className="text-xs px-1.5 py-0 cursor-pointer hover:bg-muted transition-colors"
                              onClick={() => toggleExpand(s.name)}
                            >
                              {isExpanded ? t("mcp.collapse") : `+${rt.tools.length - SHOW_TOOLS} ${t("mcp.more")}`}
                            </Badge>
                          )}
                        </div>
                      )}
                    </div>
                    {/* Actions */}
                    <div className="flex items-center gap-0.5 shrink-0">
                      <Button
                        size="icon"
                        variant="ghost"
                        className={`h-8 w-8 ${isEnabled ? "text-muted-foreground hover:text-foreground" : "text-amber-500 hover:text-amber-600"}`}
                        title={isEnabled ? t("mcp.disable") : t("mcp.enable")}
                        disabled={toggle.isPending && toggle.variables?.name === s.name}
                        onClick={() => toggle.mutate({ name: s.name, enabled: !isEnabled })}
                      >
                        {toggle.isPending && toggle.variables?.name === s.name
                          ? <Loader2 className="h-4 w-4 animate-spin" />
                          : <Power className="h-4 w-4" />}
                      </Button>
                      <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => openEdit(s)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button size="icon" variant="ghost" className="h-8 w-8 text-destructive"
                        onClick={() => setDelTarget(s.name)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
          {(!servers || servers.length === 0) && (
            <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground text-sm">
              {t("common.noData")}
            </div>
          )}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? t("mcp.edit") : t("mcp.add")}</DialogTitle>
          </DialogHeader>

          {/* Mode tabs — only shown when creating */}
          {!editing && (
            <div className="flex rounded-lg border p-0.5 gap-0.5 bg-muted/40 text-sm">
              <button
                className={`flex-1 rounded-md px-3 py-1.5 transition-colors ${
                  dialogMode === "json"
                    ? "bg-background shadow-sm font-medium"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                onClick={() => setDialogMode("json")}
              >
                {t("mcp.modeJson")}
              </button>
              <button
                className={`flex-1 rounded-md px-3 py-1.5 transition-colors ${
                  dialogMode === "manual"
                    ? "bg-background shadow-sm font-medium"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                onClick={() => setDialogMode("manual")}
              >
                {t("mcp.modeManual")}
              </button>
            </div>
          )}

          {/* JSON import mode */}
          {dialogMode === "json" && !editing && (
            <div className="space-y-3 py-1">
              <p className="text-xs text-muted-foreground">{t("mcp.jsonHint")}</p>
              <textarea
                className="w-full rounded-md border bg-background px-3 py-2 text-xs font-mono h-56 resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder={'{ "mcpServers": { "my-server": { "url": "https://...", "headers": {} } } }'}
                value={jsonText}
                onChange={(e) => handleJsonChange(e.target.value)}
              />
              {jsonError && (
                <p className="text-xs text-destructive">{jsonError}</p>
              )}
              {jsonPreview.length > 0 && (
                <div className="rounded-md border divide-y text-sm">
                  {jsonPreview.map((s) => (
                    <div key={s.name} className="flex items-center gap-2 px-3 py-2">
                      <Badge variant="outline" className="gap-1 text-xs shrink-0">
                        {s.type !== "stdio" ? <Globe className="h-3 w-3" /> : <Terminal className="h-3 w-3" />}
                        {s.type}
                      </Badge>
                      <span className="font-mono font-medium">{s.name}</span>
                      <span className="text-muted-foreground truncate text-xs">{s.url || s.command}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Manual form */}
          {(dialogMode === "manual" || editing) && (
            <div className="space-y-3 py-2">
              <div className="space-y-1">
                <Label>{t("mcp.name")}</Label>
                <Input value={name} onChange={(e) => setName(e.target.value)} disabled={!!editing} />
              </div>
              <div className="space-y-1">
                <Label>{t("mcp.type")}</Label>
                <Select value={mcpType} onValueChange={(v) => setMcpType(v as McpType)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="stdio">
                      <span className="flex items-center gap-2"><Terminal className="h-3.5 w-3.5" /> stdio — {t("mcp.typeStdioDesc")}</span>
                    </SelectItem>
                    <SelectItem value="http">
                      <span className="flex items-center gap-2"><Globe className="h-3.5 w-3.5" /> http — {t("mcp.typeHttpDesc")}</span>
                    </SelectItem>
                    <SelectItem value="sse">
                      <span className="flex items-center gap-2"><Globe className="h-3.5 w-3.5" /> sse — {t("mcp.typeSseDesc")}</span>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {isRemote ? (
                <>
                  <div className="space-y-1">
                    <Label>{t("mcp.url")}</Label>
                    <Input value={url} onChange={(e) => setUrl(e.target.value)}
                      placeholder="https://mcp.example.com/sse" />
                  </div>
                  <div className="space-y-1">
                    <Label>{t("mcp.headers")} ({t("common.optional")})</Label>
                    <textarea
                      className="w-full rounded-md border bg-background px-3 py-2 text-sm font-mono h-20 resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                      value={headersStr}
                      onChange={(e) => setHeadersStr(e.target.value)}
                      placeholder={"Authorization: Bearer <token>\nX-Custom: value"}
                    />
                    <p className="text-xs text-muted-foreground">{t("mcp.headersHint")}</p>
                  </div>
                </>
              ) : (
                <>
                  <div className="space-y-1">
                    <Label>{t("mcp.command")}</Label>
                    <Input value={command} onChange={(e) => setCommand(e.target.value)} placeholder="npx" />
                  </div>
                  <div className="space-y-1">
                    <Label>{t("mcp.args")} ({t("common.optional")})</Label>
                    <Input value={argsStr} onChange={(e) => setArgsStr(e.target.value)}
                      placeholder="-y @modelcontextprotocol/server-github" />
                  </div>
                  <div className="space-y-1">
                    <Label>{t("mcp.env")} ({t("common.optional")})</Label>
                    <textarea
                      className="w-full rounded-md border bg-background px-3 py-2 text-sm font-mono h-24 resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                      value={envStr}
                      onChange={(e) => setEnvStr(e.target.value)}
                      placeholder={"GITHUB_TOKEN=xxx\nSOME_KEY=value"}
                    />
                  </div>
                </>
              )}
              <div className="space-y-1">
                <Label>{t("mcp.timeout")} (s)</Label>
                <Input type="number" value={timeout} onChange={(e) => setTimeout_(e.target.value)} className="w-32" />
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>{t("common.cancel")}</Button>
            {dialogMode === "json" && !editing ? (
              <Button onClick={handleSaveJson} disabled={!canSaveJson}>
                {t("mcp.importN", { count: jsonPreview.length })}
              </Button>
            ) : (
              <Button onClick={handleSaveManual} disabled={!canSaveManual}>{t("mcp.save")}</Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!delTarget}
        title={t("mcp.delete")}
        description={t("mcp.deleteConfirm")}
        destructive
        onConfirm={() => { if (delTarget) del.mutate(delTarget); setDelTarget(null); }}
        onCancel={() => setDelTarget(null)}
      />

      {/* Tool detail dialog */}
      <Dialog open={activeTool !== null} onOpenChange={(v) => { if (!v) setActiveTool(null); }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 font-mono text-base">
              <Wrench className="h-4 w-4 shrink-0" />
              {activeTool?.name}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-1 overflow-y-auto max-h-[60vh]">
            <div className="space-y-1">
              <p className="text-sm font-semibold">{t("mcp.description")}</p>
              <p className="text-sm text-muted-foreground">
                {activeTool?.description || <span className="italic">{t("mcp.noDescription")}</span>}
              </p>
            </div>
            {activeTool && (() => {
              const schema = activeTool.parameters as Record<string, unknown> | undefined;
              const props = (schema?.properties as Record<string, Record<string, string>>) ?? {};
              const required = (schema?.required as string[]) ?? [];
              const entries = Object.entries(props);
              return (
                <div className="space-y-1">
                  <p className="text-sm font-semibold">{t("mcp.parameters")} ({entries.length})</p>
                  {entries.length === 0 ? (
                    <p className="text-sm text-muted-foreground italic">{t("mcp.noParams")}</p>
                  ) : (
                    <div className="rounded-md border divide-y text-xs">
                      {entries.map(([pname, pdef]) => (
                        <div key={pname} className="px-3 py-2 flex items-baseline gap-2 flex-wrap">
                          <span className="font-mono font-semibold">{pname}</span>
                          {pdef.type && <Badge variant="outline" className="text-xs px-1 py-0">{pdef.type}</Badge>}
                          {required.includes(pname) && <Badge variant="secondary" className="text-xs px-1 py-0">{t("mcp.required")}</Badge>}
                          {pdef.description && <span className="text-muted-foreground">{pdef.description}</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })()}
            <div className="space-y-1">
              <p className="text-sm font-semibold">{t("mcp.fullDef")}</p>
              <pre className="rounded-md bg-muted px-3 py-2 text-xs font-mono overflow-auto max-h-40 whitespace-pre-wrap break-all">
                {JSON.stringify({ name: activeTool?.name, description: activeTool?.description, parameters: activeTool?.parameters }, null, 2)}
              </pre>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setActiveTool(null)}>{t("common.close")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}