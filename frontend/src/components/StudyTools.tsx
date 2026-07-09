import { useEffect, useState } from "react";

import { ApiError } from "../api/client";
import {
  generateNotes,
  generateQuiz,
  listSources,
  type Difficulty,
  type NoteType,
  type NotesResult,
  type QuestionCount,
  type QuestionType,
  type QuizResult,
  type SourceItem,
  type SourceType,
} from "../api/studyTools";

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
export default function StudyTools() {
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourcesError, setSourcesError] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("pdf");
  const [sourceId, setSourceId] = useState("");
  const [tab, setTab] = useState<Tab>("quiz");

  useEffect(() => {
    let active = true;
    setSourcesLoading(true);
    listSources()
      .then((items) => {
        if (active) {
          setSources(items);
          setSourcesError("");
        }
      })
      .catch((err) => {
        if (active) setSourcesError(friendlyError(err, "Could not load sources."));
      })
      .finally(() => {
        if (active) setSourcesLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const filteredSources = sources.filter((source) => source.type === sourceType);

  // Keep the selected source valid for the chosen source type.
  useEffect(() => {
    if (filteredSources.length === 0) {
      setSourceId("");
    } else if (!filteredSources.some((source) => source.id === sourceId)) {
      setSourceId(filteredSources[0].id);
    }
  }, [sourceType, sources]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-4 sm:space-y-5">
      {/* Source selection */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">
          Choose a learning source
        </h2>

        <div className="flex flex-wrap gap-4">
          {(["pdf", "youtube"] as SourceType[]).map((type) => (
            <label
              key={type}
              className="inline-flex items-center gap-2 text-sm text-slate-700"
            >
              <input
                type="radio"
                name="source-type"
                value={type}
                checked={sourceType === type}
                onChange={() => setSourceType(type)}
                className="h-4 w-4 accent-orange-500"
              />
              {type === "pdf" ? "Uploaded PDF" : "Processed YouTube Video"}
            </label>
          ))}
        </div>

        <div className="mt-4">
          {sourcesLoading ? (
            <p className="text-sm text-slate-500">Loading your sources…</p>
          ) : sourcesError ? (
            <p className="text-sm text-red-600" role="alert">
              {sourcesError}
            </p>
          ) : filteredSources.length === 0 ? (
            <p className="text-sm text-slate-500">
              {sourceType === "pdf"
                ? "No processed PDFs yet. Upload and process one first."
                : "No processed videos yet. Process a YouTube video first."}
            </p>
          ) : (
            <select
              value={sourceId}
              onChange={(event) => setSourceId(event.target.value)}
              aria-label="Select a processed source"
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
            >
              {filteredSources.map((source) => (
                <option key={source.id} value={source.id}>
                  {source.title}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="mb-4 flex gap-2">
          {(["quiz", "notes"] as Tab[]).map((name) => {
            const isActive = tab === name;
            return (
              <button
                key={name}
                type="button"
                onClick={() => setTab(name)}
                className={
                  "rounded-lg px-4 py-2 text-sm font-medium transition-colors " +
                  (isActive
                    ? "bg-orange-500 text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-100")
                }
              >
                {name === "quiz" ? "Quiz" : "Notes"}
              </button>
            );
          })}
        </div>

        {tab === "quiz" ? (
          <QuizPanel sourceId={sourceId} sourceType={sourceType} />
        ) : (
          <NotesPanel sourceId={sourceId} sourceType={sourceType} />
        )}
      </div>
    </div>
  );
}

/** Quiz generation form and results. */
function QuizPanel({
  sourceId,
  sourceType,
}: {
  sourceId: string;
  sourceType: SourceType;
}) {
  const [questionType, setQuestionType] = useState<QuestionType>("mcq");
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [count, setCount] = useState<QuestionCount>(5);
  const [result, setResult] = useState<QuizResult | null>(null);
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
    } catch (err) {
      setError(friendlyError(err, "Could not generate the quiz."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-600">Type</span>
          <select
            value={questionType}
            onChange={(event) => setQuestionType(event.target.value as QuestionType)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
          >
            {QUESTION_TYPES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-600">Difficulty</span>
          <select
            value={difficulty}
            onChange={(event) => setDifficulty(event.target.value as Difficulty)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm capitalize outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
          >
            {DIFFICULTIES.map((option) => (
              <option key={option} value={option} className="capitalize">
                {option}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-600">Questions</span>
          <select
            value={count}
            onChange={(event) =>
              setCount(Number(event.target.value) as QuestionCount)
            }
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
          >
            {COUNTS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </div>

      <button
        type="button"
        onClick={() => void handleGenerate()}
        disabled={loading || !sourceId}
        className="mt-4 rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-orange-600 disabled:opacity-50"
      >
        {loading ? "Generating…" : "Generate quiz"}
      </button>

      {error && (
        <p className="mt-3 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {result && result.questions.length > 0 && (
        <ol className="mt-5 space-y-4">
          {result.questions.map((question, index) => (
            <li
              key={index}
              className="rounded-lg border border-slate-200 bg-slate-50 p-4"
            >
              <p className="text-sm font-medium text-slate-800">
                {index + 1}. {question.question}
              </p>
              {question.options.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {question.options.map((option, optionIndex) => (
                    <li key={optionIndex} className="text-sm text-slate-600">
                      {String.fromCharCode(65 + optionIndex)}. {option}
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-2 text-sm font-medium text-green-700">
                Answer: {question.correct_answer}
              </p>
              {question.explanation && (
                <p className="mt-1 text-sm text-slate-500">
                  {question.explanation}
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

/** Notes generation form and results with copy / download. */
function NotesPanel({
  sourceId,
  sourceType,
}: {
  sourceId: string;
  sourceType: SourceType;
}) {
  const [noteType, setNoteType] = useState<NoteType>("chapter_summary");
  const [result, setResult] = useState<NotesResult | null>(null);
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
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="block flex-1 text-sm">
          <span className="mb-1 block font-medium text-slate-600">Notes type</span>
          <select
            value={noteType}
            onChange={(event) => setNoteType(event.target.value as NoteType)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
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
          className="rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-orange-600 disabled:opacity-50"
        >
          {loading ? "Generating…" : "Generate notes"}
        </button>
      </div>

      {error && (
        <p className="mt-3 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {result && (
        <div className="mt-5">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void handleCopy()}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-100"
            >
              {copied ? "Copied!" : "Copy notes"}
            </button>
            <button
              type="button"
              onClick={handleDownload}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-100"
            >
              Download .md
            </button>
          </div>
          <pre className="whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-relaxed text-slate-800">
            {result.content}
          </pre>
        </div>
      )}
    </div>
  );
}
