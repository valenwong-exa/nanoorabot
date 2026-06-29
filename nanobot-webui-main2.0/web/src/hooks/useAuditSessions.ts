import { useQuery } from "@tanstack/react-query";
import api from "../lib/api";

export interface AuditRecord {
  line_number: number;
  role: string;
  timestamp: string;
  summary: string;
  search_text: string;
}

export interface AuditSessionFile {
  file_name: string;
  session_type: string;
  session_key: string;
  created_at: string;
  updated_at: string;
  line_count: number;
  records: AuditRecord[];
}

export interface AuditSessionsResponse {
  workspace: string;
  sessions_dir: string;
  exists: boolean;
  files: AuditSessionFile[];
}

export function useAuditSessions() {
  return useQuery<AuditSessionsResponse>({
    queryKey: ["audit-sessions"],
    queryFn: () => api.get("/audit/sessions").then((r) => r.data),
    staleTime: 0,
    refetchOnMount: "always",
  });
}
