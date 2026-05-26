import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "../lib/api";
import i18n from "../i18n";

export interface KnowledgeBaseHealth {
  status: string;
  baseUrl: string;
}

export type KnowledgeBaseEngine = "qwen" | "bge";

export interface KnowledgeBaseUploadInput {
  file: File;
  engine: KnowledgeBaseEngine;
  chunkSizeTokens?: number;
  chunkOverlapTokens?: number;
  sourceFile?: string;
  documentType?: "pdf" | "txt";
  device?: "auto" | "cuda" | "cpu";
}

export interface KnowledgeBaseUploadResult {
  documentName: string;
  documentType: string;
  docId: number | null;
  inserted: boolean;
  parsedChunkCount: number;
  insertedChunkCount: number;
  fullTextLength: number;
  fullTextPreview: string | null;
}

export interface KnowledgeBaseSearchInput {
  prompt: string;
  engine: KnowledgeBaseEngine;
  topK: number;
  rerankerScore: number;
  documentType?: "pdf" | "txt";
  device?: "auto" | "cuda" | "cpu";
}

export interface KnowledgeBaseSearchResult {
  title: string;
  score: number;
}

export interface KnowledgeBaseDocumentListItem {
  docId: number;
  documentName: string;
  documentType: string;
  sourceFile: string | null;
  createdAt: string | null;
  chunkCount: number;
}

export interface KnowledgeBaseDocumentListResult {
  items: KnowledgeBaseDocumentListItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface KnowledgeBaseDocumentListParams {
  engine: KnowledgeBaseEngine;
  page: number;
  pageSize: number;
  keyword?: string;
  documentType?: "pdf" | "txt";
}

export interface KnowledgeBaseDeleteResult {
  success: boolean;
  docId: number;
  deletedDocumentCount: number;
  deletedChunkCount: number;
}

function getErrorMessage(err: unknown, fallbackKey: string): string {
  return (
    (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
    i18n.t(fallbackKey)
  );
}

export function useKnowledgeBaseHealth(engine: KnowledgeBaseEngine) {
  return useQuery<KnowledgeBaseHealth>({
    queryKey: ["knowledge-base", "health", engine],
    queryFn: () => api.get("/knowledge-base/health", { params: { engine } }).then((r) => r.data),
    retry: false,
    refetchInterval: 30000,
  });
}

export function useUploadKnowledgeDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: KnowledgeBaseUploadInput) => {
      const formData = new FormData();
      formData.append("file", data.file);
      formData.append("engine", data.engine);
      formData.append("chunk_size_tokens", String(data.chunkSizeTokens ?? 500));
      formData.append("chunk_overlap_tokens", String(data.chunkOverlapTokens ?? 50));
      formData.append("source_file", data.sourceFile ?? "webui");
      formData.append("device", data.device ?? "auto");
      if (data.documentType) {
        formData.append("document_type", data.documentType);
      }
      const response = await api.post("/knowledge-base/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 600000,
      });
      return response.data as KnowledgeBaseUploadResult;
    },
    onError: (err: unknown) => {
      toast.error(getErrorMessage(err, "knowledgeBase.messages.uploadFailed"));
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["knowledge-base", "documents"] });
    },
  });
}

export function useSearchKnowledgeBase() {
  return useMutation({
    mutationFn: async (data: KnowledgeBaseSearchInput) => {
      const response = await api.post("/knowledge-base/search", {
        prompt: data.prompt,
        engine: data.engine,
        topK: data.topK,
        rerankerScore: data.rerankerScore,
        documentType: data.documentType,
        device: data.device ?? "auto",
      }, {
        timeout: 600000,
      });
      return response.data as KnowledgeBaseSearchResult[];
    },
    onError: (err: unknown) => {
      toast.error(getErrorMessage(err, "knowledgeBase.messages.searchFailed"));
    },
  });
}

export function useKnowledgeBaseDocuments(params: KnowledgeBaseDocumentListParams) {
  return useQuery<KnowledgeBaseDocumentListResult>({
    queryKey: ["knowledge-base", "documents", params],
    queryFn: async () => {
      const response = await api.get("/knowledge-base/documents", {
        params: {
          page: params.page,
          pageSize: params.pageSize,
          engine: params.engine,
          keyword: params.keyword || undefined,
          documentType: params.documentType || undefined,
        },
      });
      return response.data as KnowledgeBaseDocumentListResult;
    },
    placeholderData: (previousData) => previousData,
  });
}

export function useDeleteKnowledgeDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ docId, engine }: { docId: number; engine: KnowledgeBaseEngine }) => {
      const response = await api.delete(`/knowledge-base/documents/${docId}`, {
        params: { engine },
      });
      return response.data as KnowledgeBaseDeleteResult;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["knowledge-base", "documents"] });
      toast.success(i18n.t("knowledgeBase.messages.deleteSuccess"));
    },
    onError: (err: unknown) => {
      toast.error(getErrorMessage(err, "knowledgeBase.messages.deleteFailed"));
    },
  });
}
