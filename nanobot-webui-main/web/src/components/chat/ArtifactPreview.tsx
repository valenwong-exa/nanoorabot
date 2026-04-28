import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import {
  ChevronDown,
  ChevronRight,
  Download,
  ExternalLink,
  FileCode,
  FileImage,
  FileText,
  FileVideo,
  RefreshCw,
} from "lucide-react";

import api from "../../lib/api";
import { cn } from "../../lib/utils";

type FileCategory = "html" | "image" | "video" | "markdown" | "text" | "other";

function getFileCategory(filePath: string): FileCategory {
  const ext = filePath.split(".").pop()?.toLowerCase() ?? "";

  if (["html", "htm"].includes(ext)) return "html";
  if (["jpg", "jpeg", "png", "gif", "webp", "svg", "bmp", "ico"].includes(ext)) return "image";
  if (["mp4", "webm", "ogg", "mov", "avi", "mkv"].includes(ext)) return "video";
  if (["md", "markdown"].includes(ext)) return "markdown";
  if (
    [
      "txt",
      "log",
      "csv",
      "xml",
      "yaml",
      "yml",
      "toml",
      "ini",
      "env",
      "json",
      "jsonl",
      "json5",
      "py",
      "js",
      "ts",
      "jsx",
      "tsx",
      "css",
      "scss",
      "sh",
      "bash",
      "rs",
      "go",
      "java",
      "c",
      "cpp",
      "h",
      "sql",
    ].includes(ext)
  ) {
    return "text";
  }

  return "other";
}

function getFileName(filePath: string): string {
  return filePath.split(/[/\\]/).pop() ?? filePath;
}

function getLangHint(filePath: string): string {
  const ext = filePath.split(".").pop()?.toLowerCase() ?? "";
  const languageMap: Record<string, string> = {
    json: "json",
    jsonl: "json",
    json5: "json",
    js: "javascript",
    ts: "typescript",
    jsx: "javascript",
    tsx: "typescript",
    py: "python",
    sh: "bash",
    bash: "bash",
    css: "css",
    scss: "scss",
    xml: "xml",
    yaml: "yaml",
    yml: "yaml",
    toml: "toml",
    sql: "sql",
    rs: "rust",
    go: "go",
    java: "java",
    c: "c",
    cpp: "cpp",
  };

  return languageMap[ext] ?? "";
}

function maybeFormatJson(content: string, filePath: string): string {
  const ext = filePath.split(".").pop()?.toLowerCase() ?? "";
  if (ext === "json" || ext === "json5") {
    try {
      return JSON.stringify(JSON.parse(content), null, 2);
    } catch {
      return content;
    }
  }
  return content;
}

const CATEGORY_ICON: Record<FileCategory, React.ComponentType<{ className?: string }>> = {
  html: FileCode,
  image: FileImage,
  video: FileVideo,
  markdown: FileText,
  text: FileCode,
  other: FileText,
};

const CATEGORY_LABEL: Record<FileCategory, string> = {
  html: "HTML",
  image: "Image",
  video: "Video",
  markdown: "Markdown",
  text: "Text",
  other: "File",
};

interface ArtifactPreviewProps {
  filePath: string;
}

export function ArtifactPreview({ filePath }: ArtifactPreviewProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const blobUrlRef = useRef<string | null>(null);

  const category = getFileCategory(filePath);
  const fileName = getFileName(filePath);
  const Icon = CATEGORY_ICON[category];

  const fetchContent = async () => {
    setLoading(true);
    setError(null);
    try {
      if (category === "html" || category === "markdown" || category === "text") {
        const resp = await api.get<string>("/workspace/file", {
          params: { path: filePath },
          responseType: "text",
        });
        setTextContent(resp.data);
      } else {
        const resp = await api.get<Blob>("/workspace/file", {
          params: { path: filePath },
          responseType: "blob",
        });
        const url = URL.createObjectURL(resp.data);
        if (blobUrlRef.current) {
          URL.revokeObjectURL(blobUrlRef.current);
        }
        blobUrlRef.current = url;
        setBlobUrl(url);
      }
    } catch {
      setError(t("chat.artifact.loadError"));
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (event: React.MouseEvent) => {
    event.stopPropagation();
    try {
      const resp = await api.get<Blob>("/workspace/file", {
        params: { path: filePath },
        responseType: "blob",
      });
      const url = URL.createObjectURL(resp.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = fileName;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      return;
    }
  };

  const handleOpenExternal = (event: React.MouseEvent) => {
    event.stopPropagation();
    if (!textContent) return;

    const blob = new Blob([textContent], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank", "noopener,noreferrer");
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
  };

  useEffect(() => {
    return () => {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
      }
    };
  }, []);

  const handleToggle = () => {
    const nextExpanded = !expanded;
    setExpanded(nextExpanded);
    if (nextExpanded && !textContent && !blobUrl && !loading) {
      void fetchContent();
    }
  };

  return (
    <div className="rounded-lg border border-emerald-200/60 bg-emerald-50/30 text-xs overflow-hidden dark:border-emerald-800/40 dark:bg-emerald-950/15">
      <button
        onClick={handleToggle}
        className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left transition-colors hover:bg-emerald-100/40 dark:hover:bg-emerald-900/20"
      >
        <Icon className="h-3 w-3 shrink-0 text-emerald-600 dark:text-emerald-400" />
        <span className="flex-1 truncate font-mono font-medium text-emerald-700 dark:text-emerald-300">
          {fileName}
        </span>
        <span className="shrink-0 rounded bg-emerald-100 px-1 py-0.5 text-[10px] font-medium text-emerald-600 dark:bg-emerald-900/50 dark:text-emerald-400">
          {CATEGORY_LABEL[category]}
        </span>

        {category === "html" && textContent !== null && (
          <span
            role="button"
            onClick={handleOpenExternal}
            className="shrink-0 p-0.5 text-muted-foreground/50 transition-colors hover:text-muted-foreground"
            aria-label={t("chat.artifact.openExternal")}
          >
            <ExternalLink className="h-3 w-3" />
          </span>
        )}

        <span
          role="button"
          onClick={handleDownload}
          className="shrink-0 p-0.5 text-muted-foreground/50 transition-colors hover:text-muted-foreground"
          aria-label={t("chat.artifact.download")}
        >
          <Download className="h-3 w-3" />
        </span>

        {loading ? (
          <RefreshCw className="h-3 w-3 shrink-0 animate-spin text-emerald-500" />
        ) : expanded ? (
          <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground/50" />
        ) : (
          <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground/50" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-emerald-200/40 dark:border-emerald-800/30">
          {loading && (
            <div className="flex items-center justify-center py-6 text-muted-foreground/60">
              <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
              <span>{t("chat.artifact.loading")}</span>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-between px-3 py-2">
              <span className="text-red-500/80">{error}</span>
              <button
                onClick={() => void fetchContent()}
                className="flex items-center gap-1 text-muted-foreground/60 transition-colors hover:text-muted-foreground"
              >
                <RefreshCw className="h-3 w-3" />
                <span>{t("chat.artifact.retry")}</span>
              </button>
            </div>
          )}

          {!loading && !error && category === "html" && textContent !== null && (
            <iframe
              srcDoc={textContent}
              sandbox="allow-scripts"
              className="h-[480px] w-full bg-white"
              title={fileName}
            />
          )}

          {!loading && !error && category === "markdown" && textContent !== null && (
            <div
              className={cn(
                "prose prose-sm max-w-none px-4 py-3 dark:prose-invert",
                "[&_pre]:overflow-x-auto [&_pre]:rounded-xl [&_pre]:bg-zinc-100 [&_pre]:p-4 [&_pre]:text-xs dark:[&_pre]:bg-zinc-900",
                "[&_code:not(pre_code)]:rounded [&_code:not(pre_code)]:bg-muted [&_code:not(pre_code)]:px-1.5 [&_code:not(pre_code)]:py-0.5 [&_code:not(pre_code)]:text-xs",
              )}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                {textContent}
              </ReactMarkdown>
            </div>
          )}

          {!loading && !error && category === "image" && blobUrl !== null && (
            <div className="flex justify-center p-3">
              <img
                src={blobUrl}
                alt={fileName}
                className="max-h-[480px] max-w-full rounded object-contain"
              />
            </div>
          )}

          {!loading && !error && category === "video" && blobUrl !== null && (
            <div className="p-3">
              <video controls src={blobUrl} className="max-h-[480px] w-full rounded" />
            </div>
          )}

          {!loading && !error && category === "text" && textContent !== null && (
            <pre
              className={cn(
                "max-h-[480px] overflow-auto bg-zinc-50 px-4 py-3 font-mono text-[11px] leading-relaxed text-foreground/80 dark:bg-zinc-900",
                `language-${getLangHint(filePath)}`,
              )}
            >
              {maybeFormatJson(textContent, filePath)}
            </pre>
          )}

          {!loading && !error && category === "other" && (
            <div className="px-3 py-2 text-muted-foreground/70">
              {t("chat.artifact.unsupported")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
