import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Skeleton } from "../components/ui/skeleton";
import { useAuditSessions } from "../hooks/useAuditSessions";
import { AlertCircle, CheckCircle2, FileText, Filter, MessagesSquare, RotateCcw, ShieldCheck } from "lucide-react";
import { cn } from "../lib/utils";

function formatTime(value: string) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function Audit() {
  const { t } = useTranslation();
  const { data, isLoading, isError, error, refetch, isFetching } = useAuditSessions();
  const [keyword, setKeyword] = useState("");
  const [sessionTypeFilter, setSessionTypeFilter] = useState("all");
  const [roleFilter, setRoleFilter] = useState("all");

  const files = data?.files ?? [];
  const sessionTypes = useMemo(
    () => Array.from(new Set(files.map((file) => file.session_type).filter(Boolean))).sort(),
    [files]
  );
  const roles = useMemo(
    () =>
      Array.from(
        new Set(
          files.flatMap((file) => file.records.map((record) => record.role).filter(Boolean))
        )
      ).sort(),
    [files]
  );

  const visibleFiles = useMemo(() => {
    const query = keyword.trim().toLowerCase();
    return files
      .filter((file) => sessionTypeFilter === "all" || file.session_type === sessionTypeFilter)
      .map((file) => {
        const filteredRecords = file.records.filter((record) => {
          if (roleFilter !== "all" && record.role !== roleFilter) {
            return false;
          }
          if (!query) {
            return true;
          }
          const haystack = [record.role, record.summary, record.timestamp, record.search_text]
            .join(" ")
            .toLowerCase();
          return haystack.includes(query);
        });
        const fileMatched =
          !!query &&
          [file.file_name, file.session_key, file.session_type, file.created_at, file.updated_at]
            .join(" ")
            .toLowerCase()
            .includes(query);
        return {
          ...file,
          records: fileMatched && roleFilter === "all" ? file.records : filteredRecords,
          fileMatched,
        };
      })
      .filter((file) => file.records.length > 0 || file.fileMatched);
  }, [files, keyword, roleFilter, sessionTypeFilter]);

  const totalRecords = files.reduce((sum, file) => sum + file.records.length, 0);
  const visibleRecords = visibleFiles.reduce((sum, file) => sum + file.records.length, 0);
  const webFiles = files.filter((file) => file.session_type === "websocket").length;
  const externalFiles = files.filter((file) => file.session_type !== "websocket").length;
  const errorMessage = error instanceof Error ? error.message : t("audit.error");

  const statCards = [
    {
      label: t("audit.stats.sessionFiles"),
      value: files.length,
      sub: t("audit.stats.allLines"),
      icon: FileText,
      iconColor: "text-blue-500",
      iconBg: "bg-blue-50 dark:bg-blue-950/50",
    },
    {
      label: t("audit.stats.auditRows"),
      value: totalRecords,
      sub: `${t("audit.stats.visibleRows")}: ${visibleRecords}`,
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
          ) : isError ? (
            <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                  <div className="space-y-1">
                    <div className="font-medium text-destructive">{t("audit.loadFailed")}</div>
                    <div className="text-muted-foreground">{errorMessage}</div>
                  </div>
                </div>
                <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
                  <RotateCcw className={cn("h-4 w-4", isFetching && "animate-spin")} />
                  {t("audit.retry")}
                </Button>
              </div>
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
                <div className="w-40">
                  <Select value={sessionTypeFilter} onValueChange={setSessionTypeFilter}>
                    <SelectTrigger>
                      <SelectValue placeholder={t("audit.filters.sessionType")} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">{t("audit.filters.allSessionTypes")}</SelectItem>
                      {sessionTypes.map((value) => (
                        <SelectItem key={value} value={value}>
                          {value}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="w-36">
                  <Select value={roleFilter} onValueChange={setRoleFilter}>
                    <SelectTrigger>
                      <SelectValue placeholder={t("audit.filters.role")} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">{t("audit.filters.allRoles")}</SelectItem>
                      {roles.map((value) => (
                        <SelectItem key={value} value={value}>
                          {value}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span>{t("audit.filters.visibleFiles")}: {visibleFiles.length}</span>
                <span>{t("audit.filters.visibleRecords")}: {visibleRecords}</span>
              </div>

              {visibleFiles.length === 0 ? (
                <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
                  {t("audit.noMatch")}
                </div>
              ) : (
                visibleFiles.map((file) => (
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
                          <Badge variant="outline">
                            {t("audit.matchCount")}: {file.records.length}
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
