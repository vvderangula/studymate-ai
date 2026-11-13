import {
  request, API_BASE_URL, ApiError, authHeaders, readErrorDetail } from "./client";

export type SourceType = "pdf" | "youtube";
export type QuestionType = "mcq" | "true_false" | "short_answer";
export type Difficulty = "easy" | "medium" | "hard";
export type QuestionCount = 5 | 10 | 20;
export type NoteType =
  | "chapter_summary"
  | "key_points"
  | "important_concepts"
  | "formula_sheet"
  | "revision_notes";

export interface SourceItem {
  id: string;
  type: SourceType;
  title: string;
}

export interface QuizQuestion {
  type: string;
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
}

export interface QuizResult {
  id?: string | null;
  source_title?: string;
  created_at?: string | null;
  source_id: string;
  source_type: SourceType;
  question_type: QuestionType;
  difficulty: Difficulty;
  questions: QuizQuestion[];
}

export interface NotesResult {
  id?: string | null;
  source_title?: string;
  created_at?: string | null;
  source_id: string;
  source_type: SourceType;
  note_type: NoteType;
  content: string;
}

/** List processed PDFs and YouTube videos available for study tools. */
export async function listSources(): Promise<SourceItem[]> {
  const response = await fetch(`${API_BASE_URL}/study-tools/sources`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  const body = (await response.json()) as { sources: SourceItem[] };
  return body.sources;
}

/** Generate a quiz from a processed source. */
export async function generateQuiz(params: {
  sourceId: string;
  sourceType: SourceType;
  questionType: QuestionType;
  difficulty: Difficulty;
  count: QuestionCount;
}): Promise<QuizResult> {
  const response = await fetch(`${API_BASE_URL}/study-tools/quiz`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      source_id: params.sourceId,
      source_type: params.sourceType,
      question_type: params.questionType,
      difficulty: params.difficulty,
      count: params.count,
    }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response.json();
}

/** Generate study notes from a processed source. */
export async function generateNotes(params: {
  sourceId: string;
  sourceType: SourceType;
  noteType: NoteType;
}): Promise<NotesResult> {
  const response = await fetch(`${API_BASE_URL}/study-tools/notes`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      source_id: params.sourceId,
      source_type: params.sourceType,
      note_type: params.noteType,
    }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response.json();
}

/** A saved quiz or note set, as listed in history. */
export interface StudyHistoryItem {
  id: string;
  kind: "quiz" | "notes";
  source_type: SourceType;
  source_id: string;
  source_title: string;
  created_at: string;
  label: string;
}

/** Every saved quiz and note set, newest first. */
export async function getStudyHistory(): Promise<StudyHistoryItem[]> {
  const result = await request<{ items: StudyHistoryItem[] }>("GET", "/study-tools/history");
  return result.items;
}

export function getQuiz(id: string): Promise<QuizResult> {
  return request("GET", `/study-tools/quizzes/${id}`);
}

export function getNotes(id: string): Promise<NotesResult> {
  return request("GET", `/study-tools/notes/${id}`);
}

export function deleteQuiz(id: string): Promise<void> {
  return request("DELETE", `/study-tools/quizzes/${id}`);
}

export function deleteNotes(id: string): Promise<void> {
  return request("DELETE", `/study-tools/notes/${id}`);
}
