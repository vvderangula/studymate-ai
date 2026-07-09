import { useState } from "react";

import { ApiError } from "../api/client";
import { generalChat, type ChatTurn } from "../api/assistant";
import { useChatScroll } from "../hooks/useChatScroll";
import AcademicSearch from "./AcademicSearch";

type Tab = "general" | "research";

interface ChatMessage {
  id: number;
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
    <div className="space-y-5">
      {/* Mode selector — styled as a pill toggle, not a nav bar */}
      <div className="flex flex-col gap-1">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Mode
        </p>
        <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-1">
          {(["general", "research"] as Tab[]).map((name) => {
            const isActive = tab === name;
            return (
              <button
                key={name}
                type="button"
                onClick={() => setTab(name)}
                className={
                  "rounded-md px-5 py-2 text-sm font-medium transition-colors " +
                  (isActive
                    ? "bg-white text-orange-600 shadow-sm"
                    : "text-slate-500 hover:text-slate-700")
                }
              >
                {name === "general" ? "General Chat" : "Research Assistant"}
              </button>
            );
          })}
        </div>
      </div>

      {tab === "general" ? <GeneralChat /> : <AcademicSearch />}
    </div>
  );
}

/** ChatGPT-like general chat panel using the shared LLM service. */
function GeneralChat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useChatScroll([messages, busy]);

  async function handleSend() {
    const text = input.trim();
    if (!text || busy) return;

    setInput("");
    setError("");

    const userMsg: ChatMessage = { id: Date.now(), role: "user", text };
    setMessages((prev) => [...prev, userMsg]);
    setBusy(true);

    // Build history for context (all previous turns)
    const history: ChatTurn[] = messages.map((m) => ({
      role: m.role,
      content: m.text,
    }));

    try {
      const result = await generalChat(text, history);
      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, role: "assistant", text: result.answer },
      ]);
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

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
      {/* Conversation */}
      <div
        className="max-h-[26rem] min-h-[8rem] space-y-3 overflow-y-auto pr-1"
        role="log"
        aria-live="polite"
        aria-label="General chat conversation"
      >
        {messages.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-400">
            Ask me anything — I'm here to help you study.
          </p>
        ) : (
          messages.map((message) => {
            const isUser = message.role === "user";
            return (
              <div
                key={message.id}
                className={isUser ? "flex justify-end" : "flex justify-start"}
              >
                <div
                  className={
                    "max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm leading-relaxed " +
                    (isUser
                      ? "bg-orange-500 text-white"
                      : "bg-slate-100 text-slate-800")
                  }
                >
                  {message.text}
                </div>
              </div>
            );
          })
        )}

        {busy && (
          <div
            className="mr-auto max-w-[85%] rounded-2xl bg-slate-100 px-4 py-2 text-sm text-slate-500"
            role="status"
          >
            <span className="inline-flex items-center gap-2">
              <span className="h-2 w-2 animate-pulse rounded-full bg-orange-400" />
              Thinking…
            </span>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {error && (
        <p className="mt-3 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {/* Composer */}
      <div className="mt-4 flex items-end gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={busy}
          rows={1}
          placeholder="Ask me anything…  (Enter to send, Shift+Enter for new line)"
          aria-label="Chat message"
          className="max-h-32 min-h-[2.75rem] flex-1 resize-y rounded-lg border border-slate-300 px-4 py-2.5 text-sm leading-relaxed outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100 disabled:bg-slate-50"
        />
        <button
          type="button"
          onClick={() => void handleSend()}
          disabled={busy || !input.trim()}
          className="rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-orange-600 disabled:opacity-50"
        >
          {busy ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}
