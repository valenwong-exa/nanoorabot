import { create } from "zustand";
import { persist } from "zustand/middleware";
import { nanoid } from "nanoid";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "tool" | "system" | "sub_tool";
  content: string;
  hiddenPrompts?: string[];
  timestamp: string;
  mediaPaths?: string[];
  isStreaming?: boolean;
  toolCalls?: ToolCallInfo[];
  name?: string; // tool result: the tool's name
  isSubAgent?: boolean; // message originated from a background SubAgent
  serverIndex?: number; // original index in the server session.messages array (used for revoke)
}

export interface ToolCallInfo {
  id: string;
  name: string;
  input?: string;
  output?: string;
}

/** Per-session transient state (waiting indicator, progress text). */
interface SessionState {
  isWaiting: boolean;
  progressText: string;
}

interface DraftSelection {
  start: number;
  end: number;
}

export interface DraftSnippet {
  id: string;
  text: string;
  sourceType: "node_path";
}

interface ChatState {
  currentSessionKey: string | null;
  messages: ChatMessage[];
  showToolMessages: boolean;
  mobileShowChat: boolean;
  draftMessages: Record<string, string>;
  draftSelections: Record<string, DraftSelection>;
  draftSnippets: Record<string, DraftSnippet[]>;
  draftAutoSendTokens: Record<string, number>;

  /** Per-session waiting / progress state — keyed by session key. */
  sessionStates: Record<string, SessionState>;

  // Convenience getters for the *current* session
  isWaiting: boolean;
  progressText: string;

  setMobileShowChat: (v: boolean) => void;
  setDraftMessage: (value: string, sessionKey?: string) => void;
  setDraftSelection: (start: number, end?: number, sessionKey?: string) => void;
  insertDraftMessage: (value: string, sessionKey?: string) => void;
  addDraftSnippet: (text: string, sessionKey?: string) => void;
  requestDraftAutoSend: (sessionKey?: string) => void;
  clearDraftAutoSend: (sessionKey?: string) => void;
  updateDraftSnippet: (snippetId: string, text: string, sessionKey?: string) => void;
  removeDraftSnippet: (snippetId: string, sessionKey?: string) => void;
  clearDraftSnippets: (sessionKey?: string) => void;
  setCurrentSession: (key: string | null, options?: { preserveMessages?: boolean }) => void;
  addMessage: (msg: ChatMessage) => void;
  appendAssistantText: (id: string, text: string) => void;
  setStreaming: (id: string, isStreaming: boolean) => void;
  /** Set progress for a specific session (defaults to current). */
  setProgress: (text: string, sessionKey?: string) => void;
  /** Set waiting for a specific session (defaults to current). */
  setWaiting: (v: boolean, sessionKey?: string) => void;
  clearMessages: () => void;
  setMessages: (msgs: ChatMessage[]) => void;
  toggleToolMessages: () => void;
  /** Get waiting state for a specific session. */
  getSessionState: (key: string) => SessionState;
}

const DEFAULT_SESSION_STATE: SessionState = { isWaiting: false, progressText: "" };

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      currentSessionKey: null,
      messages: [],
      showToolMessages: false,
      mobileShowChat: false,
      draftMessages: {},
      draftSelections: {},
      draftSnippets: {},
      draftAutoSendTokens: {},
      sessionStates: {},

      // Derived from sessionStates[currentSessionKey]
      get isWaiting() {
        const s = get();
        return (s.sessionStates[s.currentSessionKey ?? ""] ?? DEFAULT_SESSION_STATE).isWaiting;
      },
      get progressText() {
        const s = get();
        return (s.sessionStates[s.currentSessionKey ?? ""] ?? DEFAULT_SESSION_STATE).progressText;
      },

      setMobileShowChat: (v) => set({ mobileShowChat: v }),

      setDraftMessage: (value, sessionKey?) =>
        set((state) => {
          const key = sessionKey ?? state.currentSessionKey ?? "";
          if (!key) {
            return state;
          }
          return {
            draftMessages: {
              ...state.draftMessages,
              [key]: value,
            },
          };
        }),

      setDraftSelection: (start, end, sessionKey?) =>
        set((state) => {
          const key = sessionKey ?? state.currentSessionKey ?? "";
          if (!key) {
            return state;
          }
          return {
            draftSelections: {
              ...state.draftSelections,
              [key]: { start, end: end ?? start },
            },
          };
        }),

      insertDraftMessage: (value, sessionKey?) =>
        set((state) => {
          const key = sessionKey ?? state.currentSessionKey ?? "";
          if (!key) {
            return state;
          }
          const current = state.draftMessages[key] ?? "";
          const selection = state.draftSelections[key] ?? {
            start: current.length,
            end: current.length,
          };
          const next =
            current.slice(0, selection.start) + value + current.slice(selection.end);
          const cursor = selection.start + value.length;
          return {
            draftMessages: {
              ...state.draftMessages,
              [key]: next,
            },
            draftSelections: {
              ...state.draftSelections,
              [key]: { start: cursor, end: cursor },
            },
          };
        }),

      addDraftSnippet: (text, sessionKey?) =>
        set((state) => {
          const key = sessionKey ?? state.currentSessionKey ?? "";
          const normalized = text.trim();
          if (!key || !normalized) {
            return state;
          }
          const current = state.draftSnippets[key] ?? [];
          const currentDraftMessage = state.draftMessages[key] ?? "";
          const shouldInsertSpacer = currentDraftMessage.length === 0;
          return {
            draftSnippets: {
              ...state.draftSnippets,
              [key]: [...current, { id: nanoid(), text: normalized, sourceType: "node_path" }],
            },
            ...(shouldInsertSpacer
              ? {
                  draftMessages: {
                    ...state.draftMessages,
                    [key]: " ",
                  },
                  draftSelections: {
                    ...state.draftSelections,
                    [key]: { start: 1, end: 1 },
                  },
                }
              : {}),
          };
        }),

      requestDraftAutoSend: (sessionKey?) =>
        set((state) => {
          const key = sessionKey ?? state.currentSessionKey ?? "";
          if (!key) {
            return state;
          }
          return {
            draftAutoSendTokens: {
              ...state.draftAutoSendTokens,
              [key]: (state.draftAutoSendTokens[key] ?? 0) + 1,
            },
          };
        }),

      clearDraftAutoSend: (sessionKey?) =>
        set((state) => {
          const key = sessionKey ?? state.currentSessionKey ?? "";
          if (!key) {
            return state;
          }
          return {
            draftAutoSendTokens: {
              ...state.draftAutoSendTokens,
              [key]: 0,
            },
          };
        }),

      updateDraftSnippet: (snippetId, text, sessionKey?) =>
        set((state) => {
          const key = sessionKey ?? state.currentSessionKey ?? "";
          if (!key) {
            return state;
          }
          const current = state.draftSnippets[key] ?? [];
          const normalized = text;
          const next = current
            .map((snippet) => (snippet.id === snippetId ? { ...snippet, text: normalized } : snippet))
            .filter((snippet) => snippet.text.length > 0);
          return {
            draftSnippets: {
              ...state.draftSnippets,
              [key]: next,
            },
          };
        }),

      removeDraftSnippet: (snippetId, sessionKey?) =>
        set((state) => {
          const key = sessionKey ?? state.currentSessionKey ?? "";
          if (!key) {
            return state;
          }
          const current = state.draftSnippets[key] ?? [];
          const nextSnippets = current.filter((snippet) => snippet.id !== snippetId);
          const currentDraftMessage = state.draftMessages[key] ?? "";
          const shouldClearSpacer = nextSnippets.length === 0 && currentDraftMessage === " ";
          return {
            draftSnippets: {
              ...state.draftSnippets,
              [key]: nextSnippets,
            },
            ...(shouldClearSpacer
              ? {
                  draftMessages: {
                    ...state.draftMessages,
                    [key]: "",
                  },
                  draftSelections: {
                    ...state.draftSelections,
                    [key]: { start: 0, end: 0 },
                  },
                }
              : {}),
          };
        }),

      clearDraftSnippets: (sessionKey?) =>
        set((state) => {
          const key = sessionKey ?? state.currentSessionKey ?? "";
          if (!key) {
            return state;
          }
          const currentDraftMessage = state.draftMessages[key] ?? "";
          const shouldClearSpacer = currentDraftMessage === " ";
          return {
            draftSnippets: {
              ...state.draftSnippets,
              [key]: [],
            },
            ...(shouldClearSpacer
              ? {
                  draftMessages: {
                    ...state.draftMessages,
                    [key]: "",
                  },
                  draftSelections: {
                    ...state.draftSelections,
                    [key]: { start: 0, end: 0 },
                  },
                }
              : {}),
          };
        }),

      setCurrentSession: (key, options) =>
        set((state) => {
          const currentKey = state.currentSessionKey;
          const shouldPreserveMessages =
            options?.preserveMessages === true &&
            !!currentKey &&
            !!key &&
            currentKey !== key &&
            state.messages.length > 0;
          return {
            currentSessionKey: key,
            messages:
              currentKey === key || shouldPreserveMessages
                ? state.messages
                : [],
          };
        }),

      addMessage: (msg) =>
        set((state) => ({ messages: [...state.messages, msg] })),

      appendAssistantText: (id, text) =>
        set((state) => ({
          messages: state.messages.map((m) =>
            m.id === id ? { ...m, content: m.content + text } : m
          ),
        })),

      setStreaming: (id, isStreaming) =>
        set((state) => ({
          messages: state.messages.map((m) =>
            m.id === id ? { ...m, isStreaming } : m
          ),
        })),

      setProgress: (progressText, sessionKey?) =>
        set((state) => {
          const key = sessionKey ?? state.currentSessionKey ?? "";
          const prev = state.sessionStates[key] ?? DEFAULT_SESSION_STATE;
          return {
            sessionStates: { ...state.sessionStates, [key]: { ...prev, progressText } },
          };
        }),

      setWaiting: (isWaiting, sessionKey?) =>
        set((state) => {
          const key = sessionKey ?? state.currentSessionKey ?? "";
          const prev = state.sessionStates[key] ?? DEFAULT_SESSION_STATE;
          return {
            sessionStates: {
              ...state.sessionStates,
              [key]: { ...prev, isWaiting, ...(isWaiting ? {} : { progressText: "" }) },
            },
          };
        }),

      clearMessages: () => set({ messages: [] }),

      setMessages: (messages) => set({ messages }),

      toggleToolMessages: () =>
        set((state) => ({ showToolMessages: !state.showToolMessages })),

      getSessionState: (key) => {
        return get().sessionStates[key] ?? DEFAULT_SESSION_STATE;
      },
    }),
    {
      name: "nanobot-chat",
      partialize: (state) => ({
        currentSessionKey: state.currentSessionKey,
        messages: state.messages,
        showToolMessages: state.showToolMessages,
      }),
    }
  )
);
