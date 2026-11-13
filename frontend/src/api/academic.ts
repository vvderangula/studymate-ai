import { request } from "./client";
import type { StoredMessageDto } from "./history";
import { API_BASE_URL, ApiError, authHeaders, readErrorDetail } from "./client";

export interface PaperItem {
  paper_id: string;
  title: string;
  authors: string[];
  year: number | null;
  abstract: string | null;
  pdf_url: string | null;
}

export interface PaperSearchResult {
  search_id?: string | null;
  created_at?: string | null;
  query: string;
  papers: PaperItem[];
}

export interface PaperSummary {
  paper_id: string;
  summary: string;
}

export interface PaperAnswer {
  paper_id: string;
  question: string;
  answer: string;
}

/** Search academic papers by topic. */
export async function searchPapers(
  query: string,
  limit = 10,
): Promise<PaperSearchResult> {
  const response = await fetch(`${API_BASE_URL}/academic/search`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ query, limit }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response.json();
}

/** Generate an AI summary for a paper using its abstract. */
export async function summarizePaper(paper: PaperItem): Promise<PaperSummary> {
  const response = await fetch(`${API_BASE_URL}/academic/papers/summarize`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      paper_id: paper.paper_id,
      title: paper.title,
      authors: paper.authors,
      year: paper.year,
      abstract: paper.abstract,
    }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response.json();
}

/** Ask a question about a paper using its abstract as context. */
export async function askPaper(
  paper: PaperItem,
  question: string,
): Promise<PaperAnswer> {
  const response = await fetch(`${API_BASE_URL}/academic/papers/ask`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      paper_id: paper.paper_id,
      title: paper.title,
      abstract: paper.abstract,
      question,
    }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response.json();
}

/** A past search, as listed in history. */
export interface SearchHistoryItem {
  id: string;
  query: string;
  result_count: number;
  created_at: string;
}

/** A paper the user summarised or asked about. */
export interface SavedPaperItem {
  paper: PaperItem;
  has_summary: boolean;
  message_count: number;
  updated_at: string;
}

/** Everything saved about one paper. */
export interface PaperDetail {
  paper: PaperItem;
  summary: string | null;
  conversation_id: string | null;
  messages: StoredMessageDto[];
}

export function listSearches(): Promise<SearchHistoryItem[]> {
  return request("GET", "/academic/searches");
}

/** Reopen a past search with its saved results (no new lookup). */
export function getSearch(id: string): Promise<PaperSearchResult> {
  return request("GET", `/academic/searches/${id}`);
}

export function deleteSearch(id: string): Promise<void> {
  return request("DELETE", `/academic/searches/${id}`);
}

export function listSavedPapers(): Promise<SavedPaperItem[]> {
  return request("GET", "/academic/papers");
}

/** Saved summary + Q&A for a paper; rejects with 404 if never saved. */
export function getSavedPaper(paperId: string): Promise<PaperDetail> {
  return request("GET", `/academic/papers/${encodeURIComponent(paperId)}`);
}

export function deleteSavedPaper(paperId: string): Promise<void> {
  return request("DELETE", `/academic/papers/${encodeURIComponent(paperId)}`);
}
