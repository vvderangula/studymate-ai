import { useRef, useState } from "react";

import { ApiError } from "../api/client";
import {
  askPaper,
  searchPapers,
  summarizePaper,
  type PaperItem,
} from "../api/academic";

type SearchStage = "idle" | "searching";
type SummaryStage = "idle" | "loading" | "done";
type AskStage = "idle" | "loading";

interface QAMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
}

/** Per-paper state snapshot stored when switching away from a paper. */
interface PaperState {
  messages: QAMessage[];
  summary: string;
  summaryStage: SummaryStage;
  summaryError: string;
}

function friendlyError(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.status === 0) return "Network error. Please check your connection.";
    if (err.status === 400) return "Invalid request. Please check your input.";
    if (err.status === 503)
      return "Search is temporarily unavailable. Please try again shortly.";
    if (err.status === 502)
      return "AI service is temporarily unavailable. Please try again shortly.";
    return err.message || fallback;
  }
  return "Network error. Please check your connection.";
}

/** AI Academic Search: search papers, read summaries, ask questions. */
export default function AcademicSearch() {
  const [query, setQuery] = useState("");
  const [searchStage, setSearchStage] = useState<SearchStage>("idle");
  const [searchError, setSearchError] = useState("");
  const [papers, setPapers] = useState<PaperItem[]>([]);
  const [searchedQuery, setSearchedQuery] = useState("");

  const [selectedPaper, setSelectedPaper] = useState<PaperItem | null>(null);
  const [summaryStage, setSummaryStage] = useState<SummaryStage>("idle");
  const [summaryError, setSummaryError] = useState("");
  const [summary, setSummary] = useState("");

  const [askInput, setAskInput] = useState("");
  const [askStage, setAskStage] = useState<AskStage>("idle");
  const [askError, setAskError] = useState("");
  const [messages, setMessages] = useState<QAMessage[]>([]);

  /** Per-paper conversation/summary cache. Keyed by paper_id. */
  const paperCache = useRef<Map<string, PaperState>>(new Map());

  const endRef = useRef<HTMLDivElement>(null);

  async function handleSearch() {
    const q = query.trim();
    if (!q) return;
    setSearchStage("searching");
    setSearchError("");
    setPapers([]);
    // Save current paper state before clearing it
    _saveCurrentPaperState();
    setSelectedPaper(null);
    setSummary("");
    setSummaryStage("idle");
    setSummaryError("");
    setMessages([]);
    setAskInput("");
    setAskError("");

    try {
      const result = await searchPapers(q, 10);
      setPapers(result.papers);
      setSearchedQuery(result.query);
    } catch (err) {
      setSearchError(friendlyError(err, "Search failed. Please try again."));
    } finally {
      setSearchStage("idle");
    }
  }

  /** Persist the active paper's UI state into the cache. */
  function _saveCurrentPaperState() {
    if (!selectedPaper) return;
    paperCache.current.set(selectedPaper.paper_id, {
      messages,
      summary,
      summaryStage,
      summaryError,
    });
  }

  function handleSelectPaper(paper: PaperItem) {
    // Persist current paper before switching
    _saveCurrentPaperState();

    setSelectedPaper(paper);
    setAskInput("");
    setAskError("");

    // Restore cached state for the newly selected paper, or use fresh defaults
    const cached = paperCache.current.get(paper.paper_id);
    if (cached) {
      setMessages(cached.messages);
      setSummary(cached.summary);
      setSummaryStage(cached.summaryStage);
      setSummaryError(cached.summaryError);
    } else {
      setMessages([]);
      setSummary("");
      setSummaryStage("idle");
      setSummaryError("");
    }
  }

  async function handleSummarize() {
    if (!selectedPaper) return;
    setSummaryStage("loading");
    setSummaryError("");
    setSummary("");

    try {
      const result = await summarizePaper(selectedPaper);
      setSummary(result.summary);
      setSummaryStage("done");
      // Persist the generated summary for this paper
      paperCache.current.set(selectedPaper.paper_id, {
        messages,
        summary: result.summary,
        summaryStage: "done",
        summaryError: "",
      });
    } catch (err) {
      const errMsg = friendlyError(err, "Summary generation failed.");
      setSummaryError(errMsg);
      setSummaryStage("idle");
      paperCache.current.set(selectedPaper.paper_id, {
        messages,
        summary: "",
        summaryStage: "idle",
        summaryError: errMsg,
      });
    }
  }

  async function handleAsk() {
    if (!selectedPaper || !askInput.trim() || askStage !== "idle") return;
    const question = askInput.trim();
    setAskInput("");
    setAskError("");

    const userMsg: QAMessage = { id: Date.now(), role: "user", text: question };
    setMessages((prev) => [...prev, userMsg]);
    setAskStage("loading");

    try {
      const result = await askPaper(selectedPaper, question);
      const assistantMsg: QAMessage = {
        id: Date.now() + 1,
        role: "assistant",
        text: result.answer,
      };
      setMessages((prev) => {
        const next = [...prev, assistantMsg];
        // Keep cache in sync so switching away preserves the full conversation
        paperCache.current.set(selectedPaper.paper_id, {
          messages: next,
          summary,
          summaryStage,
          summaryError,
        });
        return next;
      });
    } catch (err) {
      setAskError(friendlyError(err, "Failed to get an answer."));
    } finally {
      setAskStage("idle");
      setTimeout(() => {
        endRef.current?.scrollIntoView?.({ behavior: "smooth" });
      }, 50);
    }
  }

  const searching = searchStage === "searching";

  return (
    <div className="space-y-4 sm:space-y-5">
      {/* Search box */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <label
          htmlFor="academic-query"
          className="mb-2 block text-sm font-medium text-slate-700"
        >
          Search academic papers
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            id="academic-query"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void handleSearch();
              }
            }}
            disabled={searching}
            placeholder="e.g. transformer attention mechanism"
            aria-label="Search query"
            className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100 disabled:bg-slate-50"
          />
          <button
            type="button"
            onClick={() => void handleSearch()}
            disabled={searching || !query.trim()}
            className="rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-orange-600 disabled:opacity-50"
          >
            {searching ? "Searching…" : "Search"}
          </button>
        </div>

        {searchError && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            {searchError}
          </p>
        )}
      </div>

      {/* Results list */}
      {papers.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">
            Results for "{searchedQuery}"
            <span className="ml-2 font-normal text-slate-400">
              {papers.length} paper{papers.length !== 1 ? "s" : ""}
            </span>
          </h2>
          <ul className="space-y-3">
            {papers.map((paper) => {
              const isSelected = selectedPaper?.paper_id === paper.paper_id;
              return (
                <li key={paper.paper_id}>
                  <button
                    type="button"
                    onClick={() => handleSelectPaper(paper)}
                    className={
                      "w-full rounded-lg border p-4 text-left transition-colors " +
                      (isSelected
                        ? "border-orange-400 bg-orange-50"
                        : "border-slate-200 hover:border-orange-300 hover:bg-slate-50")
                    }
                  >
                    <p className="text-sm font-medium text-slate-800 leading-snug">
                      {paper.title}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {paper.authors.slice(0, 3).join(", ")}
                      {paper.authors.length > 3 ? " et al." : ""}
                      {paper.year ? ` · ${paper.year}` : ""}
                    </p>
                    {paper.abstract && (
                      <p className="mt-2 line-clamp-2 text-xs text-slate-600 leading-relaxed">
                        {paper.abstract}
                      </p>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Paper detail panel */}
      {selectedPaper && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          {/* Header */}
          <div className="mb-4">
            <h2 className="text-base font-semibold text-slate-800 leading-snug">
              {selectedPaper.title}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              {selectedPaper.authors.join(", ")}
              {selectedPaper.year ? ` · ${selectedPaper.year}` : ""}
            </p>
            {selectedPaper.pdf_url && (
              <a
                href={selectedPaper.pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-block text-xs font-medium text-orange-500 underline underline-offset-2 hover:text-orange-600"
              >
                View PDF ↗
              </a>
            )}
          </div>

          {/* Abstract */}
          {selectedPaper.abstract && (
            <div className="mb-4 rounded-lg bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Abstract
              </p>
              <p className="mt-2 text-sm text-slate-700 leading-relaxed">
                {selectedPaper.abstract}
              </p>
            </div>
          )}

          {/* Summarize button */}
          {summaryStage === "idle" && (
            <button
              type="button"
              onClick={() => void handleSummarize()}
              className="rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-orange-600"
            >
              Generate AI Summary
            </button>
          )}

          {summaryStage === "loading" && (
            <p className="text-sm text-slate-500" role="status">
              Generating summary…
            </p>
          )}

          {summaryError && (
            <p className="text-sm text-red-600" role="alert">
              {summaryError}
            </p>
          )}

          {/* Summary output */}
          {summaryStage === "done" && summary && (
            <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                AI Summary
              </p>
              <pre className="whitespace-pre-wrap text-sm text-slate-700 leading-relaxed font-sans">
                {summary}
              </pre>
            </div>
          )}

          {/* Q&A section */}
          <div className="mt-6">
            <h3 className="mb-3 text-sm font-semibold text-slate-700">
              Ask a question about this paper
            </h3>

            {/* Conversation */}
            {messages.length > 0 && (
              <div
                className="mb-4 max-h-64 space-y-3 overflow-y-auto pr-1"
                role="log"
                aria-live="polite"
                aria-label="Paper Q&A conversation"
              >
                {messages.map((message) => {
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
                })}

                {askStage === "loading" && (
                  <div
                    className="mr-auto max-w-[85%] rounded-2xl bg-slate-100 px-4 py-2 text-sm text-slate-500"
                    role="status"
                  >
                    <span className="inline-flex items-center gap-2">
                      <span className="h-2 w-2 animate-pulse rounded-full bg-orange-400" />
                      Generating answer…
                    </span>
                  </div>
                )}

                <div ref={endRef} />
              </div>
            )}

            {askError && (
              <p className="mb-2 text-sm text-red-600" role="alert">
                {askError}
              </p>
            )}

            <div className="flex items-end gap-2">
              <textarea
                value={askInput}
                onChange={(e) => setAskInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void handleAsk();
                  }
                }}
                disabled={askStage === "loading"}
                rows={1}
                placeholder="Ask something about this paper…  (Enter to send)"
                aria-label="Ask a question about this paper"
                className="max-h-32 min-h-[2.75rem] flex-1 resize-y rounded-lg border border-slate-300 px-4 py-2.5 text-sm leading-relaxed outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100 disabled:bg-slate-50"
              />
              <button
                type="button"
                onClick={() => void handleAsk()}
                disabled={askStage === "loading" || !askInput.trim()}
                className="rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-orange-600 disabled:opacity-50"
              >
                {askStage === "loading" ? "…" : "Ask"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
