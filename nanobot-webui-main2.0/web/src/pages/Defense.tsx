import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { AlertTriangle, Plus, Search, Shield, ShieldAlert, Trash2, Pencil } from "lucide-react";
import { cn } from "../lib/utils";

type DefenseRule = {
  command: string;
  category: "oracle" | "linux" | "filesystem";
  severity: "high" | "critical";
  mode: "warn" | "block";
  scope: string;
  note: string;
};

const RULES: DefenseRule[] = [
  { command: "truncate table", category: "oracle", severity: "critical", mode: "block", scope: "SQL", note: "高风险数据清空操作" },
  { command: "drop table", category: "oracle", severity: "critical", mode: "block", scope: "SQL", note: "直接删除表结构与数据" },
  { command: "delete from", category: "oracle", severity: "high", mode: "warn", scope: "SQL", note: "大批量删除需要人工确认" },
  { command: "update ... without where", category: "oracle", severity: "high", mode: "warn", scope: "SQL", note: "避免整表更新" },
  { command: "rm -rf", category: "filesystem", severity: "critical", mode: "block", scope: "Shell", note: "危险递归删除命令" },
  { command: "shutdown -h now", category: "linux", severity: "critical", mode: "block", scope: "Shell", note: "主机关机命令" },
  { command: "reboot", category: "linux", severity: "high", mode: "warn", scope: "Shell", note: "主机重启前要求提示" },
];

export default function Defense() {
  const { t } = useTranslation();
  const [keyword, setKeyword] = useState("");

  const filteredRules = useMemo(() => {
    const query = keyword.trim().toLowerCase();
    if (!query) return RULES;
    return RULES.filter((rule) =>
      [rule.command, rule.category, rule.severity, rule.mode, rule.scope, rule.note]
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }, [keyword]);

  const statCards = [
    {
      label: t("defense.stats.totalRules"),
      value: RULES.length,
      sub: t("defense.stats.demoPolicy"),
      icon: Shield,
      iconColor: "text-blue-500",
      iconBg: "bg-blue-50 dark:bg-blue-950/50",
    },
    {
      label: t("defense.stats.blockRules"),
      value: RULES.filter((rule) => rule.mode === "block").length,
      sub: t("defense.block"),
      icon: ShieldAlert,
      iconColor: "text-destructive",
      iconBg: "bg-destructive/10",
    },
    {
      label: t("defense.stats.warnRules"),
      value: RULES.filter((rule) => rule.mode === "warn").length,
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
            <Button variant="outline" size="sm">
              <Pencil className="h-4 w-4" />
              {t("defense.buttons.editPolicy")}
            </Button>
            <Button size="sm">
              <Plus className="h-4 w-4" />
              {t("defense.buttons.addRule")}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="rounded-lg border bg-muted/20 px-4 py-3 text-xs text-muted-foreground">
              {t("defense.banner")}
            </div>

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
                    <TableHead>{t("defense.table.category")}</TableHead>
                    <TableHead>{t("defense.table.severity")}</TableHead>
                    <TableHead>{t("defense.table.mode")}</TableHead>
                    <TableHead>{t("defense.table.scope")}</TableHead>
                    <TableHead>{t("defense.table.note")}</TableHead>
                    <TableHead className="w-36 text-right">{t("defense.table.actions")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRules.map((rule) => (
                    <TableRow key={`${rule.command}-${rule.scope}`}>
                      <TableCell className="font-mono text-xs font-medium">{rule.command}</TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={badgeClass(rule.category)}>
                          {t(`defense.category.${rule.category}`)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={badgeClass(rule.severity)}>
                          {t(`defense.severity.${rule.severity}`)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={badgeClass(rule.mode)}>
                          {t(`defense.mode.${rule.mode}`)}
                        </Badge>
                      </TableCell>
                      <TableCell>{rule.scope}</TableCell>
                      <TableCell className="text-muted-foreground">{rule.note}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button variant="outline" size="sm">
                            <Pencil className="h-4 w-4" />
                            {t("defense.buttons.edit")}
                          </Button>
                          <Button variant="destructive" size="sm">
                            <Trash2 className="h-4 w-4" />
                            {t("defense.buttons.delete")}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {filteredRules.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
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
    </div>
  );
}
