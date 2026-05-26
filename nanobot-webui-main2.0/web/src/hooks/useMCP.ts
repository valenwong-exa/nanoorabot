import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "../lib/api";
import i18n from "../i18n";

export interface MCPServer {
  name: string;
  type?: string;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  url?: string;
  headers?: Record<string, string>;
  timeout?: number;
  enabled?: boolean;
}

export function useMCPServers() {
  return useQuery<MCPServer[]>({
    queryKey: ["mcp", "servers"],
    queryFn: () => api.get("/mcp/servers").then((r) => r.data),
  });
}

export function useCreateMCPServer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MCPServer) =>
      api.post(`/mcp/servers/${encodeURIComponent(data.name)}`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mcp", "servers"] });
      toast.success(i18n.t("mcp.created"));
    },
  });
}

export function useUpdateMCPServer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, data }: { name: string; data: Partial<MCPServer> }) =>
      api.put(`/mcp/servers/${name}`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mcp", "servers"] });
      toast.success(i18n.t("mcp.saved"));
    },
  });
}

export function useDeleteMCPServer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api.delete(`/mcp/servers/${name}`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mcp", "servers"] });
      toast.success(i18n.t("mcp.deleted"));
    },
  });
}

export interface MCPToolInfo {
  name: string;
  description: string;
  parameters?: Record<string, unknown>;
}

export interface MCPServerRuntime {
  name: string;
  running: boolean;
  enabled: boolean;
  tools: MCPToolInfo[];
  tool_count: number;
}

export function useMCPRuntime() {
  return useQuery<MCPServerRuntime[]>({
    queryKey: ["mcp", "runtime"],
    queryFn: () => api.get("/mcp/servers/runtime").then((r) => r.data),
    refetchInterval: 15000,
  });
}

export function useToggleMCPServer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, enabled }: { name: string; enabled: boolean }) =>
      api.patch(`/mcp/servers/${encodeURIComponent(name)}/enabled`, { enabled }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mcp", "servers"] });
      qc.invalidateQueries({ queryKey: ["mcp", "runtime"] });
    },
    onError: () => {
      toast.error(i18n.t("common.saveFailed"));
    },
  });
}
