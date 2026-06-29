import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { ConfirmDialog } from "../components/shared/ConfirmDialog";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { useSaveToolPolicy, useToolPolicy, type DefenseRule } from "../hooks/useToolPolicy";
import {
  AlertTriangle,
  Loader2,
  Pencil,
  Plus,
  Save,
  Search,
  Shield,
  ShieldAlert,
  Trash2,
} from "lucide-react";
import { cn } from "../lib/utils";

type ToolPolicyForm = {
  version: number;
  name: string;
  source: string;
  description: string;
  rules: DefenseRule[];
};

const DEFAULT_RULES: DefenseRule[] = [
  { command: "truncate table", matchType: "literal", regexFlags: "", category: "oracle", severity: "critical", mode: "block", scope: "SQL", note: "高风险数据清空操作" },
  { command: "drop table", matchType: "literal", regexFlags: "", category: "oracle", severity: "critical", mode: "block", scope: "SQL", note: "直接删除表结构与数据" },
  { command: "delete from", matchType: "literal", regexFlags: "", category: "oracle", severity: "high", mode: "warn", scope: "SQL", note: "大批量删除需要人工确认" },
  { command: String.raw`\bupdate\b[\s\S]*?\bset\b(?:(?!\bwhere\b)[\s\S])*$`, matchType: "regex", regexFlags: "i", category: "oracle", severity: "high", mode: "warn", scope: "SQL", note: "避免整表更新" },
  { command: "rm -rf", matchType: "literal", regexFlags: "", category: "filesystem", severity: "critical", mode: "block", scope: "Shell", note: "危险递归删除命令" },
  { command: "shutdown -h now", matchType: "literal", regexFlags: "", category: "linux", severity: "critical", mode: "block", scope: "Shell", note: "主机关机命令" },
  { command: "reboot", matchType: "literal", regexFlags: "", category: "linux", severity: "high", mode: "warn", scope: "Shell", note: "主机重启前要求提示" },
];

const DEFAULT_POLICY: ToolPolicyForm = {
  version: 1,
  name: "dangerous_tool_policy",
  source: "webui-defense-page",
  description: "Initial dangerous command policy seeded from the WebUI Defense page demo rules.",
  rules: DEFAULT_RULES,
};

const EMPTY_RULE: DefenseRule = {
  command: "",
  matchType: "literal",
  regexFlags: "",
  category: "oracle",
  severity: "high",
  mode: "warn",
  scope: "SQL",
  note: "",
};

export default function Defense() {
  const { t } = useTranslation();
  const { data, error, isLoading } = useToolPolicy();
  const saveMutation = useSaveToolPolicy();
  const [keyword, setKeyword] = useState("");
  const [policy, setPolicy] = useState<ToolPolicyForm>(DEFAULT_POLICY);
  const [configPath, setConfigPath] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [policyDialogOpen, setPolicyDialogOpen] = useState(false);
  const [ruleDialogOpen, setRuleDialogOpen] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [deleteIndex, setDeleteIndex] = useState<number | null>(null);
  const [draftRule, setDraftRule] = useState<DefenseRule>(EMPTY_RULE);

  useEffect(() => {
    if (!data) {
      return;
    }
    setPolicy({
      version: data.version,
      name: data.name,
      source: data.source,
      description: data.description,
      rules: data.rules,
    });
    setConfigPath(data.configPath);
    setUpdatedAt(data.updatedAt);
  }, [data]);

  const filteredRules = useMemo(() => {
    const query = keyword.trim().toLowerCase();
    return policy.rules
      .map((rule, index) => ({ rule, index }))
      .filter(({ rule }) =>
        !query
          || [rule.command, rule.matchType, rule.regexFlags, rule.category, rule.severity, rule.mode, rule.scope, rule.note]
            .join(" ")
            .toLowerCase()
            .includes(query)
      );
  }, [keyword, policy.rules]);

  const statCards = [
    {
      label: t("defense.stats.totalRules"),
      value: policy.rules.length,
      sub: t("defense.stats.demoPolicy"),
      icon: Shield,
      iconColor: "text-blue-500",
      iconBg: "bg-blue-50 dark:bg-blue-950/50",
    },
    {
      label: t("defense.stats.blockRules"),
      value: policy.rules.filter((rule) => rule.mode === "block").length,
      sub: t("defense.block"),
      icon: ShieldAlert,
      iconColor: "text-destructive",
      iconBg: "bg-destructive/10",
    },
    {
      label: t("defense.stats.warnRules"),
      value: policy.rules.filter((rule) => rule.mode === "warn").length,
      sub: t("defense.warn"),
      icon: AlertTriangle,
      iconColor: "text-amber-500",
      iconBg: "bg-amber-50 dark:bg-amber-950/50",
    },
  ];

  const badgeClass = (value: string) =>
    ({
      critical: "bg-destructive/10 text-destructive",
      high: "bg-amber-500/10 text-amber-700 dark:text-amber-300",
      block: "bg-destructive text-destructive-foreground",
      warn: "bg-amber-500 text-white",
      oracle: "bg-violet-500/10 text-violet-700 dark:text-violet-300",
      linux: "bg-blue-500/10 text-blue-700 dark:text-blue-300",
      filesystem: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    }[value] ?? "bg-muted text-muted-foreground");

  const loadErrorMessage = (
    error as { response?: { data?: { detail?: string } } } | null
  )?.response?.data?.detail;

  const updatePolicyField = (key: keyof Omit<ToolPolicyForm, "rules">, value: string) => {
    setPolicy((prev) => ({
      ...prev,
      [key]: key === "version" ? Number(value || "1") : value,
    }));
  };

  const updateDraftRule = (key: keyof DefenseRule, value: string) => {
    setDraftRule((prev) => ({ ...prev, [key]: value }));
  };

  const openCreateRule = () => {
    setEditingIndex(null);
    setDraftRule(EMPTY_RULE);
    setRuleDialogOpen(true);
  };

  const openEditRule = (index: number) => {
    setEditingIndex(index);
    setDraftRule(policy.rules[index]);
    setRuleDialogOpen(true);
  };

  const applySavedPolicy = (saved: ToolPolicyForm & { configPath?: string | null; updatedAt?: string | null }) => {
    setPolicy({
      version: saved.version,
      name: saved.name,
      source: saved.source,
      description: saved.description,
      rules: saved.rules,
    });
    setConfigPath(saved.configPath ?? null);
    setUpdatedAt(saved.updatedAt ?? null);
  };

  const saveRule = async () => {
    if (!draftRule.command.trim() || !draftRule.scope.trim()) {
      return;
    }
    const normalized: DefenseRule = {
      ...draftRule,
      command: draftRule.command.trim(),
      scope: draftRule.scope.trim(),
      note: draftRule.note.trim(),
    };
    const nextRules = [...policy.rules];
    if (editingIndex === null) {
      nextRules.push(normalized);
    } else {
      nextRules[editingIndex] = normalized;
    }
    const nextPolicy: ToolPolicyForm = {
      ...policy,
      rules: nextRules,
    };
    const saved = await saveMutation.mutateAsync(nextPolicy);
    applySavedPolicy(saved);
    setRuleDialogOpen(false);
  };

  const deleteRule = async () => {
    if (deleteIndex === null) {
      return;
    }
    const nextPolicy: ToolPolicyForm = {
      ...policy,
      rules: policy.rules.filter((_, index) => index !== deleteIndex),
    };
    const saved = await saveMutation.mutateAsync(nextPolicy);
    applySavedPolicy(saved);
    setDeleteIndex(null);
  };

  const handleSavePolicy = async () => {
    const saved = await saveMutation.mutateAsync(policy);
    applySavedPolicy(saved);
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {statCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground">{stat.label}</p>
                    <p className="mt-1 text-2xl font-bold">{stat.value}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{stat.sub}</p>
                  </div>
                  <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg", stat.iconBg)}>
                    <Icon className={cn("h-4 w-4", stat.iconColor)} />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>{t("defense.title")}</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">{t("defense.subtitle")}</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setPolicyDialogOpen(true)}>
              <Pencil className="h-4 w-4" />
              {t("defense.buttons.editPolicy")}
            </Button>
            <Button size="sm" onClick={openCreateRule} disabled={saveMutation.isPending}>
              <Plus className="h-4 w-4" />
              {t("defense.buttons.addRule")}
            </Button>
            <Button size="sm" onClick={handleSavePolicy} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              保存策略
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="rounded-lg border bg-muted/20 px-4 py-3 text-xs text-muted-foreground">
              {t("defense.banner")}
              <div className="mt-2 flex flex-col gap-1">
                <span>策略文件: {configPath ?? "未配置 --tool-policy"}</span>
                <span>最近更新时间: {updatedAt ?? "未保存"}</span>
              </div>
            </div>

            <div className="rounded-lg border border-blue-200/60 bg-blue-50/60 px-4 py-3 text-xs text-blue-900 dark:border-blue-900/40 dark:bg-blue-950/20 dark:text-blue-100">
              <div className="font-medium">Regex 说明</div>
              <div className="mt-1 flex flex-col gap-1">
                <span>`matchType=literal` 表示普通关键字匹配，大小写不敏感，并自动压缩连续空格。</span>
                <span>`matchType=regex` 表示按正则表达式匹配，默认建议 `regexFlags=i` 以忽略大小写。</span>
                <span>如果要匹配多个空格、换行或任意空白，请使用 `\s+` 或 `[\s\S]*`。</span>
                <span>示例：匹配无 where 的 update 可写成 `\bupdate\b[\s\S]*?\bset\b(?:(?!\bwhere\b)[\s\S])*$`。</span>
              </div>
            </div>

            {isLoading && (
              <div className="rounded-lg border bg-background/60 px-4 py-3 text-sm text-muted-foreground">
                正在加载危险命令策略...
              </div>
            )}

            {loadErrorMessage && (
              <div className="rounded-lg border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                加载策略失败: {loadErrorMessage}
              </div>
            )}

            <div className="flex items-center gap-3 rounded-lg border bg-background/60 p-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                <Search className="h-4 w-4 text-primary" />
              </div>
              <Input
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder={t("defense.filterPlaceholder")}
              />
            </div>

            <div className="rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("defense.table.command")}</TableHead>
                    <TableHead>匹配方式</TableHead>
                    <TableHead>{t("defense.table.category")}</TableHead>
                    <TableHead>{t("defense.table.severity")}</TableHead>
                    <TableHead>{t("defense.table.mode")}</TableHead>
                    <TableHead>{t("defense.table.scope")}</TableHead>
                    <TableHead>{t("defense.table.note")}</TableHead>
                    <TableHead className="w-36 text-right">{t("defense.table.actions")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRules.map(({ rule, index }) => (
                    <TableRow key={`${rule.command}-${rule.scope}-${index}`}>
                      <TableCell className="font-mono text-xs font-medium">{rule.command}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{rule.matchType}</Badge>
                        {rule.matchType === "regex" && rule.regexFlags ? (
                          <span className="ml-2 font-mono text-xs text-muted-foreground">{rule.regexFlags}</span>
                        ) : null}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={badgeClass(rule.category)}>
                          {t(`defense.category.${rule.category}`, { defaultValue: rule.category })}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={badgeClass(rule.severity)}>
                          {t(`defense.severity.${rule.severity}`, { defaultValue: rule.severity })}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={badgeClass(rule.mode)}>
                          {t(`defense.mode.${rule.mode}`, { defaultValue: rule.mode })}
                        </Badge>
                      </TableCell>
                      <TableCell>{rule.scope}</TableCell>
                      <TableCell className="text-muted-foreground">{rule.note}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button variant="outline" size="sm" onClick={() => openEditRule(index)} disabled={saveMutation.isPending}>
                            <Pencil className="h-4 w-4" />
                            {t("defense.buttons.edit")}
                          </Button>
                          <Button variant="destructive" size="sm" onClick={() => setDeleteIndex(index)} disabled={saveMutation.isPending}>
                            <Trash2 className="h-4 w-4" />
                            {t("defense.buttons.delete")}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {filteredRules.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
                        {t("defense.noMatch")}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </CardContent>
      </Card>

      <Dialog open={policyDialogOpen} onOpenChange={setPolicyDialogOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>编辑策略元数据</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>名称</Label>
              <Input value={policy.name} onChange={(e) => updatePolicyField("name", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>来源</Label>
              <Input value={policy.source} onChange={(e) => updatePolicyField("source", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>版本</Label>
              <Input value={String(policy.version)} onChange={(e) => updatePolicyField("version", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>说明</Label>
              <textarea
                className="min-h-24 w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                value={policy.description}
                onChange={(e) => updatePolicyField("description", e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPolicyDialogOpen(false)}>关闭</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={ruleDialogOpen} onOpenChange={setRuleDialogOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editingIndex === null ? "新增规则" : "编辑规则"}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-2 md:grid-cols-2">
            <div className="space-y-2 md:col-span-2">
              <Label>命令关键字 / Regex</Label>
              <Input value={draftRule.command} onChange={(e) => updateDraftRule("command", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>匹配方式</Label>
              <select
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={draftRule.matchType}
                onChange={(e) => updateDraftRule("matchType", e.target.value)}
              >
                <option value="literal">literal</option>
                <option value="regex">regex</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>Regex Flags</Label>
              <Input
                value={draftRule.regexFlags}
                onChange={(e) => updateDraftRule("regexFlags", e.target.value)}
                placeholder="i / im / is"
                disabled={draftRule.matchType !== "regex"}
              />
            </div>
            <div className="space-y-2">
              <Label>分类</Label>
              <select
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={draftRule.category}
                onChange={(e) => updateDraftRule("category", e.target.value)}
              >
                <option value="oracle">oracle</option>
                <option value="linux">linux</option>
                <option value="filesystem">filesystem</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>作用域</Label>
              <Input value={draftRule.scope} onChange={(e) => updateDraftRule("scope", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>风险级别</Label>
              <select
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={draftRule.severity}
                onChange={(e) => updateDraftRule("severity", e.target.value)}
              >
                <option value="high">high</option>
                <option value="critical">critical</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>处理模式</Label>
              <select
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={draftRule.mode}
                onChange={(e) => updateDraftRule("mode", e.target.value)}
              >
                <option value="warn">warn</option>
                <option value="block">block</option>
              </select>
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label>备注</Label>
              <textarea
                className="min-h-24 w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                value={draftRule.note}
                onChange={(e) => updateDraftRule("note", e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRuleDialogOpen(false)} disabled={saveMutation.isPending}>取消</Button>
            <Button onClick={saveRule} disabled={saveMutation.isPending || !draftRule.command.trim() || !draftRule.scope.trim()}>
              保存规则
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteIndex !== null}
        title="删除规则"
        description="删除后会立即写回 dangerous_tool_policy.json。"
        destructive
        onConfirm={deleteRule}
        onCancel={() => setDeleteIndex(null)}
      />
    </div>
  );
}
