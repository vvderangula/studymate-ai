import { useEffect, useRef, useState } from "react";

import { ApiError } from "../api/client";
import {
  clearConversation,
  loadConversation,
  saveConversation,
  type StoredMessage,
} from "../api/conversations";
import type { Citation } from "../api/pdf";
import { chatWithYoutube, processYoutube } from "../api/youtube";

type VideoStatus = "idle" | "processing" | "ready" | "failed";
type ChatStage = "idle" | "searching" | "generating";

type ChatMessage = StoredMessage;

/** Turn a processing failure into a friendly, user-facing message. */
function friendlyProcessError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 0) {
      return "Network error. Please check your connection and try again.";
    }
    if (err.status === 400) {
      return "Please enter a valid YouTube video URL.";
    }
    if (err.status === 422) {
      return "No transcript is available for this video. Try another one.";
    }
    return err.message || "We couldn't process that video. Please try again.";
  }
  return "Network error. Please check your connection and try again.";
}

/** Turn a chat failure into a friendly, user-facing message. */
function friendlyChatError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 0) {
      return "Network error. Please check your connection and try again.";
    }
    if (err.status === 404) {
      return "This video could not be found. Please process it again.";
    }
    if (err.status === 422) {
      return "This video is still being prepared. Please wait for processing to finish.";
    }
    if (err.status === 400) {
      return "Please enter a question.";
    }
    return err.message || "Something went wrong. Please try again.";
  }
  return "Network error. Please check your connection and try again.";
}

/** Learn from YouTube module: process a video transcript, then chat with it. */
export default function YoutubeChat() {
  const [url, setUrl] = useState("");
  const [videoId, setVideoId] = useState("");
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState<VideoStatus>("idle");
  const [processError, setProcessError] = useState("");
  const [stage, setStage] = useState<ChatStage>("idle");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  // Persist the conversation whenever it changes for an active video.
  useEffect(() => {
    if (videoId) {
      saveConversation(videoId, messages);
    }
  }, [videoId, messages]);

  // Keep the latest message in view.
  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages, stage]);

  function pushMessage(message: Omit<ChatMessage, "id">) {
    setMessages((prev) => [...prev, { id: Date.now() + Math.random(), ...message }]);
  }

  async function handleProcess() {
    const trimmed = url.trim();
    if (!trimmed) {
      setProcessError("Please enter a YouTube video URL.");
      return;
    }

    setStatus("processing");
    setProcessError("");
    setError("");

    try {
      const result = await processYoutube(trimmed);
      setVideoId(result.video_id);
      setTitle(result.title);
      setStatus("ready");

      const existing = loadConversation(result.video_id);
      if (existing.length > 0) {
        setMessages(existing);
        return;
      }
      setMessages([
        {
          id: Date.now(),
          role: "assistant",
          text: `"${result.title}" is ready. Ask me anything about this video.`,
        },
      ]);
    } catch (err) {
      setStatus("failed");
      setProcessError(friendlyProcessError(err));
    }
  }

  async function handleSend() {
    const question = input.trim();
    if (!question) {
      setError("Please enter a question.");
      return;
    }
    if (!videoId || stage !== "idle") return;

    setError("");
    pushMessage({ role: "user", text: question });
    setInput("");
    setStage("searching");
    const toGenerating = window.setTimeout(() => setStage("generating"), 400);

    try {
      const result = await chatWithYoutube(videoId, question);
      pushMessage({
        role: "assistant",
        text: result.answer,
        citations: result.citations,
      });
    } catch (err) {
      setError(friendlyChatError(err));
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
    if (videoId) {
      clearConversation(videoId);
    }
    setMessages([]);
    setError("");
  }

  const ready = status === "ready" && Boolean(videoId);
  const busy = stage !== "idle";
  const processing = status === "processing";

  return (
    <div className="space-y-4 sm:space-y-5">
      {/* Video URL & processing */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <label
          htmlFor="youtube-url"
          className="mb-2 block text-sm font-medium text-slate-700"
        >
          YouTube video URL
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            id="youtube-url"
            type="url"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void handleProcess();
              }
            }}
            disabled={processing}
            placeholder="https://www.youtube.com/watch?v=…"
            aria-label="YouTube video URL"
            className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100 disabled:bg-slate-50"
          />
          <button
            type="button"
            onClick={() => void handleProcess()}
            disabled={processing || !url.trim()}
            className="rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-orange-600 disabled:opacity-50"
          >
            {processing ? "Processing…" : "Process"}
          </button>
        </div>

        {processing && (
          <p className="mt-3 text-sm text-slate-500" role="status">
            Retrieving transcript and preparing the video…
          </p>
        )}

        {status === "ready" && title && (
          <p className="mt-3 text-sm text-green-600" role="status">
            "{title}" is ready to chat.
          </p>
        )}

        {status === "failed" && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            {processError}
          </p>
        )}

        {status === "idle" && processError && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            {processError}
          </p>
        )}
      </div>

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
            <EmptyState status={status} />
          ) : messages.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-400">
              No messages yet. Ask your first question below.
            </p>
          ) : (
            messages.map((message) => (
              <MessageBubble key={message.id} message={message} videoId={videoId} />
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
                  ? "Searching the transcript…"
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
            aria-label="Ask a question about this video"
            placeholder={
              ready
                ? "Ask a question…  (Enter to send, Shift+Enter for a new line)"
                : "Process a video to start chatting"
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
function EmptyState({ status }: { status: VideoStatus }) {
  const message =
    status === "processing"
      ? "Preparing your video… this may take a moment."
      : status === "failed"
        ? "We couldn't prepare that video. Please try another URL."
        : "No video yet. Paste a YouTube URL above to start a conversation.";

  return (
    <div className="flex h-full min-h-[8rem] flex-col items-center justify-center gap-2 py-8 text-center">
      <p className="text-sm text-slate-500">{message}</p>
    </div>
  );
}

/** A single chat bubble, with timestamp citations for grounded AI answers. */
function MessageBubble({
  message,
  videoId,
}: {
  message: ChatMessage;
  videoId: string;
}) {
  const isUser = message.role === "user";
  return (
    <div className={isUser ? "flex justify-end" : "flex justify-start"}>
      <div
        className={
          "max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm leading-relaxed " +
          (isUser ? "bg-orange-500 text-white" : "bg-slate-100 text-slate-800")
        }
      >
        {message.text}
        {!isUser && message.citations && message.citations.length > 0 && (
          <Citations citations={message.citations} videoId={videoId} />
        )}
      </div>
    </div>
  );
}

/** Expandable citation sources with clickable timestamp badges. */
function Citations({
  citations,
  videoId,
}: {
  citations: Citation[];
  videoId: string;
}) {
  const [expanded, setExpanded] = useState(false);

  function videoLink(seconds: number | null): string {
    const base = `https://www.youtube.com/watch?v=${videoId}`;
    return seconds != null ? `${base}&t=${seconds}s` : base;
  }

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
        {citations.map((citation) => (
          <a
            key={citation.chunk_id}
            href={videoLink(citation.page)}
            target="_blank"
            rel="noreferrer"
            className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-700 transition-colors hover:bg-orange-200"
          >
            {citation.source_reference}
          </a>
        ))}
      </div>

      {expanded && (
        <ul className="mt-2 space-y-1">
          {citations.map((citation) => (
            <li key={citation.chunk_id} className="text-xs text-slate-500">
              <a
                href={videoLink(citation.page)}
                target="_blank"
                rel="noreferrer"
                className="font-medium text-slate-600 underline-offset-2 hover:underline"
              >
                {citation.source_reference}
              </a>
              {" — jump to this moment in the video"}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
