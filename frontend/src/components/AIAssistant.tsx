import { useEffect, useRef, useState } from "react";

import { ApiError } from "../api/client";
import {
  deleteConversation,
  generalChat,
  getConversation,
  listConversations,
} from "../api/assistant";
import type { ConversationSummary } from "../api/history";
import { useChatScroll } from "../hooks/useChatScroll";
import { timeAgo } from "../lib/time";
import AcademicSearch from "./AcademicSearch";
import HistoryList from "./HistoryList";
import { IconPlus } from "./icons";
import Segmented from "./Segmented";
import { EmptyNote, ErrorNotice, TypingIndicator } from "./ui";
import { Workspace } from "./workspace";
import Markdown from "./Markdown";

type Tab = "general" | "research";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
}

function friendlyError(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.status === 0) return "Network error. Please check your connection.";
    if (err.status === 400) return "Invalid request. Please check your input.";
    if (err.status === 502)
      return "AI service is temporarily unavailable. Please try again shortly.";
    return err.message || fallback;
  }
  return "Network error. Please check your connection.";
}

/** AI Assistant: General Chat tab + Research Assistant tab. */
export default function AIAssistant() {
  const [tab, setTab] = useState<Tab>("general");

  return (
    <div className="flex flex-col gap-4 lg:h-full">
      <Segmented
        label="Mode"
        options={[
          { value: "general", label: "General Chat" },
          { value: "research", label: "Research Assistant" },
        ]}
        value={tab}
        onChange={setTab}
        className="grid w-full shrink-0 grid-cols-2 sm:w-96"
      />

      <div
        className={tab === "general" ? "view-enter min-h-0 lg:flex-1" : "hidden"}
        style={{ "--enter-x": "-24px" } as React.CSSProperties}
        aria-hidden={tab !== "general"}
      >
        <GeneralChat />
      </div>

      <div
        className={tab === "research" ? "view-enter min-h-0 lg:flex-1" : "hidden"}
        style={{ "--enter-x": "24px" } as React.CSSProperties}
        aria-hidden={tab !== "research"}
      >
        <AcademicSearch />
      </div>
    </div>
  );
}

/**
 * General chat with saved conversations: the chat list on the left, the
 * selected (or a new) conversation on the right. Every exchange is stored
 * on the server; the model gets the stored turns as context.
 */
function GeneralChat() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loadingChat, setLoadingChat] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const openingRef = useRef<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useChatScroll([messages, busy]);

  useEffect(() => {
    let live = true;
    listConversations()
      .then((items) => {
        if (live) setConversations(items);
      })
      .catch((err) => {
        if (live) setError(friendlyError(err, "Could not load your chats."));
      })
      .finally(() => {
        if (live) setListLoading(false);
      });
    return () => {
      live = false;
    };
  }, []);

  async function openConversation(id: string) {
    openingRef.current = id;
    setActiveId(id);
    setError("");
    setMessages([]);
    setLoadingChat(true);
    try {
      const detail = await getConversation(id);
      if (openingRef.current === id) {
        setMessages(detail.messages.map((m) => ({ id: m.id, role: m.role, text: m.text })));
      }
    } catch (err) {
      if (openingRef.current === id) setError(friendlyError(err, "Could not open this chat."));
    } finally {
      if (openingRef.current === id) setLoadingChat(false);
    }
  }

  function startNewChat() {
    openingRef.current = null;
    setActiveId(null);
    setMessages([]);
    setError("");
    setInput("");
    setLoadingChat(false);
    inputRef.current?.focus();
  }

  async function handleDelete(id: string) {
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((item) => item.id !== id));
      if (id === activeId) startNewChat();
    } catch (err) {
      setError(friendlyError(err, "Could not delete this chat."));
    }
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || busy) return;

    setInput("");
    setError("");
    setMessages((prev) => [...prev, { id: `local-${Date.now()}`, role: "user", text }]);
    setBusy(true);

    try {
      const result = await generalChat(text, activeId);
      setMessages((prev) => [
        ...prev,
        { id: `local-${Date.now()}-a`, role: "assistant", text: result.answer },
      ]);
      openingRef.current = result.conversation_id;
      setActiveId(result.conversation_id);
      // Move (or add) this chat to the top of the list.
      setConversations((prev) => {
        const existing = prev.find((item) => item.id === result.conversation_id);
        const now = new Date().toISOString();
        const updated: ConversationSummary = existing
          ? {
              ...existing,
              message_count: existing.message_count + 2,
              preview: result.answer.slice(0, 160),
              updated_at: now,
            }
          : {
              id: result.conversation_id,
              kind: "assistant",
              title: result.title,
              source_id: null,
              message_count: 2,
              preview: result.answer.slice(0, 160),
              created_at: now,
              updated_at: now,
            };
        return [updated, ...prev.filter((item) => item.id !== result.conversation_id)];
      });
    } catch (err) {
      setError(friendlyError(err, "Failed to get a response. Please try again."));
    } finally {
      setBusy(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  const activeTitle = conversations.find((item) => item.id === activeId)?.title;

  return (
    <Workspace
      aside={
        <HistoryList
          title="Your chats"
          loading={listLoading}
          items={conversations.map((item) => ({
            id: item.id,
            title: item.title,
            subtitle: item.preview,
            meta: timeAgo(item.updated_at),
          }))}
          selectedId={activeId}
          emptyText="Your chats will appear here."
          onSelect={(id) => void openConversation(id)}
          onDelete={(id) => void handleDelete(id)}
          action={
            <button type="button" onClick={startNewChat} className="btn-quiet">
              <IconPlus className="h-4 w-4" />
              New chat
            </button>
          }
        />
      }
    >
      <div className="pane">
        <div className="pane-head">
          <h2 className="section-title min-w-0 truncate">{activeTitle ?? "New chat"}</h2>
          <span className="hidden shrink-0 text-xs text-muted sm:inline">Saved automatically</span>
        </div>

        <div className="pane-scroll">
          <div
            className="chat-log"
            role="log"
            aria-live="polite"
            aria-label="General chat conversation"
          >
            {loadingChat ? (
              <div className="space-y-4" role="status" aria-label="Loading chat">
                <div className="skeleton ml-auto h-10 w-2/3" />
                <div className="skeleton h-20 w-5/6" />
              </div>
            ) : messages.length === 0 ? (
              <EmptyNote>Ask me anything. I can explain a concept, check your understanding or help you plan revision.</EmptyNote>
            ) : (
              messages.map((message) => {
                const isUser = message.role === "user";
                return (
                  <div
                    key={message.id}
                    className={isUser ? "flex justify-end" : "flex justify-start"}
                  >
                    <div className={isUser ? "bubble-user" : "bubble-assistant"}>
                      {isUser ? message.text : <Markdown>{message.text}</Markdown>}
                    </div>
                  </div>
                );
              })
            )}

            {busy && <TypingIndicator>Thinking…</TypingIndicator>}

            <div ref={endRef} />
          </div>
        </div>

        <div className="pane-foot">
          <div className="mx-auto w-full max-w-reading">
            {error && <ErrorNotice className="mb-3">{error}</ErrorNotice>}
            <div className="composer">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={busy}
                rows={1}
                placeholder="Ask me anything…"
                aria-label="Chat message"
                className="composer-input"
              />
              <button
                type="button"
                onClick={() => void handleSend()}
                disabled={busy || !input.trim()}
                className="composer-send"
              >
                {busy && <span className="spinner" aria-hidden="true" />}
                Send
              </button>
            </div>
            <p className="mt-2 hidden text-center text-xs text-faint sm:block">
              Enter to send, Shift + Enter for a new line
            </p>
          </div>
        </div>
      </div>
    </Workspace>
  );
}
