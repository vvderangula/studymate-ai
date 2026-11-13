import { useEffect, useRef, useState } from "react";

import { useChatScroll } from "../hooks/useChatScroll";
import { useAuth } from "../context/AuthContext";

import { ApiError } from "../api/client";
import type { StoredMessageDto } from "../api/history";
import type { Citation } from "../api/pdf";
import {
  chatWithYoutube,
  clearVideoMessages,
  deleteVideo,
  getVideoMessages,
  listVideos,
  processYoutube,
  type VideoItem,
} from "../api/youtube";
import { timeAgo } from "../lib/time";
import HistoryList from "./HistoryList";
import { IconChevronRight } from "./icons";
import { EmptyNote, ErrorNotice, ProgressNotice, TypingIndicator } from "./ui";
import { AsideCard, Workspace } from "./workspace";
import Markdown from "./Markdown";

type VideoStatus = "idle" | "processing" | "ready" | "failed";
type ChatStage = "idle" | "searching" | "generating";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
}

function fromStored(message: StoredMessageDto): ChatMessage {
  return { id: message.id, role: message.role, text: message.text, citations: message.citations };
}

function localId(): string {
  return `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return "";
  const minutes = Math.round(seconds / 60);
  return minutes >= 60 ? `${Math.floor(minutes / 60)}h ${minutes % 60}m` : `${minutes} min`;
}

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
  const { user } = useAuth();
  const userId = user?.user_id;
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [videosLoading, setVideosLoading] = useState(true);
  const [url, setUrl] = useState("");
  const [videoId, setVideoId] = useState("");
  const [status, setStatus] = useState<VideoStatus>("idle");
  const [processError, setProcessError] = useState("");
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [stage, setStage] = useState<ChatStage>("idle");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState("");
  const openingRef = useRef("");

  const selected = videos.find((video) => video.video_id === videoId) ?? null;
  const title = selected?.title ?? "";

  async function openVideo(id: string) {
    openingRef.current = id;
    setVideoId(id);
    setStatus("ready");
    setError("");
    setInput("");
    setMessages([]);
    setLoadingMessages(true);
    try {
      const result = await getVideoMessages(id);
      if (openingRef.current === id) setMessages(result.messages.map(fromStored));
    } catch (err) {
      if (openingRef.current === id) setError(friendlyChatError(err));
    } finally {
      if (openingRef.current === id) setLoadingMessages(false);
    }
  }

  // Load the library and reopen the most recently active video.
  useEffect(() => {
    let live = true;
    setVideosLoading(true);
    setVideoId("");
    setStatus("idle");
    setMessages([]);
    listVideos()
      .then((items) => {
        if (!live) return;
        setVideos(items);
        if (items[0]) void openVideo(items[0].video_id);
      })
      .catch((err) => {
        if (live) setError(friendlyChatError(err));
      })
      .finally(() => {
        if (live) setVideosLoading(false);
      });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  // Keep the latest message in view.
  const endRef = useChatScroll([messages, stage]);

  function pushMessage(message: Omit<ChatMessage, "id">) {
    setMessages((prev) => [...prev, { id: localId(), ...message }]);
  }

  function touchVideo(id: string, extraMessages: number) {
    setVideos((prev) => {
      const video = prev.find((item) => item.video_id === id);
      if (!video) return prev;
      const updated = {
        ...video,
        message_count: video.message_count + extraMessages,
        last_active: new Date().toISOString(),
      };
      return [updated, ...prev.filter((item) => item.video_id !== id)];
    });
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
      const items = await listVideos().catch(() => videos);
      setVideos(items);
      setUrl("");
      await openVideo(result.video_id);
      // A first visit gets a short welcome; a returning one shows its history.
      setMessages((prev) =>
        prev.length > 0
          ? prev
          : [
              {
                id: localId(),
                role: "assistant",
                text: `"${result.title}" is ready. Ask me anything about this video.`,
              },
            ],
      );
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
      touchVideo(videoId, 2);
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

  async function handleClear() {
    if (!videoId) return;
    try {
      await clearVideoMessages(videoId);
      setMessages([]);
      setError("");
      setVideos((prev) =>
        prev.map((video) => (video.video_id === videoId ? { ...video, message_count: 0 } : video)),
      );
    } catch (err) {
      setError(friendlyChatError(err));
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteVideo(id);
    } catch (err) {
      setError(friendlyChatError(err));
      return;
    }
    const remaining = videos.filter((video) => video.video_id !== id);
    setVideos(remaining);
    if (id === videoId) {
      if (remaining[0]) {
        void openVideo(remaining[0].video_id);
      } else {
        openingRef.current = "";
        setVideoId("");
        setStatus("idle");
        setMessages([]);
      }
    }
  }

  const ready = status === "ready" && Boolean(videoId);
  const busy = stage !== "idle";
  const processing = status === "processing";

  return (
    <Workspace
      aside={
        <>
          {(videos.length > 0 || videosLoading) && (
            <HistoryList
              title="Your videos"
              loading={videosLoading}
              items={videos.map((video) => ({
                id: video.video_id,
                title: video.title,
                subtitle: [
                  formatDuration(video.duration),
                  video.message_count > 0 ? `${video.message_count} messages` : "",
                ]
                  .filter(Boolean)
                  .join(", "),
                meta: timeAgo(video.last_active),
              }))}
              selectedId={videoId}
              emptyText="No videos yet."
              onSelect={(id) => void openVideo(id)}
              onDelete={(id) => void handleDelete(id)}
            />
          )}
        <AsideCard title={videos.length > 0 ? "Add a video" : "Video"}>
          <label htmlFor="youtube-url" className="field-label">
            YouTube video URL
          </label>
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
            className="field"
          />
          <button
            type="button"
            onClick={() => void handleProcess()}
            disabled={processing || !url.trim()}
            className="btn-primary mt-3 w-full"
          >
            {processing && <span className="spinner" aria-hidden="true" />}
            {processing ? "Processing…" : "Process"}
          </button>

          {processing && (
            <ProgressNotice className="mt-3">
              Retrieving transcript and preparing the video…
            </ProgressNotice>
          )}
          {status === "failed" && <ErrorNotice className="mt-3">{processError}</ErrorNotice>}
          {status === "idle" && processError && (
            <ErrorNotice className="mt-3">{processError}</ErrorNotice>
          )}
          <p className="mt-3 text-xs leading-5 text-muted">
            Works with any video that has captions or an auto-generated transcript.
          </p>
        </AsideCard>
        </>
      }
    >
      <div className="pane">
        <div className="pane-head">
          <div className="min-w-0">
            <h2 className="section-title">Chat</h2>
            {ready && title && (
              <p className="truncate text-xs text-muted">Answers come from {title}</p>
            )}
          </div>
          {ready && messages.length > 0 && (
            <button type="button" onClick={() => void handleClear()} className="btn-ghost -mr-2">
              Clear conversation
            </button>
          )}
        </div>

        <div className="pane-scroll">
          <div className="chat-log" role="log" aria-live="polite" aria-label="Conversation">
            {loadingMessages ? (
              <div className="space-y-4" role="status" aria-label="Loading conversation">
                <div className="skeleton ml-auto h-10 w-2/3" />
                <div className="skeleton h-20 w-5/6" />
              </div>
            ) : !ready ? (
              <EmptyState status={status} />
            ) : messages.length === 0 ? (
              <EmptyNote>No messages yet. Ask your first question below.</EmptyNote>
            ) : (
              messages.map((message) => (
                <MessageBubble key={message.id} message={message} videoId={videoId} />
              ))
            )}

            {busy && (
              <TypingIndicator>
                {stage === "searching" ? "Searching the transcript…" : "Generating answer…"}
              </TypingIndicator>
            )}

            <div ref={endRef} />
          </div>
        </div>

        <div className="pane-foot">
          <div className="mx-auto w-full max-w-reading">
            {error && <ErrorNotice className="mb-3">{error}</ErrorNotice>}
            <div className="composer">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
                disabled={!ready || busy}
                rows={1}
                aria-label="Ask a question about this video"
                placeholder={
                  ready ? "Ask a question about this video…" : "Process a video to start chatting"
                }
                className="composer-input"
              />
              <button
                type="button"
                onClick={() => void handleSend()}
                disabled={!ready || busy || !input.trim()}
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

/** Contextual empty state shown before the chat is usable. */
function EmptyState({ status }: { status: VideoStatus }) {
  const message =
    status === "processing"
      ? "Preparing your video… this may take a moment."
      : status === "failed"
        ? "We couldn't prepare that video. Please try another URL."
        : "No video yet. Paste a YouTube link to start a conversation.";

  return <EmptyNote>{message}</EmptyNote>;
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
      <div className={isUser ? "bubble-user" : "bubble-assistant"}>
        {isUser ? message.text : <Markdown>{message.text}</Markdown>}
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
    <div className="mt-3 whitespace-normal border-t border-line pt-3">
      <div className="flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          className="mr-1 inline-flex h-6 items-center gap-1 rounded-md px-1.5 text-xs font-medium text-muted transition-colors hover:bg-sunken hover:text-ink"
        >
          <IconChevronRight
            className={
              "h-3.5 w-3.5 transition-transform duration-150 " + (expanded ? "rotate-90" : "")
            }
          />
          {expanded ? "Hide sources" : `Sources (${citations.length})`}
        </button>
        {citations.map((citation) => (
          <a
            key={citation.chunk_id}
            href={videoLink(citation.page)}
            target="_blank"
            rel="noreferrer"
            className="chip tabular-nums"
          >
            {citation.source_reference}
          </a>
        ))}
      </div>

      {expanded && (
        <ul className="mt-2.5 space-y-1.5 border-l-2 border-accent-line pl-3">
          {citations.map((citation) => (
            <li key={citation.chunk_id} className="text-xs leading-relaxed text-muted">
              <a
                href={videoLink(citation.page)}
                target="_blank"
                rel="noreferrer"
                className="font-medium text-ink-soft underline-offset-2 hover:text-accent hover:underline"
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
