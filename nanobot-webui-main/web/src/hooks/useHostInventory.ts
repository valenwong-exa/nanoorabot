import { useMutation, useQuery } from "@tanstack/react-query";
import api from "../lib/api";

export interface HostDatabase {
  database_name: string;
  database_version: string;
  database_status?: string;
}

export interface HostInventoryItem {
  host_name: string;
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
  hosts: HostInventoryItem[];
}

export function useHostInventory() {
  return useQuery<HostInventoryResponse>({
    queryKey: ["host-inventory"],
    queryFn: () => api.get("/hosts/inventory").then((r) => r.data),
    staleTime: 0,
    refetchOnMount: "always",
  });
}

export function useRefreshHostInventory() {
  return useMutation<HostInventoryResponse>({
    mutationFn: () => api.post("/hosts/inventory/refresh").then((r) => r.data),
  });
}
