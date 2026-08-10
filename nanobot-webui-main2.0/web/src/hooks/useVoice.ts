import { useMutation, useQuery } from "@tanstack/react-query";
import api from "../lib/api";

export interface VoiceTranscriptionInput {
  file: File;
  language?: string;
  device?: string;
}

export interface VoiceTranscriptionResult {
  success: boolean;
  text: string;
  language: string;
  device: string;
  inferenceMs: number;
  audioDurationMs: number | null;
  filename: string | null;
}

export interface VoiceHealthResult {
  ok: boolean;
  reason: string | null;
  sensevoiceDir: string;
  modelPy: string;
  pythonExecutable: string;
  modelLoaded: boolean;
  device: string | null;
  missingDependencies: string[];
  missingPaths: string[];
}

export function useVoiceHealth() {
  return useQuery({
    queryKey: ["voice", "health"],
    queryFn: async () => {
      const response = await api.get("/voice/health");
      return response.data as VoiceHealthResult;
    },
    retry: false,
    staleTime: 60_000,
  });
}

export function useVoiceTranscription() {
  return useMutation({
    mutationFn: async (data: VoiceTranscriptionInput) => {
      const formData = new FormData();
      formData.append("file", data.file);
      formData.append("language", data.language ?? "zh");
      formData.append("device", data.device ?? "cuda:0");
      const response = await api.post("/voice/transcriptions", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 600000,
      });
      return response.data as VoiceTranscriptionResult;
    },
  });
}
