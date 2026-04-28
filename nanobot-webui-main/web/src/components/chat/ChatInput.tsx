import { useRef, useState, useCallback, useLayoutEffect, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Send, Square, Wifi, WifiOff, Paperclip, X, Loader2, ImageIcon, FileText, Terminal } from "lucide-react";
import { nanoid } from "nanoid";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { Textarea } from "../ui/textarea";
import { cn } from "../../lib/utils";
import { uploadFile } from "../../hooks/useConfig";

const MODEL_IMAGE_EXTENSIONS = new Set([
  ".jpeg",
  ".jpg",
  ".png",
  ".bmp",
  ".gif",
  ".svg",
  ".svgz",
  ".webp",
  ".ico",
  ".xbm",
  ".dib",
  ".pjp",
  ".tif",
  ".pjpeg",
  ".avif",
  ".apng",
  ".tiff",
  ".jfif",
]);

const MODEL_IMAGE_ACCEPT = Array.from(MODEL_IMAGE_EXTENSIONS).join(",");

function isModelImageFile(name: string): boolean {
  const lower = name.toLowerCase();
  return Array.from(MODEL_IMAGE_EXTENSIONS).some((ext) => lower.endsWith(ext));
}

interface Attachment {
  id: string;
  name: string;
  url?: string;
  localPath?: string;
  sendAsMedia?: boolean;
  uploading: boolean;
}

interface ChatInputProps {
  onSend: (content: string, media?: string[]) => void;
  disabled?: boolean;
  onStop?: () => void;
  isWaiting?: boolean;
  isConnected?: boolean;
  showToolMessages?: boolean;
  onToggleToolMessages?: () => void;
}

export function ChatInput({
  onSend,
  disabled,
  onStop,
  isWaiting,
  isConnected = true,
  showToolMessages = false,
  onToggleToolMessages,
}: ChatInputProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isVoiceOverlayOpen, setIsVoiceOverlayOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const MAX_TEXTAREA_H = 240;
  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    // height:0 fully collapses even inside a flex container, unlike height:auto
    el.style.overflowY = "hidden";
    el.style.height = "0px";
    const contentH = el.scrollHeight;
    if (contentH > MAX_TEXTAREA_H) {
      el.style.height = MAX_TEXTAREA_H + "px";
      el.style.overflowY = "auto";
    } else {
      el.style.height = Math.max(contentH, 52) + "px";
    }
  }, [value]);

  const handleFilesSelected = useCallback(async (files: File[]) => {
    for (const file of files) {
      const id = nanoid();
      setAttachments((prev) => [...prev, { id, name: file.name, uploading: true }]);
      try {
        const uploaded = await uploadFile(file);
        const isImage = isModelImageFile(file.name);
        setAttachments((prev) =>
          prev.map((a) => (
            a.id === id
              ? {
                  ...a,
                  url: uploaded.url,
                  localPath: uploaded.local_path,
                  sendAsMedia: isImage && !!uploaded.local_path,
                  uploading: false,
                }
              : a
          ))
        );
      } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        toast.error(detail ?? t("chat.uploadFailed"));
        setAttachments((prev) => prev.filter((a) => a.id !== id));
      }
    }
  }, [t]);

  const handlePaste = useCallback(
    (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
      const fileItems = Array.from(e.clipboardData.items).filter((i) => i.kind === "file");
      if (fileItems.length === 0) return;
      e.preventDefault();
      const files = fileItems.map((i) => i.getAsFile()).filter(Boolean) as File[];
      handleFilesSelected(files);
    },
    [handleFilesSelected]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isUploading = attachments.some((a) => a.uploading);

  const handleSend = useCallback(() => {
    const text = value.trim();
    const readyAttachments = attachments.filter((a) => a.url && !a.uploading);
    if ((!text && readyAttachments.length === 0) || disabled || isUploading) return;

    const media = readyAttachments
      .filter((a) => a.sendAsMedia && a.localPath)
      .map((a) => a.localPath as string);

    let content = text;
    for (const att of readyAttachments) {
      if (att.url && !att.sendAsMedia) {
        const isImage = isModelImageFile(att.name);
        content += `\n${isImage ? `![${att.name}](${att.url})` : `[${att.name}](${att.url})`}`;
      }
    }

    onSend(content.trim(), media);
    setValue("");
    setAttachments([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = "52px";
      textareaRef.current.style.overflowY = "hidden";
    }
  }, [value, attachments, disabled, isUploading, onSend]);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    // height adjustment is handled by useLayoutEffect
  };

  const removeAttachment = (id: string) =>
    setAttachments((prev) => prev.filter((a) => a.id !== id));

  const canSend = (value.trim().length > 0 || attachments.filter((a) => a.url).length > 0) && !isUploading;

  useEffect(() => {
    if (!isVoiceOverlayOpen) return;

    const timer = window.setTimeout(() => {
      setIsVoiceOverlayOpen(false);
    }, 15000);

    return () => {
      window.clearTimeout(timer);
    };
  }, [isVoiceOverlayOpen]);

  return (
    <>
      {isVoiceOverlayOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background/72 backdrop-blur-sm">
          <button
            type="button"
            onClick={() => setIsVoiceOverlayOpen(false)}
            className="flex min-h-[240px] w-[min(88vw,360px)] flex-col items-center justify-center gap-5 rounded-3xl border border-border bg-background/95 px-8 py-10 text-center shadow-2xl transition-transform hover:scale-[1.01]"
            aria-label="关闭语音输入提示"
            title="点击关闭"
          >
            <img
              src="/microphone-speaking.svg"
              alt=""
              className="h-24 w-24 object-contain"
            />
            <div className="flex items-end justify-center text-xl font-medium text-foreground">
              <span>请说话</span>
              <span className="ml-1 inline-flex w-6 justify-start text-primary">
                <span className="animate-bounce [animation-delay:0ms]">.</span>
                <span className="animate-bounce [animation-delay:180ms]">.</span>
                <span className="animate-bounce [animation-delay:360ms]">.</span>
              </span>
            </div>
          </button>
        </div>
      )}
      <div className="px-4 pb-4 pt-2">
        <div className="w-full">
        <div className={cn(
          "relative flex flex-col rounded-2xl border bg-background/90 backdrop-blur-xl shadow-lg transition-all",
          isWaiting ? "border-primary/40" : "focus-within:border-primary/60 focus-within:shadow-xl"
        )}>
          {/* Attachment chips */}
          {attachments.length > 0 && (
            <div className="flex flex-wrap gap-1.5 px-4 pt-3">
              {attachments.map((att) => {
                const isImage = isModelImageFile(att.name);
                return (
                  <div
                    key={att.id}
                    className="flex items-center gap-1.5 rounded-lg border bg-muted/60 px-2.5 py-1 text-xs"
                  >
                    {att.uploading ? (
                      <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                    ) : isImage ? (
                      <ImageIcon className="h-3 w-3 text-primary" />
                    ) : (
                      <FileText className="h-3 w-3 text-primary" />
                    )}
                    <span className="max-w-[140px] truncate text-muted-foreground">
                      {att.uploading ? t("chat.uploading") : att.name}
                    </span>
                    {!att.uploading && (
                      <button
                        onClick={() => removeAttachment(att.id)}
                        className="ml-0.5 rounded-sm text-muted-foreground hover:text-foreground"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          <div className="relative">
            <button
              type="button"
              onClick={() => setIsVoiceOverlayOpen(true)}
              className="absolute left-3 top-1/2 z-10 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full text-muted-foreground/70 transition-colors hover:bg-muted/70 hover:text-foreground"
              aria-label="语音输入"
              title="语音输入"
            >
              <img src="/microphone-.svg" alt="" className="h-4 w-4 opacity-80" />
            </button>
            <Textarea
              ref={textareaRef}
              value={value}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              placeholder={t("chat.placeholder")}
              rows={1}
              className="resize-none border-0 bg-transparent pl-14 pr-4 py-3.5 shadow-none focus-visible:ring-0 text-base leading-relaxed w-full"
              disabled={!isWaiting && disabled}
            />
          </div>
          <div className="flex items-center justify-between px-3 pb-2">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              {isConnected ? (
                <Wifi className="h-3 w-3 text-green-500" />
              ) : (
                <WifiOff className="h-3 w-3 text-destructive" />
              )}
              <span>{isConnected ? t("chat.connected") : t("chat.disconnected")}</span>

              {/* File upload button */}
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 ml-1"
                onClick={() => fileInputRef.current?.click()}
                disabled={isWaiting}
                title={t("chat.uploadAttachment")}
              >
                <Paperclip className="h-3.5 w-3.5" />
              </Button>
              {/* Toggle tool messages */}
              <Button
                variant="ghost"
                size="icon"
                className={`h-6 w-6 transition-colors ${
                  showToolMessages
                    ? "text-primary"
                    : "text-muted-foreground/40 hover:text-muted-foreground"
                }`}
                onClick={onToggleToolMessages}
                title={showToolMessages ? t("chat.hideToolMessages") : t("chat.showToolMessages")}
              >
                <Terminal className="h-3.5 w-3.5" />
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                hidden
                accept={MODEL_IMAGE_ACCEPT}
                onChange={(e) => {
                  if (e.target.files) handleFilesSelected(Array.from(e.target.files));
                  e.target.value = "";
                }}
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">
                {isWaiting ? "" : t("chat.hint")}
              </span>
              {isWaiting ? (
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={onStop}
                  className="h-8 gap-1.5 rounded-xl px-3"
                >
                  <Square className="h-3.5 w-3.5" />
                  {t("chat.stop")}
                </Button>
              ) : (
                <Button
                  size="sm"
                  onClick={handleSend}
                  disabled={!canSend || disabled}
                  className="h-8 gap-1.5 rounded-xl px-3"
                >
                  <Send className="h-3.5 w-3.5" />
                  {t("chat.send")}
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
      </div>
    </>
  );
}
