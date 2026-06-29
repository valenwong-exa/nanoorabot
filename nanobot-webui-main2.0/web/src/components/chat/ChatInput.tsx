import { useRef, useState, useCallback, useLayoutEffect, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Send, Square, Wifi, WifiOff, Paperclip, X, Loader2, ImageIcon, FileText, Terminal } from "lucide-react";
import { nanoid } from "nanoid";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { Textarea } from "../ui/textarea";
import { cn } from "../../lib/utils";
import { uploadFile } from "../../hooks/useConfig";
import { useSkills } from "../../hooks/useSkills";
import { useMCPServers } from "../../hooks/useMCP";
import { useChatStore, type DraftSnippet } from "../../stores/chatStore";
import { SkillPickerPanel, type ToolPickerItem } from "./SkillPickerPanel";

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
const MAX_SNIPPET_VISIBLE_ROWS = 6;

function isModelImageFile(name: string): boolean {
  const lower = name.toLowerCase();
  return Array.from(MODEL_IMAGE_EXTENSIONS).some((ext) => lower.endsWith(ext));
}

interface Attachment {
  id: string;
  name: string;
  url?: string;
  localPath?: string;
  previewUrl?: string;
  sendAsMedia?: boolean;
  uploading: boolean;
}

function revokePreviewUrl(url?: string) {
  if (url?.startsWith("blob:")) {
    URL.revokeObjectURL(url);
  }
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

interface SnippetContextMenuState {
  snippetId: string;
  x: number;
  y: number;
}

function composeDraftContent(snippets: DraftSnippet[], text: string): string {
  const snippetTexts = snippets.map((snippet) => snippet.text.trim()).filter(Boolean);
  const normalizedText = text.trim();
  if (snippetTexts.length === 0) {
    return normalizedText;
  }
  if (!normalizedText) {
    return snippetTexts.join("\n\n");
  }
  return [...snippetTexts, normalizedText].join("\n\n");
}

function parseToolPromptSnippet(text: string): { kind: "Skill" | "MCP"; name: string } | null {
  const match = text.match(/^Try read and use (Skill|MCP)\s+(.+?)(?:\s*,\s*)?$/);
  if (!match) {
    return null;
  }
  return {
    kind: match[1] as "Skill" | "MCP",
    name: match[2].trim(),
  };
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
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isVoiceOverlayOpen, setIsVoiceOverlayOpen] = useState(false);
  const [snippetContextMenu, setSnippetContextMenu] = useState<SnippetContextMenuState | null>(null);
  const [skillPanelDismissed, setSkillPanelDismissed] = useState(false);
  const [showEnabledOnly, setShowEnabledOnly] = useState(true);
  const [showAvailableOnly, setShowAvailableOnly] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const attachmentsRef = useRef<Attachment[]>([]);
  const previousSnippetCountRef = useRef(0);
  const skillPanelRef = useRef<HTMLDivElement>(null);
  const lastHandledAutoSendTokenRef = useRef(0);
  const currentSessionKey = useChatStore((s) => s.currentSessionKey);
  const draftSelection = useChatStore((s) =>
    s.currentSessionKey ? s.draftSelections[s.currentSessionKey] : undefined,
  );
  const value = useChatStore((s) =>
    s.currentSessionKey ? (s.draftMessages[s.currentSessionKey] ?? "") : "",
  );
  const snippets = useChatStore((s) =>
    s.currentSessionKey ? (s.draftSnippets[s.currentSessionKey] ?? []) : [],
  );
  const draftAutoSendToken = useChatStore((s) =>
    s.currentSessionKey ? (s.draftAutoSendTokens[s.currentSessionKey] ?? 0) : 0,
  );
  const setDraftMessage = useChatStore((s) => s.setDraftMessage);
  const setDraftSelection = useChatStore((s) => s.setDraftSelection);
  const addDraftSnippet = useChatStore((s) => s.addDraftSnippet);
  const clearDraftAutoSend = useChatStore((s) => s.clearDraftAutoSend);
  const updateDraftSnippet = useChatStore((s) => s.updateDraftSnippet);
  const removeDraftSnippet = useChatStore((s) => s.removeDraftSnippet);
  const clearDraftSnippets = useChatStore((s) => s.clearDraftSnippets);
  const { data: skills = [], isLoading: skillsLoading } = useSkills();
  const { data: mcpServers = [], isLoading: mcpLoading } = useMCPServers();
  const toolItems = useMemo<ToolPickerItem[]>(
    () => [
      ...skills
        .filter((skill) => skill.source === "workspace")
        .map((skill) => ({
          id: `skill:${skill.name}`,
          name: skill.name,
          kind: "skill" as const,
          description: skill.description,
          enabled: skill.enabled,
          available: skill.available,
        })),
      ...mcpServers.map((server) => ({
        id: `mcp:${server.name}`,
        name: server.name,
        kind: "mcp" as const,
        description: "This is an MCP server.",
        enabled: server.enabled !== false,
        available: true,
      })),
    ],
    [mcpServers, skills]
  );

  const skillTrigger = useMemo(() => {
    const cursor = draftSelection?.start ?? value.length;
    const beforeCursor = value.slice(0, cursor);
    const match = beforeCursor.match(/(?:^|\s)\/tool(?:\s+([^\n]*))?$/);
    if (!match) {
      return null;
    }

    const slashIndex = beforeCursor.lastIndexOf("/tool");
    if (slashIndex < 0) {
      return null;
    }

    return {
      start: slashIndex,
      end: cursor,
      query: (match[1] ?? "").trim(),
    };
  }, [draftSelection?.start, value]);

  const isSkillPanelOpen = !!skillTrigger && !skillPanelDismissed;

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
      const previewUrl = isModelImageFile(file.name) ? URL.createObjectURL(file) : undefined;
      setAttachments((prev) => [...prev, { id, name: file.name, previewUrl, uploading: true }]);
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
        setAttachments((prev) => {
          const target = prev.find((a) => a.id === id);
          revokePreviewUrl(target?.previewUrl);
          return prev.filter((a) => a.id !== id);
        });
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
    const composedDraft = composeDraftContent(snippets, value);
    const readyAttachments = attachments.filter((a) => a.url && !a.uploading);
    if ((!composedDraft && readyAttachments.length === 0) || disabled || isUploading) return;

    const media = readyAttachments
      .filter((a) => a.sendAsMedia && a.localPath)
      .map((a) => a.localPath as string);

    let content = composedDraft;
    for (const att of readyAttachments) {
      if (att.url && !att.sendAsMedia) {
        const isImage = isModelImageFile(att.name);
        content += `${content ? "\n" : ""}${isImage ? `![${att.name}](${att.url})` : `[${att.name}](${att.url})`}`;
      }
    }

    onSend(content.trim(), media);
    setDraftMessage("", currentSessionKey ?? undefined);
    setDraftSelection(0, 0, currentSessionKey ?? undefined);
    clearDraftSnippets(currentSessionKey ?? undefined);
    setSnippetContextMenu(null);
    setSkillPanelDismissed(false);
    attachments.forEach((att) => revokePreviewUrl(att.previewUrl));
    setAttachments([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = "52px";
      textareaRef.current.style.overflowY = "hidden";
    }
  }, [
    value,
    snippets,
    attachments,
    disabled,
    isUploading,
    onSend,
    setDraftMessage,
    currentSessionKey,
    setDraftSelection,
    clearDraftSnippets,
  ]);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setSkillPanelDismissed(false);
    setDraftMessage(e.target.value, currentSessionKey ?? undefined);
    setDraftSelection(e.target.selectionStart ?? e.target.value.length, e.target.selectionEnd ?? e.target.value.length, currentSessionKey ?? undefined);
    // height adjustment is handled by useLayoutEffect
  };

  const syncSelection = () => {
    const el = textareaRef.current;
    if (!el) return;
    setDraftSelection(el.selectionStart ?? value.length, el.selectionEnd ?? value.length, currentSessionKey ?? undefined);
  };

  const removeAttachment = (id: string) =>
    setAttachments((prev) => {
      const target = prev.find((a) => a.id === id);
      revokePreviewUrl(target?.previewUrl);
      return prev.filter((a) => a.id !== id);
    });

  const canSend = (composeDraftContent(snippets, value).length > 0 || attachments.filter((a) => a.url).length > 0) && !isUploading;

  const handleSkillSelect = useCallback(
    (item: ToolPickerItem) => {
      if (!skillTrigger) {
        return;
      }

      const nextValue = value.slice(0, skillTrigger.start) + value.slice(skillTrigger.end);
      const nextCursor = skillTrigger.start;
      addDraftSnippet(
        `Try read and use ${item.kind === "mcp" ? "MCP" : "Skill"} ${item.name} ,`,
        currentSessionKey ?? undefined,
      );

      setDraftMessage(nextValue, currentSessionKey ?? undefined);
      setDraftSelection(nextCursor, nextCursor, currentSessionKey ?? undefined);
      setSkillPanelDismissed(true);

      window.requestAnimationFrame(() => {
        const el = textareaRef.current;
        if (!el) {
          return;
        }
        el.focus();
        el.setSelectionRange(nextCursor, nextCursor);
      });
    },
    [addDraftSnippet, currentSessionKey, setDraftMessage, setDraftSelection, skillTrigger, value]
  );

  useEffect(() => {
    if (!isVoiceOverlayOpen) return;

    const timer = window.setTimeout(() => {
      setIsVoiceOverlayOpen(false);
    }, 15000);

    return () => {
      window.clearTimeout(timer);
    };
  }, [isVoiceOverlayOpen]);

  useEffect(() => {
    lastHandledAutoSendTokenRef.current = 0;
  }, [currentSessionKey]);

  useEffect(() => {
    if (!currentSessionKey) {
      lastHandledAutoSendTokenRef.current = 0;
      return;
    }
    if (draftAutoSendToken <= 0 || draftAutoSendToken === lastHandledAutoSendTokenRef.current) {
      return;
    }
    if (disabled || isUploading) {
      return;
    }
    const composedDraft = composeDraftContent(snippets, value);
    const readyAttachments = attachments.filter((a) => a.url && !a.uploading);
    if (!composedDraft && readyAttachments.length === 0) {
      return;
    }
    lastHandledAutoSendTokenRef.current = draftAutoSendToken;
    handleSend();
    clearDraftAutoSend(currentSessionKey);
  }, [
    attachments,
    clearDraftAutoSend,
    currentSessionKey,
    disabled,
    draftAutoSendToken,
    handleSend,
    isUploading,
    snippets,
    value,
  ]);

  useEffect(() => {
    attachmentsRef.current = attachments;
  }, [attachments]);

  useEffect(() => {
    const closeMenu = () => setSnippetContextMenu(null);
    window.addEventListener("click", closeMenu);
    window.addEventListener("scroll", closeMenu, true);
    window.addEventListener("resize", closeMenu);
    return () => {
      window.removeEventListener("click", closeMenu);
      window.removeEventListener("scroll", closeMenu, true);
      window.removeEventListener("resize", closeMenu);
    };
  }, []);

  useEffect(() => {
    if (!isSkillPanelOpen) {
      return;
    }

    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null;
      if (
        skillPanelRef.current?.contains(target ?? null) ||
        textareaRef.current?.contains(target ?? null)
      ) {
        return;
      }
      setSkillPanelDismissed(true);
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSkillPanelDismissed(true);
      }
    };

    window.addEventListener("pointerdown", handlePointerDown);
    window.addEventListener("keydown", handleEscape);
    return () => {
      window.removeEventListener("pointerdown", handlePointerDown);
      window.removeEventListener("keydown", handleEscape);
    };
  }, [isSkillPanelOpen]);

  useEffect(() => {
    const previousCount = previousSnippetCountRef.current;
    if (snippets.length > previousCount) {
      window.requestAnimationFrame(() => {
        textareaRef.current?.focus();
      });
    }
    previousSnippetCountRef.current = snippets.length;
  }, [snippets.length]);

  useEffect(() => {
    return () => {
      attachmentsRef.current.forEach((att) => revokePreviewUrl(att.previewUrl));
    };
  }, []);

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
            <div className="flex flex-wrap gap-2 px-4 pt-3">
              {attachments.map((att) => {
                const isImage = isModelImageFile(att.name);
                const previewSrc = att.previewUrl ?? att.url;
                return (
                  isImage ? (
                    <div
                      key={att.id}
                      className="group relative h-24 w-24 overflow-hidden rounded-xl border bg-muted/40 shadow-sm"
                    >
                      {previewSrc ? (
                        <img src={previewSrc} alt={att.name} className="h-full w-full object-cover" />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center bg-muted/60">
                          <ImageIcon className="h-6 w-6 text-muted-foreground" />
                        </div>
                      )}
                      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 via-black/35 to-transparent px-2 pb-1.5 pt-4">
                        <span className="block truncate text-[11px] text-white">
                          {att.uploading ? t("chat.uploading") : att.name}
                        </span>
                      </div>
                      {att.uploading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-black/25 backdrop-blur-[1px]">
                          <Loader2 className="h-5 w-5 animate-spin text-white" />
                        </div>
                      )}
                      {!att.uploading && (
                        <button
                          onClick={() => removeAttachment(att.id)}
                          className="absolute right-1.5 top-1.5 rounded-full bg-black/55 p-1 text-white opacity-90 transition hover:bg-black/70"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  ) : (
                    <div
                      key={att.id}
                      className="flex items-center gap-1.5 rounded-lg border bg-muted/60 px-2.5 py-1 text-xs"
                    >
                      {att.uploading ? (
                        <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
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
                  )
                );
              })}
            </div>
          )}

          {snippets.length > 0 && (
            <div className="flex flex-col gap-2 px-4 pt-3">
              {snippets.map((snippet) => (
                <div
                  key={snippet.id}
                  className="rounded-xl border border-emerald-400/80 bg-emerald-50/80 shadow-sm transition dark:border-emerald-700 dark:bg-emerald-950/20"
                >
                  {parseToolPromptSnippet(snippet.text) ? (
                    <div className="flex flex-wrap items-center gap-2 border-b border-emerald-300/70 px-3 py-2 dark:border-emerald-800/70">
                      <span className="rounded-full border border-emerald-500/70 bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-emerald-800 dark:border-emerald-600 dark:bg-emerald-900/40 dark:text-emerald-200">
                        {parseToolPromptSnippet(snippet.text)?.kind}
                      </span>
                      <span className="rounded-md bg-emerald-600 px-2.5 py-1 text-xs font-semibold text-white shadow-sm dark:bg-emerald-500">
                        {parseToolPromptSnippet(snippet.text)?.name}
                      </span>
                    </div>
                  ) : null}
                  <textarea
                    value={snippet.text}
                    rows={Math.min(MAX_SNIPPET_VISIBLE_ROWS, Math.max(1, snippet.text.split(/\r?\n/).length))}
                    onChange={(event) => {
                      updateDraftSnippet(snippet.id, event.target.value, currentSessionKey ?? undefined);
                      if (snippetContextMenu?.snippetId === snippet.id && event.target.value.length === 0) {
                        setSnippetContextMenu(null);
                      }
                    }}
                    onContextMenu={(event) => {
                      event.preventDefault();
                      setSnippetContextMenu({
                        snippetId: snippet.id,
                        x: event.clientX,
                        y: event.clientY,
                      });
                    }}
                    placeholder="Copied node path prompt"
                    className="min-h-[44px] max-h-40 w-full resize-none overflow-y-auto rounded-xl border-0 bg-transparent px-3 py-2 text-sm leading-relaxed text-emerald-950 outline-none transition focus:ring-2 focus:ring-emerald-200 dark:text-emerald-100 dark:focus:ring-emerald-900"
                  />
                </div>
              ))}
            </div>
          )}

          <div className="relative">
            {isSkillPanelOpen && skillTrigger ? (
              <div ref={skillPanelRef}>
                <SkillPickerPanel
                  items={toolItems}
                  query={skillTrigger.query}
                  isLoading={skillsLoading || mcpLoading}
                  enabledOnly={showEnabledOnly}
                  availableOnly={showAvailableOnly}
                  onEnabledOnlyChange={setShowEnabledOnly}
                  onAvailableOnlyChange={setShowAvailableOnly}
                  onSelectItem={handleSkillSelect}
                />
              </div>
            ) : null}
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
              onSelect={syncSelection}
              onClick={syncSelection}
              onKeyUp={syncSelection}
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
      {snippetContextMenu ? (
        <div
          className="fixed z-[120] min-w-[140px] rounded-md border bg-popover p-1 shadow-md"
          style={{ left: snippetContextMenu.x, top: snippetContextMenu.y }}
          onClick={(event) => event.stopPropagation()}
        >
          <button
            type="button"
            onClick={() => {
              removeDraftSnippet(snippetContextMenu.snippetId, currentSessionKey ?? undefined);
              setSnippetContextMenu(null);
            }}
            className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent"
          >
            <span>Delete Block</span>
          </button>
        </div>
      ) : null}
    </>
  );
}
