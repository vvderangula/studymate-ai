import { useEffect, useRef, useState } from "react";

import { useChatScroll } from "../hooks/useChatScroll";
import { useAuth } from "../context/AuthContext";

import { ApiError } from "../api/client";
import type { StoredMessageDto } from "../api/history";
import {
  chatWithPdf,
  clearPdfMessages,
  deleteDocument,
  getPdfMessages,
  listDocuments,
  type Citation,
  type DocumentItem,
  type ProcessResult,
} from "../api/pdf";
import { timeAgo } from "../lib/time";
import HistoryList from "./HistoryList";
import PdfUpload from "./PdfUpload";
import { IconChevronRight } from "./icons";
import { EmptyNote, ErrorNotice, TypingIndicator } from "./ui";
import { AsideCard, Workspace } from "./workspace";
import Markdown from "./Markdown";

type UploadStatus = "idle" | "uploading" | "processing" | "ready" | "failed";
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

function describe(doc: DocumentItem): string {
  if (doc.processing_status === "failed") return "Couldn't read this PDF";
  if (doc.processing_status !== "completed") return "Not processed yet";
  const pages = `${doc.page_count ?? 0} page${doc.page_count === 1 ? "" : "s"}`;
  return doc.message_count > 0 ? `${pages}, ${doc.message_count} messages` : pages;
}

/**
 * Learn from PDF: the user's PDF library on the left (stored on the server),
 * and the saved conversation with the selected PDF on the right.
 */
export default function PdfChat() {
  const { user } = useAuth();
  const userId = user?.user_id;
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [fileId, setFileId] = useState<string>("");
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [stage, setStage] = useState<ChatStage>("idle");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState("");
  // The PDF most recently asked for; late responses for others are ignored.
  const openingRef = useRef("");

  const selected = documents.find((doc) => doc.id === fileId) ?? null;

  async function openDocument(id: string) {
    openingRef.current = id;
    setFileId(id);
    setError("");
    setInput("");
    setMessages([]);
    setLoadingMessages(true);
    try {
      const result = await getPdfMessages(id);
      if (openingRef.current === id) setMessages(result.messages.map(fromStored));
    } catch (err) {
      if (openingRef.current === id) setError(friendlyError(err));
    } finally {
      if (openingRef.current === id) setLoadingMessages(false);
    }
  }

  // Load the library and reopen the most recently active PDF.
  useEffect(() => {
    let live = true;
    setDocsLoading(true);
    setFileId("");
    setMessages([]);
    listDocuments()
      .then((docs) => {
        if (!live) return;
        setDocuments(docs);
        const recent = docs.find((doc) => doc.processing_status === "completed");
        if (recent) void openDocument(recent.id);
      })
      .catch((err) => {
        if (live) setError(friendlyError(err));
      })
      .finally(() => {
        if (live) setDocsLoading(false);
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

  /** Bump a document to the top of the list after activity. */
  function touchDocument(id: string, extraMessages: number) {
    setDocuments((prev) => {
      const doc = prev.find((item) => item.id === id);
      if (!doc) return prev;
      const updated = {
        ...doc,
        message_count: doc.message_count + extraMessages,
        last_active: new Date().toISOString(),
      };
      return [updated, ...prev.filter((item) => item.id !== id)];
    });
  }

  function handleProcessed(id: string, result: ProcessResult, name = "") {
    const now = new Date().toISOString();
    const fresh: DocumentItem = {
      id,
      original_name: name || "Your PDF",
      size: 0,
      upload_time: now,
      processing_status: "completed",
      processed_at: result.processed_at,
      page_count: result.page_count,
      chunk_count: result.chunk_count,
      message_count: 0,
      last_active: now,
    };
    setDocuments((prev) => [fresh, ...prev.filter((doc) => doc.id !== id)]);
    openingRef.current = id;
    setFileId(id);
    setError("");
    setLoadingMessages(false);
    setMessages([
      {
        id: localId(),
        role: "assistant",
        text: `Your PDF is ready (${result.page_count ?? 0} pages, ${
          result.chunk_count ?? 0
        } chunks). Ask me anything about it.`,
      },
    ]);
    // Pick up exact server values (size etc.) in the background.
    listDocuments()
      .then(setDocuments)
      .catch(() => undefined);
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
      touchDocument(fileId, 2);
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

  async function handleClear() {
    if (!fileId) return;
    try {
      await clearPdfMessages(fileId);
      setMessages([]);
      setError("");
      setDocuments((prev) =>
        prev.map((doc) => (doc.id === fileId ? { ...doc, message_count: 0 } : doc)),
      );
    } catch (err) {
      setError(friendlyError(err));
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteDocument(id);
    } catch (err) {
      setError(friendlyError(err));
      return;
    }
    const remaining = documents.filter((doc) => doc.id !== id);
    setDocuments(remaining);
    if (id === fileId) {
      const next = remaining.find((doc) => doc.processing_status === "completed");
      if (next) {
        void openDocument(next.id);
      } else {
        openingRef.current = "";
        setFileId("");
        setMessages([]);
      }
    }
  }

  const ready = Boolean(selected && selected.processing_status === "completed");
  const busy = stage !== "idle";
  const hasDocs = documents.length > 0;

  return (
    <Workspace
      aside={
        <>
          {(hasDocs || docsLoading) && (
            <HistoryList
              title="Your PDFs"
              loading={docsLoading}
              items={documents.map((doc) => ({
                id: doc.id,
                title: doc.original_name,
                subtitle: describe(doc),
                meta: timeAgo(doc.last_active),
              }))}
              selectedId={fileId}
              emptyText="No PDFs yet."
              onSelect={(id) => void openDocument(id)}
              onDelete={(id) => void handleDelete(id)}
            />
          )}
          <AsideCard title={hasDocs ? "Add a PDF" : "Upload a PDF"}>
            <PdfUpload
              compact={hasDocs}
              onProcessed={handleProcessed}
              onStatusChange={setUploadStatus}
            />
          </AsideCard>
        </>
      }
    >
      <div className="pane">
        <div className="pane-head">
          <div className="min-w-0">
            <h2 className="section-title">Chat</h2>
            {selected && (
              <p className="truncate text-xs text-muted">
                Answers come from {selected.original_name}
              </p>
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
            ) : selected && selected.processing_status === "failed" ? (
              <EmptyNote>
                We couldn't read this PDF. It may be scanned or image-only. Delete it and try
                another file.
              </EmptyNote>
            ) : !ready ? (
              <EmptyState status={uploadStatus} />
            ) : messages.length === 0 ? (
              <EmptyNote>No messages yet. Ask your first question below.</EmptyNote>
            ) : (
              messages.map((message) => <MessageBubble key={message.id} message={message} />)
            )}

            {busy && (
              <TypingIndicator>
                {stage === "searching" ? "Searching your PDF…" : "Generating answer…"}
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
                aria-label="Ask a question about your PDF"
                placeholder={
                  ready ? "Ask a question about your PDF…" : "Upload a PDF to start chatting"
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
function EmptyState({ status }: { status: UploadStatus }) {
  const message =
    status === "uploading"
      ? "Uploading your PDF…"
      : status === "processing"
        ? "Preparing your PDF… this may take a moment."
        : status === "failed"
          ? "We couldn't prepare that PDF. Please try uploading it again."
          : "No PDF yet. Upload one to start a conversation.";

  return <EmptyNote>{message}</EmptyNote>;
}

/** A single chat bubble, with citations for grounded AI answers. */
function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={isUser ? "flex justify-end" : "flex justify-start"}>
      <div className={isUser ? "bubble-user" : "bubble-assistant"}>
        {isUser ? message.text : <Markdown>{message.text}</Markdown>}
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
        {pages.map((page) => (
          <button
            key={page}
            type="button"
            onClick={() => setExpanded(true)}
            className="chip"
          >
            Page {page}
          </button>
        ))}
      </div>

      {expanded && (
        <ul className="mt-2.5 space-y-1.5 border-l-2 border-accent-line pl-3">
          {citations.map((citation) => (
            <li key={citation.chunk_id} className="text-xs leading-relaxed text-muted">
              <span className="font-medium text-ink-soft">
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
