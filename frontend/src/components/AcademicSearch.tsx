import { useEffect, useRef, useState } from "react";

import { ApiError } from "../api/client";
import { useChatScroll } from "../hooks/useChatScroll";
import {
  askPaper,
  deleteSavedPaper,
  deleteSearch,
  getSavedPaper,
  getSearch,
  listSavedPapers,
  listSearches,
  searchPapers,
  summarizePaper,
  type PaperItem,
  type SavedPaperItem,
  type SearchHistoryItem,
} from "../api/academic";
import { timeAgo } from "../lib/time";
import HistoryList from "./HistoryList";
import { IconSearch } from "./icons";
import { EmptyNote, ErrorNotice, ProgressNotice, TypingIndicator } from "./ui";
import { AsideCard, Workspace } from "./workspace";
import Markdown from "./Markdown";

type SearchStage = "idle" | "searching";
type SummaryStage = "idle" | "loading" | "done";
type AskStage = "idle" | "loading";

interface QAMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
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

/**
 * AI Academic Search: search papers, read summaries, ask questions.
 * Searches, summaries and Q&A are saved on the server and listed on the left.
 */
export default function AcademicSearch() {
  const [query, setQuery] = useState("");
  const [searchStage, setSearchStage] = useState<SearchStage>("idle");
  const [searchError, setSearchError] = useState("");
  const [papers, setPapers] = useState<PaperItem[]>([]);
  const [searchedQuery, setSearchedQuery] = useState("");
  const [activeSearchId, setActiveSearchId] = useState<string | null>(null);

  const [searches, setSearches] = useState<SearchHistoryItem[]>([]);
  const [savedPapers, setSavedPapers] = useState<SavedPaperItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  const [selectedPaper, setSelectedPaper] = useState<PaperItem | null>(null);
  const [paperLoading, setPaperLoading] = useState(false);
  const [summaryStage, setSummaryStage] = useState<SummaryStage>("idle");
  const [summaryError, setSummaryError] = useState("");
  const [summary, setSummary] = useState("");

  const [askInput, setAskInput] = useState("");
  const [askStage, setAskStage] = useState<AskStage>("idle");
  const [askError, setAskError] = useState("");
  const [messages, setMessages] = useState<QAMessage[]>([]);

  /** The paper most recently opened; late responses for others are ignored. */
  const openingRef = useRef<string | null>(null);
  /** Scrolls to the bottom of the Q&A chat when messages or loading state changes. */
  const endRef = useChatScroll([messages, askStage]);
  /** Used to scroll the detail panel into view when a paper is selected. */
  const detailRef = useRef<HTMLDivElement>(null);
  /** Focused when a paper is selected so the user can type immediately. */
  const askInputRef = useRef<HTMLTextAreaElement>(null);

  function refreshSavedPapers() {
    listSavedPapers()
      .then(setSavedPapers)
      .catch(() => undefined);
  }

  useEffect(() => {
    let live = true;
    Promise.all([listSearches(), listSavedPapers()])
      .then(([searchItems, paperItems]) => {
        if (!live) return;
        setSearches(searchItems);
        setSavedPapers(paperItems);
      })
      .catch(() => undefined)
      .finally(() => {
        if (live) setHistoryLoading(false);
      });
    return () => {
      live = false;
    };
  }, []);

  function clearSelection() {
    openingRef.current = null;
    setSelectedPaper(null);
    setSummary("");
    setSummaryStage("idle");
    setSummaryError("");
    setMessages([]);
    setAskInput("");
    setAskError("");
  }

  async function handleSearch() {
    const q = query.trim();
    if (!q) return;
    setSearchStage("searching");
    setSearchError("");
    setPapers([]);
    clearSelection();

    try {
      const result = await searchPapers(q, 10);
      setPapers(result.papers);
      setSearchedQuery(result.query);
      setActiveSearchId(result.search_id ?? null);
      if (result.search_id) {
        const entry: SearchHistoryItem = {
          id: result.search_id,
          query: result.query,
          result_count: result.papers.length,
          created_at: result.created_at ?? new Date().toISOString(),
        };
        setSearches((prev) => [entry, ...prev]);
      }
    } catch (err) {
      setSearchError(friendlyError(err, "Search failed. Please try again."));
    } finally {
      setSearchStage("idle");
    }
  }

  /** Reopen a past search with its saved results (no new lookup). */
  async function openSearch(id: string) {
    setSearchError("");
    clearSelection();
    try {
      const result = await getSearch(id);
      setPapers(result.papers);
      setSearchedQuery(result.query);
      setQuery(result.query);
      setActiveSearchId(id);
    } catch (err) {
      setSearchError(friendlyError(err, "Could not open that search."));
    }
  }

  async function removeSearch(id: string) {
    try {
      await deleteSearch(id);
      setSearches((prev) => prev.filter((item) => item.id !== id));
      if (activeSearchId === id) setActiveSearchId(null);
    } catch (err) {
      setSearchError(friendlyError(err, "Could not delete that search."));
    }
  }

  async function removeSavedPaper(paperId: string) {
    try {
      await deleteSavedPaper(paperId);
      setSavedPapers((prev) => prev.filter((item) => item.paper.paper_id !== paperId));
      if (selectedPaper?.paper_id === paperId) clearSelection();
    } catch (err) {
      setSearchError(friendlyError(err, "Could not remove that paper."));
    }
  }

  async function handleSelectPaper(paper: PaperItem) {
    clearSelection();
    openingRef.current = paper.paper_id;
    setSelectedPaper(paper);
    setPaperLoading(true);

    // On phones the detail pane sits below the results, so bring it into
    // view. On desktop it is already beside them; scrolling would shift the
    // fixed layout.
    setTimeout(() => {
      const stacked = window.matchMedia?.("(max-width: 1023px)").matches ?? false;
      if (stacked) {
        detailRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
      }
      askInputRef.current?.focus({ preventScroll: true });
    }, 50);

    // Restore anything saved about this paper (summary, Q&A).
    try {
      const saved = await getSavedPaper(paper.paper_id);
      if (openingRef.current !== paper.paper_id) return;
      if (saved.summary) {
        setSummary(saved.summary);
        setSummaryStage("done");
      }
      setMessages(saved.messages.map((m) => ({ id: m.id, role: m.role, text: m.text })));
    } catch (err) {
      // 404 just means this paper has nothing saved yet.
      if (!(err instanceof ApiError && err.status === 404) && openingRef.current === paper.paper_id) {
        setAskError(friendlyError(err, "Could not load what you saved for this paper."));
      }
    } finally {
      if (openingRef.current === paper.paper_id) setPaperLoading(false);
    }
  }

  async function handleSummarize() {
    if (!selectedPaper) return;
    const paperId = selectedPaper.paper_id;
    setSummaryStage("loading");
    setSummaryError("");
    setSummary("");

    try {
      const result = await summarizePaper(selectedPaper);
      if (openingRef.current !== paperId) return;
      setSummary(result.summary);
      setSummaryStage("done");
      refreshSavedPapers();
    } catch (err) {
      if (openingRef.current !== paperId) return;
      setSummaryError(friendlyError(err, "Summary generation failed."));
      setSummaryStage("idle");
    }
  }

  async function handleAsk() {
    if (!selectedPaper || !askInput.trim() || askStage !== "idle") return;
    const paperId = selectedPaper.paper_id;
    const question = askInput.trim();
    setAskInput("");
    setAskError("");
    setMessages((prev) => [...prev, { id: `local-${Date.now()}`, role: "user", text: question }]);
    setAskStage("loading");

    try {
      const result = await askPaper(selectedPaper, question);
      if (openingRef.current !== paperId) return;
      setMessages((prev) => [
        ...prev,
        { id: `local-${Date.now()}-a`, role: "assistant", text: result.answer },
      ]);
      refreshSavedPapers();
    } catch (err) {
      if (openingRef.current === paperId) {
        setAskError(friendlyError(err, "Failed to get an answer."));
      }
    } finally {
      setAskStage("idle");
    }
  }

  const searching = searchStage === "searching";

  return (
    <Workspace
      aside={
        <>
          <AsideCard>
            <label htmlFor="academic-query" className="field-label">
              Search academic papers
            </label>
            <div className="relative">
              <IconSearch className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
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
                className="field pl-9"
              />
            </div>
            <button
              type="button"
              onClick={() => void handleSearch()}
              disabled={searching || !query.trim()}
              className="btn-primary mt-3 w-full"
            >
              {searching && <span className="spinner" aria-hidden="true" />}
              {searching ? "Searching…" : "Search"}
            </button>
            {searchError && <ErrorNotice className="mt-3">{searchError}</ErrorNotice>}
          </AsideCard>

          {searching && (
            <div className="card space-y-4 p-4" aria-hidden="true">
              {[0, 1, 2].map((row) => (
                <div key={row} className="space-y-2">
                  <div className="skeleton h-4 w-5/6" />
                  <div className="skeleton h-3 w-1/2" />
                </div>
              ))}
            </div>
          )}

          {papers.length > 0 && (
            // Fills the space under the search box; only the list scrolls.
            <div className="card flex flex-col overflow-hidden lg:min-h-48 lg:flex-1 lg:!shrink">
              <h2 className="flex shrink-0 items-baseline justify-between gap-3 border-b border-line px-4 py-3 text-sm font-semibold text-ink">
                <span className="min-w-0 truncate">Results for "{searchedQuery}"</span>
                <span className="shrink-0 text-xs font-normal text-muted">
                  {papers.length} paper{papers.length !== 1 ? "s" : ""}
                </span>
              </h2>
              <ul className="space-y-1 overscroll-contain p-2 lg:min-h-0 lg:flex-1 lg:overflow-y-auto">
                {papers.map((paper) => {
                  const isSelected = selectedPaper?.paper_id === paper.paper_id;
                  return (
                    <li key={paper.paper_id}>
                      <button
                        type="button"
                        onClick={() => handleSelectPaper(paper)}
                        aria-pressed={isSelected}
                        className={
                          "w-full rounded-panel px-3 py-3 text-left transition-[background-color,box-shadow] duration-150 " +
                          (isSelected
                            ? "bg-gradient-to-br from-accent-soft to-accent-tint/60 ring-1 ring-inset ring-accent-line"
                            : "hover:bg-sunken/70")
                        }
                      >
                        <p
                          className={
                            "line-clamp-2 text-sm font-medium leading-5 " +
                            (isSelected ? "text-accent-ink" : "text-ink")
                          }
                        >
                          {paper.title}
                        </p>
                        <p className="mt-1 truncate text-xs text-muted">
                          {paper.authors.slice(0, 3).join(", ")}
                          {paper.authors.length > 3 ? " et al." : ""}
                          {paper.year ? `, ${paper.year}` : ""}
                        </p>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          <HistoryList
            title="Recent searches"
            loading={historyLoading}
            items={searches.map((item) => ({
              id: item.id,
              title: item.query,
              subtitle: `${item.result_count} paper${item.result_count === 1 ? "" : "s"}`,
              meta: timeAgo(item.created_at),
            }))}
            selectedId={activeSearchId}
            emptyText="Your searches are saved here."
            onSelect={(id) => void openSearch(id)}
            onDelete={(id) => void removeSearch(id)}
          />

          <HistoryList
            title="Saved papers"
            loading={historyLoading}
            items={savedPapers.map((item) => ({
              id: item.paper.paper_id,
              title: item.paper.title,
              subtitle: [
                item.has_summary ? "Summary" : "",
                item.message_count > 0 ? `${item.message_count} messages` : "",
              ]
                .filter(Boolean)
                .join(", "),
              meta: timeAgo(item.updated_at),
            }))}
            selectedId={selectedPaper?.paper_id ?? null}
            emptyText="Papers you summarise or ask about are saved here."
            onSelect={(id) => {
              const item = savedPapers.find((entry) => entry.paper.paper_id === id);
              if (item) void handleSelectPaper(item.paper);
            }}
            onDelete={(id) => void removeSavedPaper(id)}
          />
        </>
      }
    >
      <div ref={detailRef} className="pane scroll-mt-4">
        {!selectedPaper ? (
          <div className="pane-scroll flex">
            <EmptyNote>
              Search for a topic, then pick a paper to read its abstract, get an AI summary
              and ask questions about it.
            </EmptyNote>
          </div>
        ) : (
          <>
            <div className="pane-scroll">
              <div className="mx-auto w-full max-w-reading px-4 py-6 sm:px-6">
                <h2 className="text-lg font-semibold leading-7 tracking-[-0.015em] text-ink">
                  {selectedPaper.title}
                </h2>
                <p className="mt-1 text-sm text-muted">
                  {selectedPaper.authors.join(", ")}
                  {selectedPaper.year ? `, ${selectedPaper.year}` : ""}
                </p>
                {selectedPaper.pdf_url && (
                  <a
                    href={selectedPaper.pdf_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="link mt-2 inline-block text-sm"
                  >
                    View PDF
                  </a>
                )}

                {selectedPaper.abstract && (
                  <div className="mt-6 rounded-panel bg-canvas p-4">
                    <p className="text-[13px] font-medium text-muted">Abstract</p>
                    <p className="mt-2 text-sm leading-6 text-ink-soft">
                      {selectedPaper.abstract}
                    </p>
                  </div>
                )}

                <div className="mt-4 space-y-3">
                  {paperLoading && <ProgressNotice>Loading what you saved…</ProgressNotice>}
                  {!paperLoading && summaryStage === "idle" && (
                    <button
                      type="button"
                      onClick={() => void handleSummarize()}
                      className="btn-secondary"
                    >
                      Generate AI Summary
                    </button>
                  )}
                  {summaryStage === "loading" && (
                    <ProgressNotice>Generating summary…</ProgressNotice>
                  )}
                  {summaryError && <ErrorNotice>{summaryError}</ErrorNotice>}
                  {summaryStage === "done" && summary && (
                    <div className="rounded-panel border border-accent-line bg-accent-soft p-4">
                      <p className="text-[13px] font-medium text-accent-ink">AI Summary</p>
                      <div className="mt-2">
                        <Markdown>{summary}</Markdown>
                      </div>
                    </div>
                  )}
                </div>

                <div className="mt-8 border-t border-line pt-6">
                  <h3 className="text-sm font-semibold text-ink">
                    Ask a question about this paper
                  </h3>
                  <div
                    className="mt-4 flex flex-col gap-4"
                    role="log"
                    aria-live="polite"
                    aria-label="Paper Q&A conversation"
                  >
                    {messages.length === 0 && askStage !== "loading" && (
                      <p className="text-sm text-muted">
                        Questions and answers about this paper appear here.
                      </p>
                    )}
                    {messages.map((message) => {
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
                    })}
                    {askStage === "loading" && (
                      <TypingIndicator>Generating answer…</TypingIndicator>
                    )}
                    <div ref={endRef} />
                  </div>
                </div>
              </div>
            </div>

            <div className="pane-foot">
              <div className="mx-auto w-full max-w-reading">
                {askError && <ErrorNotice className="mb-3">{askError}</ErrorNotice>}
                <div className="composer">
                  <textarea
                    ref={askInputRef}
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
                    placeholder="Ask something about this paper…"
                    aria-label="Ask a question about this paper"
                    className="composer-input"
                  />
                  <button
                    type="button"
                    onClick={() => void handleAsk()}
                    disabled={askStage === "loading" || !askInput.trim()}
                    className="composer-send"
                  >
                    {askStage === "loading" && <span className="spinner" aria-hidden="true" />}
                    Ask
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </Workspace>
  );
}
