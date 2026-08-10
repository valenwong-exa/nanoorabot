import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { ConfirmDialog } from "../components/shared/ConfirmDialog";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { ScrollArea } from "../components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import type {
  HostDatabase,
  HostInventoryItem,
  HostInventoryResponse,
  HostInventoryUpdateInput,
  MonitoredDatabaseInventoryItem,
} from "../hooks/useHostInventory";
import { cn } from "../lib/utils";
import {
  CircleHelp,
  Database,
  ExternalLink,
  HardDrive,
  Loader2,
  Plus,
  Save,
  Server,
  ShieldCheck,
  Terminal,
  Trash2,
} from "lucide-react";

const SQLCL_GUIDE_URL = "https://docs.oracle.com/en/database/oracle/sql-developer-command-line/25.4/sqcug/preparing-your-environment.html#GUID-488E1167-D76C-4AFA-B74F-C0B154DF5B0F";

const SQLCL_CONNECTION_EXAMPLE = `SQL> conn -save cline_mcp -savepwd User123/pass123@//databaseserver:1521/orcl
Name: cline_mcp
Connect String: //databaseserver:1521/orcl
User: User123
Password: ******
Connected.
SQL>`;

type DeleteTarget =
  | { type: "database"; index: number; name: string }
  | { type: "host"; index: number; name: string }
  | { type: "hostDatabase"; hostIndex: number; databaseIndex: number; name: string };

interface ServerHostEditProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  inventory?: HostInventoryResponse;
  isSaving: boolean;
  isRefreshInProgress: boolean;
  onSave: (payload: HostInventoryUpdateInput) => Promise<HostInventoryResponse>;
}

const EMPTY_DATABASE: MonitoredDatabaseInventoryItem = {
  sqlcl_saveconnname: "",
  description: "",
  database_status: "UNKNOWN",
  database_name: "",
  database_version: "",
};

const EMPTY_HOST_DATABASE: HostDatabase = {
  database_name: "",
  sqlcl_saveconnname: "",
  database_version: "",
  oracle_home: "",
  pdb: "N",
  database_status: "UNKNOWN",
};

const EMPTY_HOST: HostInventoryItem = {
  host_name: "",
  description: "",
  aliases: [],
  ip: "",
  ssh_key: "",
  default_user: "oracle",
  privilege_escalation: "sudo su -",
  os_type: "",
  databases: [],
  host_status: "unknown",
};

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function databaseDraft(item: MonitoredDatabaseInventoryItem): MonitoredDatabaseInventoryItem {
  return { ...clone(EMPTY_DATABASE), ...clone(item) };
}

function hostDraft(item: HostInventoryItem): HostInventoryItem {
  return {
    ...clone(EMPTY_HOST),
    ...clone(item),
    aliases: clone(item.aliases ?? []),
    databases: (item.databases ?? []).map((database) => ({
      ...clone(EMPTY_HOST_DATABASE),
      ...clone(database),
    })),
  };
}

function errorDetail(error: unknown): string | null {
  if (typeof error !== "object" || error === null) return null;
  const response = (error as { response?: { data?: { detail?: unknown } } }).response;
  return typeof response?.data?.detail === "string" ? response.data.detail : null;
}

function Field({
  label,
  value,
  onChange,
  required,
  type = "text",
  placeholder,
  disabled,
  autoComplete,
}: {
  label: string;
  value: string;
  onChange?: (value: string) => void;
  required?: boolean;
  type?: string;
  placeholder?: string;
  disabled?: boolean;
  autoComplete?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label>
        {label}
        {required ? <span className="ml-1 text-destructive">*</span> : null}
      </Label>
      <Input
        type={type}
        value={value}
        onChange={(event) => onChange?.(event.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete={autoComplete}
      />
    </div>
  );
}

export default function ServerHostEdit({
  open,
  onOpenChange,
  inventory,
  isSaving,
  isRefreshInProgress,
  onSave,
}: ServerHostEditProps) {
  const { t } = useTranslation();
  const initialHosts = (inventory?.hosts ?? []).map(hostDraft);
  const [databases, setDatabases] = useState<MonitoredDatabaseInventoryItem[]>(
    () => (inventory?.database_inventory ?? []).map(databaseDraft),
  );
  const [hosts, setHosts] = useState<HostInventoryItem[]>(() => initialHosts);
  const [aliasTexts, setAliasTexts] = useState<string[]>(() => initialHosts.map((host) => host.aliases.join(", ")));
  const [databaseIndex, setDatabaseIndex] = useState(0);
  const [hostIndex, setHostIndex] = useState(0);
  const [hostDatabaseIndex, setHostDatabaseIndex] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [discardOpen, setDiscardOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);

  const selectedDatabase = databases[databaseIndex];
  const selectedHost = hosts[hostIndex];
  const selectedHostDatabase = selectedHost?.databases?.[hostDatabaseIndex];

  const validationError = (() => {
    const connectionNames = new Set<string>();
    for (const database of databases) {
      const connection = database.sqlcl_saveconnname?.trim() ?? "";
      if (!connection || !database.database_name.trim()) return t("host.maintenance.validation.databaseRequired");
      if (connectionNames.has(connection)) return t("host.maintenance.validation.duplicateConnection", { name: connection });
      connectionNames.add(connection);
    }
    const hostNames = new Set<string>();
    for (const host of hosts) {
      if (!host.host_name.trim() || !host.ip.trim() || !host.ssh_key.trim() || !host.default_user.trim()) {
        return t("host.maintenance.validation.hostRequired");
      }
      if (hostNames.has(host.host_name.trim())) {
        return t("host.maintenance.validation.duplicateHost", { name: host.host_name.trim() });
      }
      hostNames.add(host.host_name.trim());
      if (host.databases.some((database) => !database.database_name.trim())) {
        return t("host.maintenance.validation.hostDatabaseRequired");
      }
    }
    return null;
  })();

  const updateDatabase = (field: keyof MonitoredDatabaseInventoryItem, value: string) => {
    setDatabases((current) => current.map((item, index) => index === databaseIndex ? { ...item, [field]: value } : item));
    setDirty(true);
  };

  const updateHost = (field: keyof HostInventoryItem, value: string) => {
    setHosts((current) => current.map((item, index) => index === hostIndex ? { ...item, [field]: value } : item));
    setDirty(true);
  };

  const updateHostDatabase = (field: keyof HostDatabase, value: string) => {
    setHosts((current) => current.map((host, index) => {
      if (index !== hostIndex) return host;
      return {
        ...host,
        databases: host.databases.map((database, nestedIndex) =>
          nestedIndex === hostDatabaseIndex ? { ...database, [field]: value } : database),
      };
    }));
    setDirty(true);
  };

  const addDatabase = () => {
    setDatabases((current) => [...current, clone(EMPTY_DATABASE)]);
    setDatabaseIndex(databases.length);
    setDirty(true);
  };

  const addHost = () => {
    setHosts((current) => [...current, clone(EMPTY_HOST)]);
    setAliasTexts((current) => [...current, ""]);
    setHostIndex(hosts.length);
    setHostDatabaseIndex(0);
    setDirty(true);
  };

  const addHostDatabase = () => {
    if (!selectedHost) return;
    const nextIndex = selectedHost.databases.length;
    setHosts((current) => current.map((host, index) => index === hostIndex
      ? { ...host, databases: [...host.databases, clone(EMPTY_HOST_DATABASE)] }
      : host));
    setHostDatabaseIndex(nextIndex);
    setDirty(true);
  };

  const confirmDelete = () => {
    if (!deleteTarget) return;
    if (deleteTarget.type === "database") {
      setDatabases((current) => current.filter((_, index) => index !== deleteTarget.index));
      setDatabaseIndex((current) => Math.max(0, Math.min(current, databases.length - 2)));
    } else if (deleteTarget.type === "host") {
      setHosts((current) => current.filter((_, index) => index !== deleteTarget.index));
      setAliasTexts((current) => current.filter((_, index) => index !== deleteTarget.index));
      setHostIndex((current) => Math.max(0, Math.min(current, hosts.length - 2)));
      setHostDatabaseIndex(0);
    } else {
      setHosts((current) => current.map((host, index) => index === deleteTarget.hostIndex
        ? { ...host, databases: host.databases.filter((_, nestedIndex) => nestedIndex !== deleteTarget.databaseIndex) }
        : host));
      setHostDatabaseIndex((current) => Math.max(0, Math.min(current, (selectedHost?.databases.length ?? 1) - 2)));
    }
    setDirty(true);
    setDeleteTarget(null);
  };

  const requestClose = () => {
    if (isSaving) return;
    if (dirty) setDiscardOpen(true);
    else onOpenChange(false);
  };

  const save = async () => {
    if (validationError) {
      toast.error(validationError);
      return;
    }
    const normalizedHosts = hosts.map((host, index) => ({
      ...host,
      aliases: (aliasTexts[index] ?? "").split(/[,\n]/).map((alias) => alias.trim()).filter(Boolean),
    }));
    try {
      await onSave({ database_inventory: databases, host_inventory: normalizedHosts });
      setHosts(normalizedHosts);
      setDirty(false);
      toast.success(t("host.maintenance.saved"));
    } catch (error) {
      toast.error(errorDetail(error) ?? t("host.maintenance.saveFailed"));
    }
  };

  return (
    <>
      <Dialog open={open} onOpenChange={(next) => { if (!next) requestClose(); }}>
        <DialogContent className="flex h-[88vh] w-[94vw] max-w-[1180px] flex-col gap-0 overflow-hidden p-0">
          <DialogHeader className="border-b px-6 py-5 pr-12">
            <DialogTitle>{t("host.maintenance.title")}</DialogTitle>
            <DialogDescription className="truncate" title={inventory?.inventory_path}>
              {t("host.maintenance.description")} · {inventory?.inventory_path ?? "-"}
            </DialogDescription>
          </DialogHeader>
          {isRefreshInProgress ? (
            <div className="mx-6 mt-4 rounded-lg border border-amber-300/60 bg-amber-50 px-4 py-2 text-xs text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
              {t("host.maintenance.refreshWarning")}
            </div>
          ) : null}

          <Tabs defaultValue="databases" className="flex min-h-0 flex-1 flex-col px-6 pt-4">
            <TabsList className="w-fit">
              <TabsTrigger value="databases" className="gap-2">
                <Database className="h-4 w-4" />
                {t("host.maintenance.databases")} <Badge variant="secondary">{databases.length}</Badge>
              </TabsTrigger>
              <TabsTrigger value="hosts" className="gap-2">
                <Server className="h-4 w-4" />
                {t("host.maintenance.hosts")} <Badge variant="secondary">{hosts.length}</Badge>
              </TabsTrigger>
              <TabsTrigger value="sqlcl-help" className="gap-2">
                <CircleHelp className="h-4 w-4" />
                {t("host.maintenance.sqlclHelp.tab")}
              </TabsTrigger>
            </TabsList>

            <TabsContent value="databases" className="min-h-0 flex-1 overflow-hidden pb-4">
              <div className="grid h-full min-h-[420px] grid-cols-1 overflow-hidden rounded-xl border md:grid-cols-[280px_1fr]">
                <InventoryList
                  title={t("host.maintenance.databaseConnections")}
                  addLabel={t("host.maintenance.addDatabase")}
                  items={databases.map((database) => ({
                    title: database.database_name || t("host.maintenance.unnamedDatabase"),
                    subtitle: database.sqlcl_saveconnname || "SQLcl",
                  }))}
                  selectedIndex={databaseIndex}
                  onSelect={setDatabaseIndex}
                  onAdd={addDatabase}
                />
                <ScrollArea className="h-full">
                  {selectedDatabase ? (
                    <div className="space-y-5 p-5">
                      <EditorHeading
                        icon={Database}
                        title={selectedDatabase.database_name || t("host.maintenance.unnamedDatabase")}
                        subtitle={t("host.maintenance.databaseHint")}
                        onDelete={() => setDeleteTarget({ type: "database", index: databaseIndex, name: selectedDatabase.database_name || t("host.maintenance.unnamedDatabase") })}
                      />
                      <div className="grid gap-4 sm:grid-cols-2">
                        <Field label="SQLcl saved connection" required value={selectedDatabase.sqlcl_saveconnname ?? ""} onChange={(value) => updateDatabase("sqlcl_saveconnname", value)} placeholder="aidemo" />
                        <Field label={t("host.maintenance.fields.databaseName")} required value={selectedDatabase.database_name} onChange={(value) => updateDatabase("database_name", value)} placeholder="AIDB" />
                        <Field label={t("host.maintenance.fields.databaseVersion")} value={selectedDatabase.database_version ?? ""} onChange={(value) => updateDatabase("database_version", value)} placeholder="23.26.1.0.0" />
                        <Field label={t("common.status")} value={selectedDatabase.database_status ?? "UNKNOWN"} disabled />
                        <div className="space-y-1.5 sm:col-span-2">
                          <Label>{t("host.maintenance.fields.description")}</Label>
                          <textarea className="min-h-20 w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring" value={selectedDatabase.description ?? ""} onChange={(event) => updateDatabase("description", event.target.value)} />
                        </div>
                      </div>
                    </div>
                  ) : <EmptyEditor text={t("host.maintenance.emptyDatabases")} />}
                </ScrollArea>
              </div>
            </TabsContent>

            <TabsContent value="hosts" className="min-h-0 flex-1 overflow-hidden pb-4">
              <div className="grid h-full min-h-[420px] grid-cols-1 overflow-hidden rounded-xl border md:grid-cols-[280px_1fr]">
                <InventoryList
                  title={t("host.maintenance.hostList")}
                  addLabel={t("host.maintenance.addHost")}
                  items={hosts.map((host) => ({ title: host.host_name || t("host.maintenance.unnamedHost"), subtitle: host.ip || "-" }))}
                  selectedIndex={hostIndex}
                  onSelect={(index) => { setHostIndex(index); setHostDatabaseIndex(0); }}
                  onAdd={addHost}
                />
                <ScrollArea className="h-full">
                  {selectedHost ? (
                    <div className="space-y-6 p-5">
                      <EditorHeading
                        icon={Server}
                        title={selectedHost.host_name || t("host.maintenance.unnamedHost")}
                        subtitle={t("host.maintenance.hostHint")}
                        onDelete={() => setDeleteTarget({ type: "host", index: hostIndex, name: selectedHost.host_name || t("host.maintenance.unnamedHost") })}
                      />
                      <section className="space-y-4">
                        <h4 className="text-sm font-semibold">{t("host.maintenance.connectionInfo")}</h4>
                        <div className="grid gap-4 sm:grid-cols-2">
                          <Field label={t("host.maintenance.fields.hostName")} required value={selectedHost.host_name} onChange={(value) => updateHost("host_name", value)} placeholder="MiWiFi-R3P-srv" />
                          <Field label={t("host.labels.ip")} required value={selectedHost.ip} onChange={(value) => updateHost("ip", value)} placeholder="192.168.56.118" />
                          <Field label={t("host.maintenance.fields.sshKey")} required type="password" autoComplete="new-password" value={selectedHost.ssh_key} onChange={(value) => updateHost("ssh_key", value)} placeholder="E:\\OpenSSH-Win64\\linux118.key" />
                          <Field label={t("host.labels.defaultUser")} required value={selectedHost.default_user} onChange={(value) => updateHost("default_user", value)} placeholder="oracle" />
                          <Field label={t("host.maintenance.fields.privilegeEscalation")} value={selectedHost.privilege_escalation} onChange={(value) => updateHost("privilege_escalation", value)} placeholder="sudo su -" />
                          <Field label={t("host.maintenance.fields.osType")} value={selectedHost.os_type} onChange={(value) => updateHost("os_type", value)} placeholder="Oracle Linux 8.10" />
                          <div className="space-y-1.5 sm:col-span-2">
                            <Label>{t("host.labels.aliases")}</Label>
                            <Input value={aliasTexts[hostIndex] ?? ""} onChange={(event) => { setAliasTexts((current) => current.map((value, index) => index === hostIndex ? event.target.value : value)); setDirty(true); }} placeholder="23ai, 23db" />
                            <p className="text-xs text-muted-foreground">{t("host.maintenance.aliasHint")}</p>
                          </div>
                          <div className="space-y-1.5 sm:col-span-2">
                            <Label>{t("host.maintenance.fields.description")}</Label>
                            <textarea className="min-h-20 w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring" value={selectedHost.description ?? ""} onChange={(event) => updateHost("description", event.target.value)} />
                          </div>
                        </div>
                      </section>

                      <section className="space-y-3 border-t pt-5">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <h4 className="text-sm font-semibold">{t("host.maintenance.hostDatabases")}</h4>
                            <p className="text-xs text-muted-foreground">{t("host.maintenance.hostDatabaseHint")}</p>
                          </div>
                          <Button type="button" variant="outline" size="sm" onClick={addHostDatabase}>
                            <Plus /> {t("host.maintenance.addHostDatabase")}
                          </Button>
                        </div>
                        {selectedHost.databases.length ? (
                          <>
                            <div className="flex flex-wrap gap-2">
                              {selectedHost.databases.map((database, index) => (
                                <Button key={`${database.database_name}-${index}`} type="button" size="sm" variant={index === hostDatabaseIndex ? "secondary" : "outline"} onClick={() => setHostDatabaseIndex(index)}>
                                  <HardDrive /> {database.database_name || t("host.maintenance.unnamedDatabase")}
                                </Button>
                              ))}
                            </div>
                            {selectedHostDatabase ? (
                              <div className="rounded-lg border bg-muted/10 p-4">
                                <div className="mb-4 flex justify-end">
                                  <Button type="button" variant="ghost" size="sm" className="text-destructive hover:text-destructive" onClick={() => setDeleteTarget({ type: "hostDatabase", hostIndex, databaseIndex: hostDatabaseIndex, name: selectedHostDatabase.database_name || t("host.maintenance.unnamedDatabase") })}>
                                    <Trash2 /> {t("common.delete")}
                                  </Button>
                                </div>
                                <div className="grid gap-4 sm:grid-cols-2">
                                  <Field label={t("host.maintenance.fields.databaseName")} required value={selectedHostDatabase.database_name} onChange={(value) => updateHostDatabase("database_name", value)} placeholder="ORCLCDB" />
                                  <Field label="SQLcl saved connection" value={selectedHostDatabase.sqlcl_saveconnname ?? ""} onChange={(value) => updateHostDatabase("sqlcl_saveconnname", value)} />
                                  <Field label={t("host.maintenance.fields.databaseVersion")} value={selectedHostDatabase.database_version} onChange={(value) => updateHostDatabase("database_version", value)} placeholder="23.0.0.0.0" />
                                  <Field label="Oracle Home" value={selectedHostDatabase.oracle_home ?? ""} onChange={(value) => updateHostDatabase("oracle_home", value)} placeholder="/opt/oracle/product/23c/dbhome_1" />
                                  <Field label="PDB" value={selectedHostDatabase.pdb ?? "N"} onChange={(value) => updateHostDatabase("pdb", value)} placeholder="Y / N" />
                                  <Field label={t("common.status")} value={selectedHostDatabase.database_status ?? "UNKNOWN"} disabled />
                                </div>
                              </div>
                            ) : null}
                          </>
                        ) : <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">{t("host.maintenance.emptyHostDatabases")}</div>}
                      </section>
                    </div>
                  ) : <EmptyEditor text={t("host.maintenance.emptyHosts")} />}
                </ScrollArea>
              </div>
            </TabsContent>

            <TabsContent value="sqlcl-help" className="min-h-0 flex-1 overflow-hidden pb-4">
              <SqlclHelpPanel />
            </TabsContent>
          </Tabs>

          <DialogFooter className="items-center border-t bg-muted/20 px-6 py-4 sm:justify-between">
            <div className={cn("text-xs", validationError ? "text-destructive" : "text-muted-foreground")}>
              {isRefreshInProgress
                ? t("host.maintenance.refreshWarning")
                : validationError ?? (dirty ? t("host.maintenance.unsaved") : t("host.maintenance.synced"))}
            </div>
            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={requestClose} disabled={isSaving}>{t("common.close")}</Button>
              <Button type="button" onClick={() => void save()} disabled={isSaving || isRefreshInProgress || !dirty || Boolean(validationError)}>
                {isSaving ? <Loader2 className="animate-spin" /> : <Save />}
                {isSaving ? t("common.saving") : t("host.maintenance.saveJson")}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteTarget !== null}
        title={t("host.maintenance.deleteTitle")}
        description={t("host.maintenance.deleteDescription", { name: deleteTarget?.name ?? "" })}
        destructive
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
      <ConfirmDialog
        open={discardOpen}
        title={t("host.maintenance.discardTitle")}
        description={t("host.maintenance.discardDescription")}
        destructive
        onConfirm={() => { setDiscardOpen(false); setDirty(false); onOpenChange(false); }}
        onCancel={() => setDiscardOpen(false)}
      />
    </>
  );
}

function InventoryList({ title, addLabel, items, selectedIndex, onSelect, onAdd }: {
  title: string;
  addLabel: string;
  items: Array<{ title: string; subtitle: string }>;
  selectedIndex: number;
  onSelect: (index: number) => void;
  onAdd: () => void;
}) {
  return (
    <div className="flex min-h-0 flex-col border-b bg-muted/20 md:border-b-0 md:border-r">
      <div className="flex items-center justify-between gap-2 border-b px-4 py-3">
        <span className="text-sm font-semibold">{title}</span>
        <Button type="button" size="sm" onClick={onAdd}><Plus /> {addLabel}</Button>
      </div>
      <ScrollArea className="max-h-36 flex-1 md:max-h-none">
        <div className="space-y-1 p-2">
          {items.map((item, index) => (
            <button
              key={`${item.title}-${index}`}
              type="button"
              className={cn("w-full rounded-lg px-3 py-2 text-left transition-colors hover:bg-accent", index === selectedIndex && "bg-accent")}
              onClick={() => onSelect(index)}
            >
              <div className="truncate text-sm font-medium">{item.title}</div>
              <div className="mt-0.5 truncate text-xs text-muted-foreground">{item.subtitle}</div>
            </button>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

function EditorHeading({ icon: Icon, title, subtitle, onDelete }: {
  icon: typeof Database;
  title: string;
  subtitle: string;
  onDelete: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10"><Icon className="h-5 w-5 text-primary" /></div>
        <div className="min-w-0">
          <h3 className="truncate font-semibold">{title}</h3>
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        </div>
      </div>
      <Button type="button" variant="ghost" size="sm" className="text-destructive hover:text-destructive" onClick={onDelete}>
        <Trash2 /> {t("common.delete")}
      </Button>
    </div>
  );
}

function EmptyEditor({ text }: { text: string }) {
  return <div className="flex min-h-[360px] items-center justify-center p-8 text-center text-sm text-muted-foreground">{text}</div>;
}

function SqlclHelpPanel() {
  const { t } = useTranslation();

  return (
    <ScrollArea className="h-full min-h-[420px] rounded-xl border bg-muted/10">
      <div className="mx-auto max-w-4xl space-y-6 p-5 sm:p-7">
        <section className="overflow-hidden rounded-2xl border bg-gradient-to-br from-primary/10 via-background to-background p-5 shadow-sm sm:p-6">
          <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
            <div className="flex min-w-0 gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-sm">
                <Terminal className="h-6 w-6" />
              </div>
              <div className="space-y-2">
                <Badge variant="secondary">Oracle SQLcl</Badge>
                <h3 className="text-xl font-semibold tracking-tight">{t("host.maintenance.sqlclHelp.title")}</h3>
                <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                  {t("host.maintenance.sqlclHelp.description")}
                </p>
              </div>
            </div>
            <Button type="button" variant="outline" className="shrink-0" asChild>
              <a href={SQLCL_GUIDE_URL} target="_blank" rel="noreferrer">
                {t("host.maintenance.sqlclHelp.officialGuide")}
                <ExternalLink className="h-4 w-4" />
              </a>
            </Button>
          </div>
        </section>

        <div className="grid gap-4 md:grid-cols-3">
          <HelpStep number="1" title={t("host.maintenance.sqlclHelp.step1Title")}>
            {t("host.maintenance.sqlclHelp.step1Description")}
          </HelpStep>
          <HelpStep number="2" title={t("host.maintenance.sqlclHelp.step2Title")}>
            {t("host.maintenance.sqlclHelp.step2Description")}
          </HelpStep>
          <HelpStep number="3" title={t("host.maintenance.sqlclHelp.step3Title")}>
            {t("host.maintenance.sqlclHelp.step3Description")}
          </HelpStep>
        </div>

        <section className="overflow-hidden rounded-xl border bg-slate-950 text-slate-100 shadow-sm">
          <div className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-3">
            <div>
              <h4 className="text-sm font-semibold">{t("host.maintenance.sqlclHelp.commandTitle")}</h4>
              <p className="mt-0.5 text-xs text-slate-400">{t("host.maintenance.sqlclHelp.commandHint")}</p>
            </div>
            <Badge className="border-white/10 bg-white/10 text-slate-200 hover:bg-white/10">SQLcl</Badge>
          </div>
          <pre className="overflow-x-auto p-4 text-xs leading-6 sm:text-sm"><code>{SQLCL_CONNECTION_EXAMPLE}</code></pre>
        </section>

        <section className="grid gap-4 rounded-xl border bg-background p-5 sm:grid-cols-[1fr_auto] sm:items-center">
          <div>
            <h4 className="text-sm font-semibold">{t("host.maintenance.sqlclHelp.matchTitle")}</h4>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              {t("host.maintenance.sqlclHelp.matchDescription")}
            </p>
          </div>
          <div className="rounded-lg border bg-muted/40 px-4 py-3 font-mono text-sm">
            <span className="text-muted-foreground">SQLcl saved connection = </span>
            <strong className="text-foreground">cline_mcp</strong>
          </div>
        </section>

        <section className="flex gap-3 rounded-xl border border-amber-300/60 bg-amber-50 p-4 text-amber-950 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-100">
          <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <h4 className="text-sm font-semibold">{t("host.maintenance.sqlclHelp.securityTitle")}</h4>
            <p className="mt-1 text-xs leading-5 opacity-80">{t("host.maintenance.sqlclHelp.securityDescription")}</p>
          </div>
        </section>
      </div>
    </ScrollArea>
  );
}

function HelpStep({ number, title, children }: { number: string; title: string; children: string }) {
  return (
    <section className="rounded-xl border bg-background p-4 shadow-sm">
      <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
        {number}
      </div>
      <h4 className="text-sm font-semibold">{title}</h4>
      <p className="mt-1.5 text-xs leading-5 text-muted-foreground">{children}</p>
    </section>
  );
}
