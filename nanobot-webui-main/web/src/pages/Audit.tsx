import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "../components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Skeleton } from "../components/ui/skeleton";
import { useAuditSessions } from "../hooks/useAuditSessions";
import { CheckCircle2, FileText, Filter, MessagesSquare, ShieldCheck } from "lucide-react";
import { cn } from "../lib/utils";

function formatTime(value: string) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function Audit() {
  const { t } = useTranslation();
  const { data, isLoading } = useAuditSessions();
  const [keyword, setKeyword] = useState("");

  const files = data?.files ?? [];
  const filteredFiles = useMemo(() => {
    const query = keyword.trim().toLowerCase();
    if (!query) return files;
    return files
      .map((file) => ({
        ...file,
        records: file.records.filter((record) => {
          const haystack = [
            file.file_name,
            file.session_key,
            file.session_type,
            record.role,
            record.summary,
            record.timestamp,
          ]
            .join(" ")
            .toLowerCase();
          return haystack.includes(query);
        }),
      }))
      .filter((file) => file.records.length > 0);
  }, [files, keyword]);

  const totalRecords = files.reduce((sum, file) => sum + file.records.length, 0);
  const webFiles = files.filter((file) => file.session_type === "web").length;
  const externalFiles = files.filter((file) => file.session_type !== "web").length;

  const statCards = [
    {
      label: t("audit.stats.sessionFiles"),
      value: files.length,
      sub: t("audit.stats.latest20Lines"),
      icon: FileText,
      iconColor: "text-blue-500",
      iconBg: "bg-blue-50 dark:bg-blue-950/50",
    },
    {
      label: t("audit.stats.auditRows"),
      value: totalRecords,
      sub: t("audit.stats.visibleRows"),
      icon: MessagesSquare,
      iconColor: "text-violet-500",
      iconBg: "bg-violet-50 dark:bg-violet-950/50",
    },
    {
      label: t("audit.stats.webSessions"),
      value: webFiles,
      sub: t("audit.stats.browserGenerated"),
      icon: CheckCircle2,
      iconColor: "text-emerald-500",
      iconBg: "bg-emerald-50 dark:bg-emerald-950/50",
    },
    {
      label: t("audit.stats.externalSessions"),
      value: externalFiles,
      sub: t("audit.stats.socialOrExternal"),
      icon: ShieldCheck,
      iconColor: "text-amber-500",
      iconBg: "bg-amber-50 dark:bg-amber-950/50",
    },
  ];

  const roleClass = (role: string) =>
    ({
      user: "bg-blue-500/10 text-blue-700 dark:text-blue-300",
      assistant: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
      tool: "bg-violet-500/10 text-violet-700 dark:text-violet-300",
      metadata: "bg-amber-500/10 text-amber-700 dark:text-amber-300",
      invalid: "bg-destructive/10 text-destructive",
    }[role] ?? "bg-muted text-muted-foreground");

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {statCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label} className="overflow-hidden">
              <CardContent className="p-3 sm:p-5">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-xs font-medium leading-snug text-muted-foreground">{stat.label}</p>
                    {isLoading ? (
                      <Skeleton className="mt-1.5 h-7 w-12" />
                    ) : (
                      <div className="mt-1 text-xl font-bold tracking-tight sm:text-2xl">{stat.value}</div>
                    )}
                    <p className="mt-0.5 text-xs text-muted-foreground">{stat.sub}</p>
                  </div>
                  <div className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg", stat.iconBg)}>
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
            <CardTitle>{t("audit.title")}</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">{t("audit.subtitle")}</p>
          </div>
          {data?.exists && (
            <Badge variant="secondary" className="max-w-full truncate">
              {data.workspace}
            </Badge>
          )}
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-72 w-full" />
            </div>
          ) : !data?.exists || files.length === 0 ? (
            <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
              {t("audit.empty")}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="rounded-lg border bg-muted/20 px-4 py-3 text-xs text-muted-foreground">
                <span className="font-medium">{t("audit.source")}:</span> {data.sessions_dir}
              </div>

              <div className="flex items-center gap-3 rounded-lg border bg-background/60 p-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                  <Filter className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1">
                  <Input
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    placeholder={t("audit.filterPlaceholder")}
                  />
                </div>
              </div>

              {filteredFiles.length === 0 ? (
                <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
                  {t("audit.noMatch")}
                </div>
              ) : (
                filteredFiles.map((file) => (
                  <Card key={file.file_name} className="overflow-hidden border-border/70">
                    <CardHeader className="space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <CardTitle className="text-base">{file.file_name}</CardTitle>
                          <p className="mt-1 text-sm text-muted-foreground">
                            {file.session_key || file.session_type}
                          </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="secondary">{file.session_type}</Badge>
                          <Badge variant="outline">
                            {t("audit.lineCount")}: {file.line_count}
                          </Badge>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                        <span>{t("audit.createdAt")}: {formatTime(file.created_at)}</span>
                        <span>{t("audit.updatedAt")}: {formatTime(file.updated_at)}</span>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="overflow-x-auto rounded-lg border">
                        <table className="w-full min-w-[760px] border-collapse text-sm">
                          <thead className="bg-muted/50">
                            <tr className="text-left">
                              <th className="px-3 py-2 font-medium">{t("audit.table.line")}</th>
                              <th className="px-3 py-2 font-medium">{t("audit.table.role")}</th>
                              <th className="px-3 py-2 font-medium">{t("audit.table.time")}</th>
                              <th className="px-3 py-2 font-medium">{t("audit.table.summary")}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {file.records.map((record) => (
                              <tr key={`${file.file_name}-${record.line_number}`} className="border-t align-top">
                                <td className="px-3 py-2 text-xs text-muted-foreground">{record.line_number}</td>
                                <td className="px-3 py-2">
                                  <Badge variant="secondary" className={roleClass(record.role)}>
                                    {record.role}
                                  </Badge>
                                </td>
                                <td className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap">
                                  {formatTime(record.timestamp)}
                                </td>
                                <td className="px-3 py-2 leading-6">{record.summary || "-"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
