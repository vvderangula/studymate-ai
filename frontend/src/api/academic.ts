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
