import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "../lib/api";

export interface DefenseRule {
  command: string;
  matchType: "literal" | "regex";
  regexFlags: string;
  category: string;
  severity: string;
  mode: string;
  scope: string;
  note: string;
}

export interface ToolPolicy {
  version: number;
  name: string;
  source: string;
  description: string;
  rules: DefenseRule[];
  configPath: string | null;
  updatedAt: string | null;
}

export interface ToolPolicyInput {
  version: number;
  name: string;
  source: string;
  description: string;
  rules: DefenseRule[];
}

function getErrorMessage(err: unknown, fallback: string): string {
  return (
    (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
    fallback
  );
}

export function useToolPolicy() {
  return useQuery<ToolPolicy>({
    queryKey: ["tool-policy"],
    queryFn: () => api.get("/tool-policy").then((r) => r.data),
  });
}

export function useSaveToolPolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ToolPolicyInput) =>
      api.put("/tool-policy", data).then((r) => r.data as ToolPolicy),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tool-policy"] });
      toast.success("危险命令策略已保存");
    },
    onError: (err: unknown) => {
      toast.error(getErrorMessage(err, "保存危险命令策略失败"));
    },
  });
}
