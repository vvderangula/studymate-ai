import { useEffect, useState } from "react";

import { useChatScroll } from "../hooks/useChatScroll";

import { ApiError } from "../api/client";
import {
  clearConversation,
  getLastPdfId,
  loadConversation,
  saveConversation,
  setLastPdfId,
  type StoredMessage,
} from "../api/conversations";
import { chatWithPdf, type Citation, type ProcessResult } from "../api/pdf";
import PdfUpload from "./PdfUpload";

type UploadStatus = "idle" | "uploading" | "processing" | "ready" | "failed";
type ChatStage = "idle" | "searching" | "generating";

type ChatMessage = StoredMessage;

/** Turn a chat failure into a friendly, user-facing message. */
function friendlyError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 0) {
      return "Network error. Please check your connection and try again.";
    }
    if (err.status === 404) {
      return "This PDF could not be found. Please upload it again.";
    }
    if (err.status === 422) {
      return "Your PDF is still being prepared. Please wait for processing to finish.";
    }
    if (err.status === 400) {
      return "Please enter a question.";
    }
    return err.message || "Something went wrong. Please try again.";
  }
  return "Network error. Please check your connection and try again.";
}

/** Learn from PDF module: upload and process a PDF, then chat with its contents. */
export default function PdfChat() {
  const [fileId, setFileId] = useState<string>("");
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [stage, setStage] = useState<ChatStage>("idle");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState("");
  // Resume the most recent conversation on first mount, if one exists.
  useEffect(() => {
    const lastId = getLastPdfId();
    if (lastId) {
      setFileId(lastId);
      setMessages(loadConversation(lastId));
      setUploadStatus("ready");
    }
  }, []);

  // Persist the conversation whenever it changes for an active PDF.
  useEffect(() => {
    if (fileId) {
      saveConversation(fileId, messages);
    }
  }, [fileId, messages]);

  // Keep the latest message in view.
  const endRef = useChatScroll([messages, stage]);

  function pushMessage(message: Omit<ChatMessage, "id">) {
    setMessages((prev) => [...prev, { id: Date.now() + Math.random(), ...message }]);
  }

  function handleProcessed(id: string, result: ProcessResult) {
    setLastPdfId(id);
    setFileId(id);
    setError("");

    const existing = loadConversation(id);
    if (existing.length > 0) {
      setMessages(existing);
      return;
    }
    setMessages([
      {
        id: Date.now(),
        role: "assistant",
        text: `Your PDF is ready (${result.page_count ?? 0} pages, ${
          result.chunk_count ?? 0
        } chunks). Ask me anything about it.`,
      },
    ]);
  }

  async function handleSend() {
    const question = input.trim();
    if (!question) {
      setError("Please enter a question.");
      return;
    }
    if (!fileId || stage !== "idle") return;

    setError("");
    pushMessage({ role: "user", text: question });
    setInput("");
    setStage("searching");
    const toGenerating = window.setTimeout(() => setStage("generating"), 400);

    try {
      const result = await chatWithPdf(fileId, question);
      pushMessage({
        role: "assistant",
        text: result.answer,
        citations: result.citations,
      });
    } catch (err) {
      setError(friendlyError(err));
    } finally {
      window.clearTimeout(toGenerating);
      setStage("idle");
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSend();
    }
  }

  function handleClear() {
    if (fileId) {
      clearConversation(fileId);
    }
    setMessages([]);
    setError("");
  }

  const ready = uploadStatus === "ready" && Boolean(fileId);
  const busy = stage !== "idle";

  return (
    <div className="space-y-4 sm:space-y-5">
      {/* Upload & processing */}
      <PdfUpload onProcessed={handleProcessed} onStatusChange={setUploadStatus} />

      {/* Chat */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-slate-700">Chat</h2>
          {ready && messages.length > 0 && (
            <button
              type="button"
              onClick={handleClear}
              className="rounded-md px-2 py-1 text-xs font-medium text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
            >
              Clear conversation
            </button>
          )}
        </div>

        {/* Conversation */}
        <div
          className="max-h-[26rem] min-h-[8rem] space-y-3 overflow-y-auto pr-1"
          role="log"
          aria-live="polite"
          aria-label="Conversation"
        >
          {!ready ? (
            <EmptyState status={uploadStatus} />
          ) : messages.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-400">
              No messages yet. Ask your first question below.
            </p>
          ) : (
            messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))
          )}

          {busy && (
            <div
              className="mr-auto max-w-[85%] rounded-2xl bg-slate-100 px-4 py-2 text-sm text-slate-500"
              role="status"
            >
              <span className="inline-flex items-center gap-2">
                <span className="h-2 w-2 animate-pulse rounded-full bg-orange-400" />
                {stage === "searching"
                  ? "Searching your PDF…"
                  : "Generating answer…"}
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
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!ready || busy}
            rows={1}
            aria-label="Ask a question about your PDF"
            placeholder={
              ready
                ? "Ask a question…  (Enter to send, Shift+Enter for a new line)"
                : "Upload a PDF to start chatting"
            }
            className="max-h-32 min-h-[2.75rem] flex-1 resize-y rounded-lg border border-slate-300 px-4 py-2.5 text-sm leading-relaxed outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100 disabled:bg-slate-50"
          />
          <button
            type="button"
            onClick={() => void handleSend()}
            disabled={!ready || busy || !input.trim()}
            className="rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-orange-600 disabled:opacity-50"
          >
            {busy ? "…" : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

/** Contextual empty state shown before the chat is usable. */
function EmptyState({ status }: { status: UploadStatus }) {
  const message =
    status === "uploading"
      ? "Uploading your PDF…"
      : status === "processing"
        ? "Preparing your PDF… this may take a moment."
        : status === "failed"
          ? "We couldn't prepare that PDF. Please try uploading it again."
          : "No PDF yet. Upload one above to start a conversation.";

  return (
    <div className="flex h-full min-h-[8rem] flex-col items-center justify-center gap-2 py-8 text-center">
      <p className="text-sm text-slate-500">{message}</p>
    </div>
  );
}

/** A single chat bubble, with citations for grounded AI answers. */
function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={isUser ? "flex justify-end" : "flex justify-start"}>
      <div
        className={
          "max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm leading-relaxed " +
          (isUser
            ? "bg-orange-500 text-white"
            : "bg-slate-100 text-slate-800")
        }
      >
        {message.text}
        {!isUser && message.citations && message.citations.length > 0 && (
          <Citations citations={message.citations} />
        )}
      </div>
    </div>
  );
}

/** Expandable citation sources with clickable page badges. */
function Citations({ citations }: { citations: Citation[] }) {
  const [expanded, setExpanded] = useState(false);
  const pages = Array.from(
    new Set(
      citations
        .map((citation) => citation.page)
        .filter((page): page is number => page != null),
    ),
  );

  return (
    <div className="mt-2 border-t border-slate-200 pt-2">
      <div className="flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          className="rounded-md px-1.5 py-0.5 text-xs font-medium text-slate-500 transition-colors hover:bg-slate-200"
        >
          {expanded ? "Hide sources" : `Sources (${citations.length})`}
        </button>
        {pages.map((page) => (
          <button
            key={page}
            type="button"
            onClick={() => setExpanded(true)}
            className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-700 transition-colors hover:bg-orange-200"
          >
            Page {page}
          </button>
        ))}
      </div>

      {expanded && (
        <ul className="mt-2 space-y-1">
          {citations.map((citation) => (
            <li
              key={citation.chunk_id}
              className="text-xs text-slate-500"
            >
              <span className="font-medium text-slate-600">
                {citation.page != null ? `Page ${citation.page}` : "Source"}
              </span>
              {" — "}
              {citation.source_reference}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
