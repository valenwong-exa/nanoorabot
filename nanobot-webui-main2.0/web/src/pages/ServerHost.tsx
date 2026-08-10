import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Skeleton } from "../components/ui/skeleton";
import { Switch } from "../components/ui/switch";
import { cn } from "../lib/utils";
import {
  useHostInventory,
  useHostInventoryRefreshConfig,
  useRefreshHostInventory,
  useUpdateHostInventory,
  useUpdateHostInventoryRefreshConfig,
} from "../hooks/useHostInventory";
import { CheckCircle2, Database, HardDrive, LoaderCircle, RefreshCw, Server, Settings2, ShieldAlert } from "lucide-react";
import ServerHostEdit from "./ServerHostEdit";

const DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES = 1;
const MIN_AUTO_REFRESH_INTERVAL_MINUTES = 1;
const MAX_AUTO_REFRESH_INTERVAL_MINUTES = 1440;
const CHAT_DATABASE_LIST_VISIBLE_STORAGE_KEY = "nanobot-chat-database-list-visible";
const CHAT_HOST_LIST_VISIBLE_STORAGE_KEY = "nanobot-chat-host-list-visible";

function getHostStatusTone(status: string) {
  switch (status) {
    case "Running":
      return "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300";
    case "unable login":
      return "bg-amber-500/12 text-amber-700 dark:text-amber-300";
    case "invalid":
      return "bg-rose-500/12 text-rose-700 dark:text-rose-300";
    default:
      return "bg-slate-500/12 text-slate-700 dark:text-slate-300";
  }
}

function getDatabaseStatusTone(status: string) {
  if (status === "OPEN" || status === "MOUNTED" || status === "STARTED" || status === "RUNNING") {
    return "bg-emerald-600 text-white hover:bg-emerald-700";
  }
  if (status === "UNKNOWN") {
    return "bg-slate-500/12 text-slate-700 hover:bg-slate-500/20 dark:text-slate-300";
  }
  return "bg-rose-600 text-white hover:bg-rose-700";
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

export default function ServerHost() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data, isLoading } = useHostInventory();
  const refreshConfigQuery = useHostInventoryRefreshConfig();
  const refreshInventory = useRefreshHostInventory();
  const updateInventory = useUpdateHostInventory();
  const updateRefreshConfig = useUpdateHostInventoryRefreshConfig();
  const lastSuccessAtRef = useRef<string | null>(null);
  const [autoRefreshIntervalDraft, setAutoRefreshIntervalDraft] = useState<string>(
    String(DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES),
  );
  const [maintenanceOpen, setMaintenanceOpen] = useState(false);
  const [showChatDatabaseList, setShowChatDatabaseList] = useState<boolean>(() => {
    if (typeof window === "undefined") {
      return true;
    }
    return window.localStorage.getItem(CHAT_DATABASE_LIST_VISIBLE_STORAGE_KEY) !== "false";
  });
  const [showChatHostList, setShowChatHostList] = useState<boolean>(() => {
    if (typeof window === "undefined") {
      return true;
    }
    return window.localStorage.getItem(CHAT_HOST_LIST_VISIBLE_STORAGE_KEY) !== "false";
  });

  const monitoredDatabases = data?.database_inventory ?? [];
  const hosts = data?.hosts ?? [];
  const hasHosts = hosts.length > 0;
  const hasMonitoredDatabases = monitoredDatabases.length > 0;
  const hasInventoryContent = hasHosts || hasMonitoredDatabases;
  const runningHosts = hosts.filter((host) => host.host_status === "Running").length;
  const attentionHosts = hosts.filter((host) => host.host_status && host.host_status !== "Running").length;
  const hostDatabaseCount = hosts.reduce((sum, host) => sum + (host.databases?.length ?? 0), 0);
  const totalDatabases = monitoredDatabases.length > 0 ? monitoredDatabases.length : hostDatabaseCount;
  const runningMonitoredDatabases = monitoredDatabases.filter((database) => {
    const status = database.database_status ?? "UNKNOWN";
    return status === "RUNNING" || status === "OPEN" || status === "MOUNTED" || status === "STARTED";
  }).length;
  const attentionMonitoredDatabases = monitoredDatabases.filter((database) => {
    const status = database.database_status ?? "UNKNOWN";
    return status !== "RUNNING" && status !== "OPEN" && status !== "MOUNTED" && status !== "STARTED";
  }).length;
  const autoRefreshEnabled = refreshConfigQuery.data?.enabled ?? false;
  const parsedInterval = Number.parseInt(autoRefreshIntervalDraft, 10);
  const autoRefreshIntervalValue = Number.isFinite(parsedInterval)
    ? Math.min(
        MAX_AUTO_REFRESH_INTERVAL_MINUTES,
        Math.max(MIN_AUTO_REFRESH_INTERVAL_MINUTES, parsedInterval),
      )
    : DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES;
  const autoRefreshConfigBusy = refreshConfigQuery.isLoading || updateRefreshConfig.isPending;
  const refreshInProgress = refreshInventory.isPending || refreshConfigQuery.data?.isRunning === true;

  const handleRefresh = () => {
    if (refreshInProgress || !data?.exists) {
      return;
    }
    refreshInventory.mutate(undefined, {
      onSuccess: (nextData) => {
        queryClient.setQueryData(["host-inventory"], nextData);
        void queryClient.invalidateQueries({ queryKey: ["host-inventory", "refresh-config"] });
      },
      onSettled: () => {
        void queryClient.invalidateQueries({ queryKey: ["host-inventory", "refresh-config"] });
      },
    });
  };

  useEffect(() => {
    const nextInterval = refreshConfigQuery.data?.intervalMinutes;
    if (typeof nextInterval !== "number") {
      return;
    }
    setAutoRefreshIntervalDraft(String(nextInterval));
  }, [refreshConfigQuery.data?.intervalMinutes]);

  useEffect(() => {
    const lastSuccessAt = refreshConfigQuery.data?.lastSuccessAt ?? null;
    if (!lastSuccessAt) {
      return;
    }
    if (lastSuccessAtRef.current === lastSuccessAt) {
      return;
    }
    lastSuccessAtRef.current = lastSuccessAt;
    void queryClient.invalidateQueries({ queryKey: ["host-inventory"] });
  }, [queryClient, refreshConfigQuery.data?.lastSuccessAt]);

  useEffect(() => {
    window.localStorage.setItem(CHAT_DATABASE_LIST_VISIBLE_STORAGE_KEY, showChatDatabaseList ? "true" : "false");
  }, [showChatDatabaseList]);

  useEffect(() => {
    window.localStorage.setItem(CHAT_HOST_LIST_VISIBLE_STORAGE_KEY, showChatHostList ? "true" : "false");
  }, [showChatHostList]);

  const handleUpdateAutoRefreshConfig = async (patch: {
    enabled?: boolean;
    intervalMinutes?: number;
  }) => {
    const nextConfig = await updateRefreshConfig.mutateAsync(patch);
    queryClient.setQueryData(["host-inventory", "refresh-config"], nextConfig);
    setAutoRefreshIntervalDraft(String(nextConfig.intervalMinutes));
  };

  const getHostStatusText = (status?: string) => {
    switch (status) {
      case "Running":
        return t("host.status.running");
      case "unable login":
        return t("host.status.unableLogin");
      case "invalid":
        return t("host.status.invalid");
      default:
        return t("host.status.unknown");
    }
  };

  const statCards = [
    {
      label: t("host.stats.totalHosts"),
      value: hosts.length,
      sub: t("host.stats.managedHosts"),
      icon: Server,
      iconColor: "text-blue-500",
      iconBg: "bg-blue-50 dark:bg-blue-950/50",
    },
    {
      label: t("host.stats.runningHosts"),
      value: runningHosts,
      sub: t("host.status.running"),
      icon: CheckCircle2,
      iconColor: "text-emerald-500",
      iconBg: "bg-emerald-50 dark:bg-emerald-950/50",
    },
    {
      label: t("host.stats.databaseCount"),
      value: totalDatabases,
      sub: t("host.database.running"),
      icon: Database,
      iconColor: "text-violet-500",
      iconBg: "bg-violet-50 dark:bg-violet-950/50",
    },
    {
      label: t("host.stats.attentionHosts"),
      value: attentionHosts,
      sub: t("host.status.attention"),
      icon: ShieldAlert,
      iconColor: "text-amber-500",
      iconBg: "bg-amber-50 dark:bg-amber-950/50",
    },
  ];

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
        <CardHeader className="flex flex-row items-center justify-between gap-4">
          <div>
            <CardTitle>{t("host.title")}</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">{t("host.subtitle")}</p>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-3">
            <div className="flex items-center gap-3 rounded-lg border px-3 py-2">
              <div className="flex items-center gap-2">
                <Switch
                  checked={autoRefreshEnabled}
                    onCheckedChange={(checked) => {
                      void handleUpdateAutoRefreshConfig({ enabled: checked });
                    }}
                    disabled={autoRefreshConfigBusy}
                />
                <Label className="text-sm">{t("host.autoRefresh.label")}</Label>
              </div>
              <div className="flex items-center gap-2">
                <Label htmlFor="host-auto-refresh-interval" className="text-sm text-muted-foreground">
                  {t("host.autoRefresh.intervalLabel")}
                </Label>
                <Input
                  id="host-auto-refresh-interval"
                  type="number"
                  min={MIN_AUTO_REFRESH_INTERVAL_MINUTES}
                  max={MAX_AUTO_REFRESH_INTERVAL_MINUTES}
                    value={autoRefreshIntervalDraft}
                    disabled={autoRefreshConfigBusy}
                  onChange={(event) => {
                      setAutoRefreshIntervalDraft(event.target.value);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        void handleUpdateAutoRefreshConfig({
                          intervalMinutes: autoRefreshIntervalValue,
                        });
                      }
                  }}
                  onBlur={() => {
                      void handleUpdateAutoRefreshConfig({
                        intervalMinutes: autoRefreshIntervalValue,
                      });
                  }}
                  className="h-8 w-24"
                />
                <span className="text-sm text-muted-foreground">{t("host.autoRefresh.intervalUnit")}</span>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3 rounded-lg border px-3 py-2">
              <Label className="text-sm">{t("host.chatPanels.label")}</Label>
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <input
                  type="checkbox"
                  checked={showChatHostList}
                  onChange={(event) => setShowChatHostList(event.target.checked)}
                  className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                />
                <span>{t("chat.hostList")}</span>
              </label>
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <input
                  type="checkbox"
                  checked={showChatDatabaseList}
                  onChange={(event) => setShowChatDatabaseList(event.target.checked)}
                  className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                />
                <span>{t("chat.databaseList")}</span>
              </label>
            </div>
            {data?.exists && (
              <Badge variant="secondary" className="max-w-full truncate">
                {data.workspace}
              </Badge>
            )}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setMaintenanceOpen(true)}
              disabled={!data?.exists}
            >
              <Settings2 />
              {t("host.maintenance.button")}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={!data?.exists || refreshInProgress}
            >
              <RefreshCw className={cn("h-4 w-4", refreshInProgress && "animate-spin")} />
              {t("common.refresh")}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-[280px] w-full" />
              ))}
            </div>
          ) : !data?.exists || !hasInventoryContent ? (
            <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
              {t("host.empty")}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg border bg-muted/20 px-4 py-2 text-xs text-muted-foreground">
                {refreshInProgress && (
                  <span className="inline-flex shrink-0 items-center gap-1.5 text-blue-700 dark:text-blue-200">
                    <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                    <span>{t("host.refreshing")}</span>
                  </span>
                )}
                <span className="inline-flex min-w-0 max-w-full flex-1 items-center gap-1">
                  <span className="shrink-0 font-medium">{t("host.inventorySource")}:</span>
                  <span className="truncate" title={data.inventory_path}>
                    {data.inventory_path}
                  </span>
                </span>
                <span className="inline-flex shrink-0 items-center gap-1">
                  <span className="font-medium">{t("host.autoRefresh.statusLabel")}:</span>
                  <span>
                    {autoRefreshEnabled
                      ? t("host.autoRefresh.statusEnabled", { minutes: autoRefreshIntervalValue })
                      : t("host.autoRefresh.statusDisabled")}
                  </span>
                </span>
                <span className="inline-flex shrink-0 items-center gap-1">
                  <span className="font-medium">{t("host.autoRefresh.lastSuccessLabel")}:</span>
                  <span>{formatDateTime(refreshConfigQuery.data?.lastSuccessAt)}</span>
                </span>
              </div>
              {refreshConfigQuery.data?.lastError ? (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
                  <span className="font-medium">{t("host.autoRefresh.lastErrorLabel")}:</span>{" "}
                  {refreshConfigQuery.data.lastError}
                </div>
              ) : null}
              {hasMonitoredDatabases ? (
              <div className="rounded-xl border bg-background/70 p-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/10">
                      <Database className="h-5 w-5 text-violet-500" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold">{t("host.monitored.title")}</h3>
                      <p className="text-xs text-muted-foreground">
                        {t("host.monitored.subtitle", { count: monitoredDatabases.length })}
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <Badge variant="outline">{t("host.monitored.total", { count: monitoredDatabases.length })}</Badge>
                    <Badge variant="outline" className="border-emerald-500/30 text-emerald-700 dark:text-emerald-300">
                      {t("host.monitored.running", { count: runningMonitoredDatabases })}
                    </Badge>
                    <Badge variant="outline" className="border-amber-500/30 text-amber-700 dark:text-amber-300">
                      {t("host.monitored.attention", { count: attentionMonitoredDatabases })}
                    </Badge>
                  </div>
                </div>

                <div className="mt-4">
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                    {monitoredDatabases.map((database, index) => {
                      const databaseStatus = database.database_status ?? "UNKNOWN";
                      return (
                        <Card
                          key={`${database.sqlcl_saveconnname ?? database.database_name ?? "database"}-${index}`}
                          className="overflow-hidden border-border/70 bg-card/90"
                        >
                          <CardContent className="p-4">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="flex items-center gap-2">
                                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-500/10">
                                    <Database className="h-4 w-4 text-violet-500" />
                                  </div>
                                  <div className="min-w-0">
                                    <h3 className="truncate text-base font-semibold">{database.database_name ?? "-"}</h3>
                                    <div className="mt-1">
                                      <span className="inline-flex max-w-full items-center rounded-md border border-sky-200 bg-sky-50 px-2 py-0.5 text-sm font-semibold text-sky-700 dark:border-sky-900/40 dark:bg-sky-950/30 dark:text-sky-300">
                                        <span className="truncate">{database.sqlcl_saveconnname || "-"}</span>
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              </div>
                              <Badge className={getDatabaseStatusTone(databaseStatus)}>
                                {databaseStatus}
                              </Badge>
                            </div>

                            <div className="mt-4 space-y-2 text-xs text-muted-foreground">
                              <div className="flex items-center justify-between gap-2">
                                <span>{t("common.status")}</span>
                                <span className="font-medium text-foreground">{databaseStatus}</span>
                              </div>
                              <div className="flex items-center justify-between gap-2">
                                <span>SQLcl</span>
                                <span className="font-semibold text-sky-700 dark:text-sky-300">
                                  {database.sqlcl_saveconnname || "-"}
                                </span>
                              </div>
                              <div className="flex items-center justify-between gap-2">
                                <span>{t("host.database.version")}</span>
                                <span className="font-medium text-foreground">
                                  {database.database_version || "-"}
                                </span>
                              </div>
                              <div className="flex items-center justify-between gap-2">
                                <span>{t("host.monitored.lastChecked")}</span>
                                <span className="font-medium text-foreground">
                                  {formatDateTime(database.last_checked_at)}
                                </span>
                              </div>
                              <div className="flex items-start justify-between gap-2">
                                <span>{t("host.monitored.lastResponse")}</span>
                                <span className="max-w-[65%] break-all text-right font-medium text-foreground">
                                  {database.probe_output || "-"}
                                </span>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                </div>
              </div>
              ) : null}
              {hasHosts ? (
              <>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold">{t("host.title")}</h3>
                  <p className="text-xs text-muted-foreground">{t("host.hostsSubtitle")}</p>
                </div>
                <Badge variant="outline">{t("host.monitored.totalHosts", { count: hosts.length })}</Badge>
              </div>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                {hosts.map((host) => {
                  const hostStatus = host.host_status ?? "unknown";
                  const hostStatusText = getHostStatusText(hostStatus);
                  const databases = host.databases ?? [];
                  return (
                    <Card key={host.host_name} className="overflow-hidden border-border/70 bg-card/90">
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/12">
                                <Server className="h-4 w-4 text-primary" />
                              </div>
                              <div className="min-w-0">
                                <h3 className="truncate text-base font-semibold">{host.host_name}</h3>
                                <p className="truncate text-xs text-muted-foreground">{host.os_type}</p>
                              </div>
                            </div>
                          </div>
                          <Badge
                            variant="secondary"
                            className={cn(
                              "shrink-0 border-0",
                              getHostStatusTone(hostStatus)
                            )}
                          >
                            {hostStatusText}
                          </Badge>
                        </div>

                        <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                          <div className="rounded-lg bg-muted/40 p-3">
                            <p className="text-xs text-muted-foreground">{t("host.labels.status")}</p>
                            <p className="mt-1 truncate font-medium">{hostStatusText}</p>
                          </div>
                          <div className="rounded-lg bg-muted/40 p-3">
                            <p className="text-xs text-muted-foreground">{t("host.labels.ip")}</p>
                            <p className="mt-1 truncate font-medium">{host.ip}</p>
                          </div>
                          <div className="rounded-lg bg-muted/40 p-3">
                            <p className="text-xs text-muted-foreground">{t("host.labels.defaultUser")}</p>
                            <p className="mt-1 truncate font-medium">{host.default_user}</p>
                          </div>
                          <div className="rounded-lg bg-muted/40 p-3">
                            <p className="text-xs text-muted-foreground">{t("host.labels.aliasCount")}</p>
                            <p className="mt-1 font-medium">{host.aliases?.length ?? 0}</p>
                          </div>
                        </div>

                        <div className="mt-4 rounded-xl border bg-background/70 p-3">
                          <div className="flex items-center justify-between gap-3">
                            <div className="flex items-center gap-2">
                              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/10">
                                <Database className="h-4 w-4 text-violet-500" />
                              </div>
                              <div>
                                <p className="text-sm font-medium">{t("host.database.title")}</p>
                                <p className="text-xs text-muted-foreground">
                                  {databases.length > 0 ? `${databases.length} database(s)` : t("host.status.unknown")}
                                </p>
                              </div>
                            </div>
                          </div>

                          <div className="mt-3 space-y-3">
                            {databases.length > 0 ? (
                              databases.map((database, index) => {
                                const databaseStatus = database.database_status ?? "UNKNOWN";
                                return (
                                  <div
                                    key={`${host.host_name}-${database.database_name}-${index}`}
                                    className="rounded-lg border bg-muted/30 p-3"
                                  >
                                    <div className="flex items-center justify-between gap-3">
                                      <div className="min-w-0">
                                        <p className="truncate text-sm font-medium text-foreground">
                                          {database.database_name}
                                        </p>
                                        <p className="truncate text-xs text-muted-foreground">
                                          {database.sqlcl_saveconnname || "-"}
                                        </p>
                                      </div>
                                      <Badge className={getDatabaseStatusTone(databaseStatus)}>
                                        {databaseStatus}
                                      </Badge>
                                    </div>

                                    <div className="mt-3 space-y-2 text-xs text-muted-foreground">
                                      <div className="flex items-center justify-between gap-2">
                                        <span>{t("common.status")}</span>
                                        <span className="font-medium text-foreground">{databaseStatus}</span>
                                      </div>
                                      <div className="flex items-center justify-between gap-2">
                                        <span>{t("host.database.primary")}</span>
                                        <span className="font-medium text-foreground">
                                          {database.database_name ?? "-"}
                                        </span>
                                      </div>
                                      <div className="flex items-center justify-between gap-2">
                                        <span>{t("host.database.version")}</span>
                                        <span className="font-medium text-foreground">
                                          {database.database_version ?? "-"}
                                        </span>
                                      </div>
                                      <div className="flex items-center justify-between gap-2">
                                        <span>SQLcl</span>
                                        <span className="font-medium text-foreground">
                                          {database.sqlcl_saveconnname || "-"}
                                        </span>
                                      </div>
                                      <div className="flex items-center justify-between gap-2">
                                        <span>{t("host.database.deployment")}</span>
                                        <span className="font-medium text-foreground">
                                          {t("host.database.singleInstance")}
                                        </span>
                                      </div>
                                    </div>
                                  </div>
                                );
                              })
                            ) : (
                              <div className="rounded-lg border border-dashed px-3 py-4 text-center text-xs text-muted-foreground">
                                {t("common.noData")}
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="mt-4 rounded-lg border border-dashed p-3">
                          <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                            <HardDrive className="h-4 w-4 text-primary" />
                            {t("host.labels.aliases")}
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {(host.aliases ?? []).map((alias) => (
                              <Badge key={alias} variant="outline" className="max-w-full truncate">
                                {alias}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
              </>
              ) : null}
            </div>
          )}
        </CardContent>
      </Card>
      {maintenanceOpen ? (
        <ServerHostEdit
          open
          onOpenChange={setMaintenanceOpen}
          inventory={data}
          isSaving={updateInventory.isPending}
          isRefreshInProgress={refreshInProgress}
          onSave={async (payload) => {
            const saved = await updateInventory.mutateAsync(payload);
            queryClient.setQueryData(["host-inventory"], saved);
            return saved;
          }}
        />
      ) : null}
    </div>
  );
}
