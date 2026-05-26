import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "../lib/api";
import i18n from "../i18n";

export interface SkillInfo {
  name: string;
  source: "builtin" | "workspace";
  path: string;
  description: string;
  available: boolean;
  enabled: boolean;
  unavailable_reason: string | null;
}

export interface SkillContent {
  name: string;
  content: string;
}

export function useSkills() {
  return useQuery<SkillInfo[]>({
    queryKey: ["skills"],
    queryFn: () => api.get("/skills").then((r) => r.data),
  });
}

export function useSkillContent(name: string) {
  return useQuery<SkillContent>({
    queryKey: ["skills", name],
    queryFn: () => api.get(`/skills/${name}`).then((r) => r.data),
    enabled: !!name,
  });
}

export function useCreateSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; content: string }) =>
      api.post("/skills", data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["skills"] });
      toast.success(i18n.t("skills.created"));
    },
  });
}

export function useUpdateSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, content }: { name: string; content: string }) =>
      api.put(`/skills/${name}`, { content }).then((r) => r.data),
    onSuccess: (_, { name }) => {
      qc.invalidateQueries({ queryKey: ["skills"] });
      qc.invalidateQueries({ queryKey: ["skills", name] });
      toast.success(i18n.t("skills.saved"));
    },
  });
}

export function useDeleteSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api.delete(`/skills/${name}`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["skills"] });
      toast.success(i18n.t("skills.deleted"));
    },
  });
}

export function useToggleSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, enabled }: { name: string; enabled: boolean }) =>
      api.post(`/skills/${name}/toggle`, { enabled }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["skills"] });
    },
    onError: () => {
      toast.error(i18n.t("common.saveFailed"));
    },
  });
}
