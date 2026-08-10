import { useMutation, useQuery } from "@tanstack/react-query";
import api from "../lib/api";

export interface HostDatabase {
  database_name: string;
  sqlcl_saveconnname?: string;
  database_version: string;
  database_status?: string;
  oracle_home?: string;
  pdb?: string;
}

export interface MonitoredDatabaseInventoryItem {
  description?: string;
  database_name: string;
  sqlcl_saveconnname?: string;
  database_version?: string;
  database_status?: string;
  probe_output?: string;
  last_checked_at?: string;
}

export interface HostInventoryItem {
  host_name: string;
  description?: string;
  aliases: string[];
  ip: string;
  ssh_key: string;
  default_user: string;
  privilege_escalation: string;
  os_type: string;
  host_status?: string;
  databases: HostDatabase[];
}

export interface HostInventoryResponse {
  workspace: string;
  inventory_path: string;
  exists: boolean;
  database_inventory: MonitoredDatabaseInventoryItem[];
  hosts: HostInventoryItem[];
}

export interface HostInventoryRefreshConfig {
  enabled: boolean;
  intervalMinutes: number;
  isRunning: boolean;
  lastRunAt: string | null;
  lastSuccessAt: string | null;
  lastError: string | null;
}

export interface HostInventoryRefreshConfigInput {
  enabled?: boolean;
  intervalMinutes?: number;
}

export interface HostInventoryUpdateInput {
  database_inventory: MonitoredDatabaseInventoryItem[];
  host_inventory: HostInventoryItem[];
}

export interface OpenMonitoredDatabaseInput {
  sqlcl_saveconnname: string;
  database_name?: string;
}

export interface OpenMonitoredDatabaseResult {
  success: boolean;
  status: string;
  connectionName: string;
  databaseName?: string | null;
  probeOutput?: string | null;
  message: string;
}

export function useHostInventory(options?: { refetchInterval?: number | false }) {
  return useQuery<HostInventoryResponse>({
    queryKey: ["host-inventory"],
    queryFn: () => api.get("/hosts/inventory").then((r) => r.data),
    staleTime: 0,
    refetchOnMount: "always",
    refetchInterval: options?.refetchInterval,
  });
}

export function useRefreshHostInventory() {
  return useMutation<HostInventoryResponse>({
    mutationFn: () => api.post("/hosts/inventory/refresh").then((r) => r.data),
  });
}

export function useUpdateHostInventory() {
  return useMutation<HostInventoryResponse, unknown, HostInventoryUpdateInput>({
    mutationFn: (data) => api.put("/hosts/inventory", data).then((r) => r.data),
  });
}

export function useOpenMonitoredDatabase() {
  return useMutation<OpenMonitoredDatabaseResult, unknown, OpenMonitoredDatabaseInput>({
    mutationFn: (data) => api.post("/hosts/database/open", data).then((r) => r.data as OpenMonitoredDatabaseResult),
  });
}

export function useHostInventoryRefreshConfig() {
  return useQuery<HostInventoryRefreshConfig>({
    queryKey: ["host-inventory", "refresh-config"],
    queryFn: () => api.get("/hosts/inventory/refresh-config").then((r) => r.data),
    refetchInterval: (query) => (query.state.data?.isRunning ? 2000 : 30000),
  });
}

export function useUpdateHostInventoryRefreshConfig() {
  return useMutation({
    mutationFn: async (data: HostInventoryRefreshConfigInput) => {
      const response = await api.put("/hosts/inventory/refresh-config", data);
      return response.data as HostInventoryRefreshConfig;
    },
  });
}
