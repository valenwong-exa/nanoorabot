import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "../lib/api";
import i18n from "../i18n";

export interface OracleConfig {
  user: string;
  password: string;
  host: string;
  port: number;
  serviceName: string;
  dsn: string;
  connectString: string;
  configPath: string | null;
  updatedAt: string | null;
}

export interface OracleConfigInput {
  user: string;
  password: string;
  host: string;
  port: number;
  serviceName: string;
}

export interface OracleConnectionTestResult {
  success: boolean;
  message: string;
  dsn: string;
  serverVersion: string | null;
  characterSet: string | null;
  isRac: boolean | null;
  isMultitenant: boolean | null;
}

function getErrorMessage(err: unknown, fallbackKey: string): string {
  return (
    (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
    i18n.t(fallbackKey)
  );
}

export function useOracleConfig() {
  return useQuery<OracleConfig>({
    queryKey: ["oracle-config"],
    queryFn: () => api.get("/oracle-config").then((r) => r.data),
  });
}

export function useSaveOracleConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: OracleConfigInput) =>
      api.put("/oracle-config", data).then((r) => r.data as OracleConfig),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["oracle-config"] });
      toast.success(i18n.t("databaseConfig.messages.saveSuccess"));
    },
    onError: (err: unknown) => {
      toast.error(getErrorMessage(err, "databaseConfig.messages.saveFailed"));
    },
  });
}

export function useTestOracleConnection() {
  return useMutation({
    mutationFn: (data: OracleConfigInput) =>
      api.post("/oracle-config/test", data).then((r) => r.data as OracleConnectionTestResult),
    onSuccess: (data) => {
      toast.success(data.message || i18n.t("databaseConfig.messages.testSuccess"));
    },
    onError: (err: unknown) => {
      toast.error(getErrorMessage(err, "databaseConfig.messages.testFailed"));
    },
  });
}
