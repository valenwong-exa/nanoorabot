import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { SecretInput } from "../components/shared/SecretInput";
import { useOracleConfig, useSaveOracleConfig, useTestOracleConnection } from "../hooks/useOracleConfig";
import { AlertCircle, CheckCircle2, Database, Loader2, PlugZap, Save, Wifi } from "lucide-react";

const DEFAULT_FORM = {
  user: "valen",
  password: "oracle",
  host: "192.168.56.101",
  port: "1521",
  serviceName: "aidemo_pdb",
};

export default function DatabaseConfig() {
  const { t } = useTranslation();
  const [form, setForm] = useState(DEFAULT_FORM);
  const { data, error, isLoading } = useOracleConfig();
  const saveMutation = useSaveOracleConfig();
  const testMutation = useTestOracleConnection();

  useEffect(() => {
    if (!data) {
      return;
    }
    setForm({
      user: data.user,
      password: data.password,
      host: data.host,
      port: String(data.port),
      serviceName: data.serviceName,
    });
  }, [data]);

  const updateField = (key: keyof typeof form, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const loadErrorMessage = (
    error as { response?: { data?: { detail?: string } } } | null
  )?.response?.data?.detail;

  const canSubmit = Boolean(
    form.user.trim() &&
      form.password &&
      form.host.trim() &&
      form.port.trim() &&
      form.serviceName.trim(),
  );

  const connectString = useMemo(
    () => `${form.user || "-"}${form.password ? `/${form.password}` : ""}@${form.host || "-"}:${form.port || "-"}${form.serviceName ? `/${form.serviceName}` : ""}`,
    [form],
  );

  const currentDsn = useMemo(
    () => `${form.host || "-"}:${form.port || "-"}${form.serviceName ? `/${form.serviceName}` : ""}`,
    [form.host, form.port, form.serviceName],
  );

  const latestStatus = testMutation.data
    ? {
        tone: "success" as const,
        message: testMutation.data.message,
        extra: testMutation.data.serverVersion
          ? `${t("databaseConfig.serverVersion")}: ${testMutation.data.serverVersion}`
          : testMutation.data.dsn,
      }
    : testMutation.isError
      ? {
          tone: "error" as const,
          message:
            (testMutation.error as { response?: { data?: { detail?: string } } })?.response?.data
              ?.detail ?? t("databaseConfig.messages.testFailed"),
          extra: currentDsn,
        }
      : null;

  const latestMetadata = testMutation.data
    ? [
        {
          label: t("databaseConfig.metadata.serverVersion"),
          value: testMutation.data.serverVersion || t("databaseConfig.runtime.notAvailable"),
        },
        {
          label: t("databaseConfig.metadata.characterSet"),
          value: testMutation.data.characterSet || t("databaseConfig.runtime.notAvailable"),
        },
        {
          label: t("databaseConfig.metadata.rac"),
          value:
            testMutation.data.isRac === null
              ? t("databaseConfig.runtime.notAvailable")
              : testMutation.data.isRac
                ? t("databaseConfig.values.yes")
                : t("databaseConfig.values.no"),
        },
        {
          label: t("databaseConfig.metadata.multitenant"),
          value:
            testMutation.data.isMultitenant === null
              ? t("databaseConfig.runtime.notAvailable")
              : testMutation.data.isMultitenant
                ? t("databaseConfig.values.yes")
                : t("databaseConfig.values.no"),
        },
      ]
    : [];

  const submitPayload = {
    user: form.user.trim(),
    password: form.password,
    host: form.host.trim(),
    port: Number(form.port),
    serviceName: form.serviceName.trim(),
  };

  const handleTest = async () => {
    if (!canSubmit) {
      return;
    }
    await testMutation.mutateAsync(submitPayload);
  };

  const handleSave = async () => {
    if (!canSubmit) {
      return;
    }
    await saveMutation.mutateAsync(submitPayload);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("databaseConfig.title")}</h1>
          <p className="text-sm text-muted-foreground">
            {t("databaseConfig.subtitle")}
          </p>
        </div>
        <Badge variant="secondary" className="w-fit">
          {t("databaseConfig.badge")}
        </Badge>
      </div>

      <Card className="overflow-hidden border-red-200/70 shadow-sm dark:border-red-900/40">
        <div className="h-1.5 bg-gradient-to-r from-red-700 via-red-500 to-orange-400" />
        <CardHeader className="gap-4 pb-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-red-200 bg-red-50 px-3 py-1 text-xs font-medium text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300">
              <Database className="h-3.5 w-3.5" />
              {t("databaseConfig.platform")}
            </div>
            <CardTitle className="text-3xl font-black tracking-tight">
              <span className="bg-gradient-to-r from-red-700 via-red-600 to-orange-500 bg-clip-text text-transparent">
                {t("databaseConfig.heroTitle")}
              </span>
            </CardTitle>
            <CardDescription className="max-w-2xl text-sm leading-6">
              {t("databaseConfig.heroDescription")}
            </CardDescription>
          </div>
          <div className="grid gap-2 rounded-2xl border bg-muted/30 p-4 text-sm sm:min-w-[220px]">
            <div className="flex items-center gap-2 font-medium">
              <PlugZap className="h-4 w-4 text-primary" />
              {t("databaseConfig.capabilityTitle")}
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">{t("databaseConfig.tags.vector")}</Badge>
              <Badge variant="outline">{t("databaseConfig.tags.rag")}</Badge>
              <Badge variant="outline">{t("databaseConfig.tags.memory")}</Badge>
              <Badge variant="outline">{t("databaseConfig.tags.audit")}</Badge>
            </div>
          </div>
        </CardHeader>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <Card className="border-primary/10 shadow-sm">
          <CardHeader className="pb-4">
            <CardTitle className="text-base">{t("databaseConfig.formTitle")}</CardTitle>
            <CardDescription>
              {t("databaseConfig.formDescription")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-5 md:grid-cols-2">
              <div className="space-y-2">
                <Label>{t("databaseConfig.fields.user")}</Label>
                <Input
                  value={form.user}
                  onChange={(event) => updateField("user", event.target.value)}
                  placeholder={t("databaseConfig.placeholders.user")}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("databaseConfig.fields.password")}</Label>
                <SecretInput
                  value={form.password}
                  onChange={(value) => updateField("password", value)}
                  placeholder={t("databaseConfig.placeholders.password")}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("databaseConfig.fields.host")}</Label>
                <Input
                  value={form.host}
                  onChange={(event) => updateField("host", event.target.value)}
                  placeholder={t("databaseConfig.placeholders.host")}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("databaseConfig.fields.port")}</Label>
                <Input
                  value={form.port}
                  onChange={(event) => updateField("port", event.target.value)}
                  placeholder="1521"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>{t("databaseConfig.fields.serviceName")}</Label>
              <Input
                value={form.serviceName}
                onChange={(event) => updateField("serviceName", event.target.value)}
                placeholder={t("databaseConfig.placeholders.serviceName")}
              />
            </div>

            {loadErrorMessage && (
              <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                {loadErrorMessage}
              </div>
            )}

            <div className="flex flex-wrap gap-3 pt-2">
              <Button
                type="button"
                onClick={() => void handleTest()}
                disabled={!canSubmit || testMutation.isPending || saveMutation.isPending}
              >
                {testMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Wifi className="mr-2 h-4 w-4" />
                )}
                {t("databaseConfig.buttons.test")}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => void handleSave()}
                disabled={!canSubmit || testMutation.isPending || saveMutation.isPending}
              >
                {saveMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Save className="mr-2 h-4 w-4" />
                )}
                {t("databaseConfig.buttons.save")}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-primary/10 shadow-sm">
          <CardHeader className="pb-4">
            <CardTitle className="text-base">{t("databaseConfig.previewTitle")}</CardTitle>
            <CardDescription>
              {t("databaseConfig.previewDescription")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="rounded-xl border bg-muted/30 p-4">
              <div className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {t("databaseConfig.snapshotTitle")}
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">{t("databaseConfig.snapshot.user")}</span>
                  <span className="font-mono">{form.user || "-"}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">{t("databaseConfig.snapshot.host")}</span>
                  <span className="font-mono">{form.host || "-"}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">{t("databaseConfig.snapshot.port")}</span>
                  <span className="font-mono">{form.port || "-"}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">{t("databaseConfig.snapshot.service")}</span>
                  <span className="font-mono">{form.serviceName || "-"}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">{t("databaseConfig.snapshot.dsn")}</span>
                  <span className="font-mono text-right">{currentDsn}</span>
                </div>
              </div>
            </div>

            <div className="rounded-xl border bg-muted/20 p-4">
              <div className="mb-2 font-medium">{t("databaseConfig.runtimeTitle")}</div>
              <div className="space-y-2 text-muted-foreground">
                <div className="flex items-center justify-between gap-3">
                  <span>{t("databaseConfig.runtime.configPath")}</span>
                  <span className="max-w-[180px] truncate text-right font-mono text-xs">
                    {data?.configPath || t("databaseConfig.runtime.notAvailable")}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span>{t("databaseConfig.runtime.connectString")}</span>
                  <span className="max-w-[180px] truncate text-right font-mono text-xs">
                    {connectString}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span>{t("databaseConfig.runtime.updatedAt")}</span>
                  <span className="text-right text-xs">
                    {data?.updatedAt ? new Date(data.updatedAt).toLocaleString() : t("databaseConfig.runtime.notAvailable")}
                  </span>
                </div>
              </div>
            </div>

            <div
              className={`rounded-xl border px-4 py-3 text-sm ${
                latestStatus?.tone === "success"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/30 dark:text-emerald-300"
                  : latestStatus?.tone === "error"
                    ? "border-destructive/30 bg-destructive/5 text-destructive"
                    : "border-border bg-muted/20 text-muted-foreground"
              }`}
            >
              <div className="flex items-start gap-2">
                {latestStatus?.tone === "success" ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                ) : latestStatus?.tone === "error" ? (
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                ) : (
                  <PlugZap className="mt-0.5 h-4 w-4 shrink-0" />
                )}
                <div className="space-y-1">
                  <div className="font-medium">
                    {latestStatus?.message ?? (isLoading ? t("databaseConfig.messages.loading") : t("databaseConfig.messages.notTested"))}
                  </div>
                  <div className="text-xs opacity-90">
                    {latestStatus?.extra ?? currentDsn}
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-xl border bg-muted/20 p-4">
              <div className="mb-2 font-medium">{t("databaseConfig.metadataTitle")}</div>
              <div className="space-y-2 text-muted-foreground">
                {latestMetadata.length > 0 ? (
                  latestMetadata.map((item) => (
                    <div key={item.label} className="flex items-center justify-between gap-3">
                      <span>{item.label}</span>
                      <span className="text-right font-mono text-xs">{item.value}</span>
                    </div>
                  ))
                ) : (
                  <div className="text-xs">{t("databaseConfig.messages.metadataPending")}</div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
