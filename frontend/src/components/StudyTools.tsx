import { useEffect, useState } from "react";

import { ApiError } from "../api/client";
import {
  deleteNotes,
  deleteQuiz,
  generateNotes,
  generateQuiz,
  getNotes,
  getQuiz,
  getStudyHistory,
  listSources,
  type StudyHistoryItem,
  type Difficulty,
  type NoteType,
  type NotesResult,
  type QuestionCount,
  type QuestionType,
  type QuizResult,
  type SourceItem,
  type SourceType,
} from "../api/studyTools";
import type { ReactNode } from "react";

import { timeAgo } from "../lib/time";
import HistoryList from "./HistoryList";
import { IconCheck } from "./icons";
import { EmptyNote, ErrorNotice, ProgressNotice } from "./ui";
import { AsideCard, Workspace } from "./workspace";
import Markdown from "./Markdown";
import Segmented from "./Segmented";

type Tab = "quiz" | "notes";

const QUESTION_TYPES: { value: QuestionType; label: string }[] = [
  { value: "mcq", label: "Multiple Choice" },
  { value: "true_false", label: "True / False" },
  { value: "short_answer", label: "Short Answer" },
];

const DIFFICULTIES: Difficulty[] = ["easy", "medium", "hard"];
const COUNTS: QuestionCount[] = [5, 10, 20];

const NOTE_TYPES: { value: NoteType; label: string }[] = [
  { value: "chapter_summary", label: "Chapter Summary" },
  { value: "key_points", label: "Key Points" },
  { value: "important_concepts", label: "Important Concepts" },
  { value: "formula_sheet", label: "Formula Sheet" },
  { value: "revision_notes", label: "Revision Notes" },
];

/** Turn an API failure into a friendly, user-facing message. */
function friendlyError(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.status === 0) {
      return "Network error. Please check your connection and try again.";
    }
    if (err.status === 404) {
      return "That source could not be found. Please pick another.";
    }
    if (err.status === 422) {
      return "This source isn't ready yet, or there wasn't enough content. Try another.";
    }
    return err.message || fallback;
  }
  return "Network error. Please check your connection and try again.";
}

/** AI Study Tools: generate quizzes and notes from a processed source. */
export default function StudyTools({ active = true }: { active?: boolean }) {
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourcesError, setSourcesError] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("pdf");
  const [sourceId, setSourceId] = useState("");
  const [tab, setTab] = useState<Tab>("quiz");
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null);
  const [notesResult, setNotesResult] = useState<NotesResult | null>(null);
  const [history, setHistory] = useState<StudyHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState("");

  function refreshHistory() {
    return getStudyHistory()
      .then((items) => {
        setHistory(items);
        setHistoryError("");
      })
      .catch((err) => setHistoryError(friendlyError(err, "Could not load saved items.")))
      .finally(() => setHistoryLoading(false));
  }

  useEffect(() => {
    if (active) void refreshHistory();
  }, [active]);

  async function openSaved(id: string) {
    const item = history.find((entry) => entry.id === id);
    if (!item) return;
    try {
      if (item.kind === "quiz") {
        setQuizResult(await getQuiz(id));
        setTab("quiz");
      } else {
        setNotesResult(await getNotes(id));
        setTab("notes");
      }
    } catch (err) {
      setHistoryError(friendlyError(err, "Could not open that item."));
    }
  }

  async function removeSaved(id: string) {
    const item = history.find((entry) => entry.id === id);
    if (!item) return;
    try {
      await (item.kind === "quiz" ? deleteQuiz(id) : deleteNotes(id));
      setHistory((prev) => prev.filter((entry) => entry.id !== id));
      if (quizResult?.id === id) setQuizResult(null);
      if (notesResult?.id === id) setNotesResult(null);
    } catch (err) {
      setHistoryError(friendlyError(err, "Could not delete that item."));
    }
  }

  const openedId = tab === "quiz" ? quizResult?.id : notesResult?.id;
  const savedList = (
    <>
      <HistoryList
        title="Saved quizzes & notes"
        loading={historyLoading}
        items={history.map((entry) => ({
          id: entry.id,
          title: `${entry.kind === "quiz" ? "Quiz" : "Notes"}: ${entry.source_title || "Untitled source"}`,
          subtitle: entry.label,
          meta: timeAgo(entry.created_at),
        }))}
        selectedId={openedId ?? null}
        emptyText="Quizzes and notes you generate are saved here."
        onSelect={(id) => void openSaved(id)}
        onDelete={(id) => void removeSaved(id)}
      />
      {historyError && <ErrorNotice>{historyError}</ErrorNotice>}
    </>
  );

  // Reload whenever the tab is opened, so PDFs and videos processed in the
  // other modules show up without a page refresh.
  useEffect(() => {
    if (!active) return;
    let live = true;
    listSources()
      .then((items) => {
        if (live) {
          setSources(items);
          setSourcesError("");
        }
      })
      .catch((err) => {
        if (live) setSourcesError(friendlyError(err, "Could not load sources."));
      })
      .finally(() => {
        if (live) setSourcesLoading(false);
      });
    return () => {
      live = false;
    };
  }, [active]);

  const filteredSources = sources.filter((source) => source.type === sourceType);

  // Keep the selected source valid for the chosen source type.
  useEffect(() => {
    if (filteredSources.length === 0) {
      setSourceId("");
    } else if (!filteredSources.some((source) => source.id === sourceId)) {
      setSourceId(filteredSources[0].id);
    }
  }, [sourceType, sources]); // eslint-disable-line react-hooks/exhaustive-deps

  const controls = (
    <>
      <AsideCard title="Source">
        <div className="segmented grid-cols-2">
          {(["pdf", "youtube"] as SourceType[]).map((type) => (
            <label
              key={type}
              className={
                "segment cursor-pointer has-[:focus-visible]:shadow-focus " +
                (sourceType === type ? "segment-on" : "segment-off")
              }
            >
              <input
                type="radio"
                name="source-type"
                value={type}
                checked={sourceType === type}
                onChange={() => setSourceType(type)}
                className="sr-only"
              />
              {type === "pdf" ? "Uploaded PDF" : "YouTube video"}
            </label>
          ))}
        </div>

        <div className="mt-3">
          {sourcesLoading ? (
            <div className="skeleton h-10" role="status" aria-label="Loading your sources" />
          ) : sourcesError ? (
            <ErrorNotice>{sourcesError}</ErrorNotice>
          ) : filteredSources.length === 0 ? (
            <p className="rounded-control border border-dashed border-line-strong px-3 py-3 text-sm leading-5 text-muted">
              {sourceType === "pdf"
                ? "No processed PDFs yet. Upload one in Learn from PDF first."
                : "No processed videos yet. Process one in Learn from YouTube first."}
            </p>
          ) : (
            <select
              value={sourceId}
              onChange={(event) => setSourceId(event.target.value)}
              aria-label="Select a processed source"
              className="field"
            >
              {filteredSources.map((source) => (
                <option key={source.id} value={source.id}>
                  {source.title}
                </option>
              ))}
            </select>
          )}
        </div>
      </AsideCard>

      <Segmented
        label="Tool"
        options={[
          { value: "quiz", label: "Quiz" },
          { value: "notes", label: "Notes" },
        ]}
        value={tab}
        onChange={setTab}
        className="grid grid-cols-2"
      />
    </>
  );

  return tab === "quiz" ? (
    <QuizPanel
      sourceId={sourceId}
      sourceType={sourceType}
      controls={controls}
      history={savedList}
      result={quizResult}
      setResult={setQuizResult}
      onSaved={() => void refreshHistory()}
    />
  ) : (
    <NotesPanel
      sourceId={sourceId}
      sourceType={sourceType}
      controls={controls}
      history={savedList}
      result={notesResult}
      setResult={setNotesResult}
      onSaved={() => void refreshHistory()}
    />
  );
}

/** Placeholder lines shown in the results pane while the model works. */
function ResultSkeleton({ label }: { label: string }) {
  return (
    <div className="space-y-6">
      <ProgressNotice>{label}</ProgressNotice>
      {[0, 1, 2].map((row) => (
        <div key={row} className="space-y-2" aria-hidden="true">
          <div className="skeleton h-4 w-3/4" />
          <div className="skeleton h-9 w-full" />
          <div className="skeleton h-9 w-full" />
        </div>
      ))}
    </div>
  );
}

/** Quiz generation form and results. */
function QuizPanel({
  sourceId,
  sourceType,
  controls,
  history,
  result,
  setResult,
  onSaved,
}: {
  sourceId: string;
  sourceType: SourceType;
  controls: ReactNode;
  history: ReactNode;
  result: QuizResult | null;
  setResult: (result: QuizResult | null) => void;
  onSaved: () => void;
}) {
  const [questionType, setQuestionType] = useState<QuestionType>("mcq");
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [count, setCount] = useState<QuestionCount>(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleGenerate() {
    if (!sourceId) {
      setError("Please select a source first.");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const quiz = await generateQuiz({
        sourceId,
        sourceType,
        questionType,
        difficulty,
        count,
      });
      setResult(quiz);
      onSaved();
    } catch (err) {
      setError(friendlyError(err, "Could not generate the quiz."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Workspace
      aside={
        <>
          {controls}
          <AsideCard title="Quiz settings">
            <div className="space-y-3">
              <label className="block">
                <span className="field-label">Type</span>
                <select
                  value={questionType}
                  onChange={(event) => setQuestionType(event.target.value as QuestionType)}
                  className="field"
                >
                  {QUESTION_TYPES.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="field-label">Difficulty</span>
                  <select
                    value={difficulty}
                    onChange={(event) => setDifficulty(event.target.value as Difficulty)}
                    className="field capitalize"
                  >
                    {DIFFICULTIES.map((option) => (
                      <option key={option} value={option} className="capitalize">
                        {option}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="field-label">Questions</span>
                  <select
                    value={count}
                    onChange={(event) => setCount(Number(event.target.value) as QuestionCount)}
                    className="field"
                  >
                    {COUNTS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>

            <button
              type="button"
              onClick={() => void handleGenerate()}
              disabled={loading || !sourceId}
              className="btn-primary mt-4 w-full"
            >
              {loading && <span className="spinner" aria-hidden="true" />}
              {loading ? "Generating…" : "Generate quiz"}
            </button>
            {error && <ErrorNotice className="mt-3">{error}</ErrorNotice>}
          </AsideCard>
          {history}
        </>
      }
    >
      <div className="pane">
        <div className="pane-head">
          <div className="min-w-0">
            <h2 className="section-title">Quiz</h2>
            {result?.source_title && (
              <p className="truncate text-xs text-muted">
                From {result.source_title}
                {result.created_at ? `, ${timeAgo(result.created_at)}` : ""}
              </p>
            )}
          </div>
          {result && result.questions.length > 0 && (
            <span className="text-xs tabular-nums text-muted">
              {result.questions.length} questions
            </span>
          )}
        </div>
        <div className="pane-scroll">
          <div className="mx-auto w-full max-w-reading px-4 py-6 sm:px-6">
            {loading ? (
              <ResultSkeleton label="Writing your quiz…" />
            ) : result && result.questions.length > 0 ? (
              <ol className="divide-y divide-line">
                {result.questions.map((question, index) => (
                  <li key={index} className="flex gap-3 py-6 first:pt-0 last:pb-0 sm:gap-4">
                    <span className="w-6 shrink-0 pt-px text-right text-sm font-medium tabular-nums text-faint">
                      {index + 1}.
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="break-words text-[15px] font-medium leading-6 text-ink">
                        {question.question}
                      </p>
                      {question.options.length > 0 && (
                        <ul className="mt-3 space-y-2">
                          {question.options.map((option, optionIndex) => (
                            <li
                              key={optionIndex}
                              className="flex gap-2 rounded-control border border-line px-3 py-2 text-sm leading-6 text-ink-soft"
                            >
                              <span className="shrink-0 font-medium text-muted">
                                {String.fromCharCode(65 + optionIndex)}.
                              </span>
                              <span className="min-w-0 break-words">{option}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                      <p className="mt-3 inline-flex items-start gap-2 text-sm font-medium text-success">
                        <IconCheck className="mt-1 h-4 w-4 shrink-0" />
                        <span className="break-words">Answer: {question.correct_answer}</span>
                      </p>
                      {question.explanation && (
                        <p className="mt-1 max-w-prose text-sm leading-6 text-muted">
                          {question.explanation}
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <EmptyNote>
                Pick a source and settings, then select Generate quiz. Questions appear here.
              </EmptyNote>
            )}
          </div>
        </div>
      </div>
    </Workspace>
  );
}

/** Notes generation form and results with copy / download. */
function NotesPanel({
  sourceId,
  sourceType,
  controls,
  history,
  result,
  setResult,
  onSaved,
}: {
  sourceId: string;
  sourceType: SourceType;
  controls: ReactNode;
  history: ReactNode;
  result: NotesResult | null;
  setResult: (result: NotesResult | null) => void;
  onSaved: () => void;
}) {
  const [noteType, setNoteType] = useState<NoteType>("chapter_summary");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  async function handleGenerate() {
    if (!sourceId) {
      setError("Please select a source first.");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    setCopied(false);
    try {
      const notes = await generateNotes({ sourceId, sourceType, noteType });
      setResult(notes);
      onSaved();
    } catch (err) {
      setError(friendlyError(err, "Could not generate the notes."));
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Could not copy to the clipboard.");
    }
  }

  function handleDownload() {
    if (!result) return;
    const blob = new Blob([result.content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${result.note_type}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Workspace
      aside={
        <>
          {controls}
          <AsideCard title="Notes settings">
            <label className="block">
              <span className="field-label">Notes type</span>
              <select
                value={noteType}
                onChange={(event) => setNoteType(event.target.value as NoteType)}
                className="field"
              >
                {NOTE_TYPES.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={() => void handleGenerate()}
              disabled={loading || !sourceId}
              className="btn-primary mt-4 w-full"
            >
              {loading && <span className="spinner" aria-hidden="true" />}
              {loading ? "Generating…" : "Generate notes"}
            </button>
            {error && <ErrorNotice className="mt-3">{error}</ErrorNotice>}
          </AsideCard>
          {history}
        </>
      }
    >
      <div className="pane">
        <div className="pane-head">
          <div className="min-w-0">
            <h2 className="section-title">Notes</h2>
            {result?.source_title && (
              <p className="truncate text-xs text-muted">
                From {result.source_title}
                {result.created_at ? `, ${timeAgo(result.created_at)}` : ""}
              </p>
            )}
          </div>
          {result && (
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => void handleCopy()} className="btn-quiet">
                {copied && <IconCheck className="h-4 w-4 text-success" />}
                {copied ? "Copied!" : "Copy notes"}
              </button>
              <button type="button" onClick={handleDownload} className="btn-quiet">
                Download .md
              </button>
            </div>
          )}
        </div>
        <div className="pane-scroll">
          <div className="mx-auto w-full max-w-reading px-4 py-6 sm:px-6">
            {loading ? (
              <ResultSkeleton label="Writing your notes…" />
            ) : result ? (
              <Markdown size="doc">{result.content}</Markdown>
            ) : (
              <EmptyNote>
                Pick a source and a notes type, then select Generate notes. Your notes appear
                here, ready to copy or download.
              </EmptyNote>
            )}
          </div>
        </div>
      </div>
    </Workspace>
  );
}
