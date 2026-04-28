import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Skeleton } from "../components/ui/skeleton";
import { cn } from "../lib/utils";
import { useHostInventory, useRefreshHostInventory } from "../hooks/useHostInventory";
import { CheckCircle2, Database, HardDrive, LoaderCircle, RefreshCw, Server, ShieldAlert } from "lucide-react";

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
  if (status === "OPEN" || status === "MOUNTED" || status === "STARTED") {
    return "bg-emerald-600 text-white hover:bg-emerald-700";
  }
  if (status === "UNKNOWN") {
    return "bg-slate-500/12 text-slate-700 hover:bg-slate-500/20 dark:text-slate-300";
  }
  return "bg-rose-600 text-white hover:bg-rose-700";
}

export default function ServerHost() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data, isLoading } = useHostInventory();
  const refreshInventory = useRefreshHostInventory();
  const refreshedInventoryPathRef = useRef<string | null>(null);

  const hosts = data?.hosts ?? [];
  const runningHosts = hosts.filter((host) => host.host_status === "Running").length;
  const attentionHosts = hosts.filter((host) => host.host_status && host.host_status !== "Running").length;
  const totalDatabases = hosts.reduce((sum, host) => sum + (host.databases?.length ?? 0), 0);

  const handleRefresh = () => {
    if (refreshInventory.isPending || !data?.exists) {
      return;
    }
    refreshInventory.mutate(undefined, {
      onSuccess: (nextData) => {
        refreshedInventoryPathRef.current = nextData.inventory_path;
        queryClient.setQueryData(["host-inventory"], nextData);
      },
    });
  };

  useEffect(() => {
    if (isLoading || !data?.exists || !data.inventory_path) {
      return;
    }
    if (refreshInventory.isPending) {
      return;
    }
    if (refreshedInventoryPathRef.current === data.inventory_path) {
      return;
    }

    refreshedInventoryPathRef.current = data.inventory_path;
    handleRefresh();
  }, [data?.exists, data?.inventory_path, isLoading, queryClient, refreshInventory]);

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
          <div className="flex flex-wrap items-center justify-end gap-2">
            {data?.exists && (
              <Badge variant="secondary" className="max-w-full truncate">
                {data.workspace}
              </Badge>
            )}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={!data?.exists || refreshInventory.isPending}
            >
              <RefreshCw className={cn("h-4 w-4", refreshInventory.isPending && "animate-spin")} />
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
          ) : !data?.exists || hosts.length === 0 ? (
            <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
              {t("host.empty")}
            </div>
          ) : (
            <div className="space-y-4">
              {refreshInventory.isPending && (
                <div className="overflow-hidden rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-900/50 dark:bg-blue-950/30">
                  <div className="h-1 w-full animate-pulse bg-blue-500" />
                  <div className="flex items-center gap-2 px-4 py-3 text-sm text-blue-700 dark:text-blue-200">
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                    <span>{t("host.refreshing")}</span>
                  </div>
                </div>
              )}
              <div className="rounded-lg border bg-muted/20 px-4 py-3 text-xs text-muted-foreground">
                <span className="font-medium">{t("host.inventorySource")}:</span> {data.inventory_path}
              </div>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                {hosts.map((host) => {
                  const hostStatus = host.host_status ?? "unknown";
                  const hostStatusText = getHostStatusText(hostStatus);
                  const primaryDb = host.databases?.[0];
                  const databaseStatus = primaryDb?.database_status ?? "UNKNOWN";
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
                                <p className="text-xs text-muted-foreground">{databaseStatus}</p>
                              </div>
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
                              <span className="font-medium text-foreground">{primaryDb?.database_name ?? "-"}</span>
                            </div>
                            <div className="flex items-center justify-between gap-2">
                              <span>{t("host.database.version")}</span>
                              <span className="font-medium text-foreground">{primaryDb?.database_version ?? "-"}</span>
                            </div>
                            <div className="flex items-center justify-between gap-2">
                              <span>{t("host.database.deployment")}</span>
                              <span className="font-medium text-foreground">{t("host.database.singleInstance")}</span>
                            </div>
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
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
