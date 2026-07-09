import { API_BASE_URL, ApiError, authHeaders, readErrorDetail } from "./client";
import type { ChatResult } from "./pdf";

export interface YoutubeProcessResult {
  video_id: string;
  title: string;
  duration: number | null;
  thumbnail: string | null;
  processing_status: string;
  processed_at: string | null;
  chunk_count: number | null;
}

/** Retrieve and process a YouTube video's transcript for chatting. */
export async function processYoutube(url: string): Promise<YoutubeProcessResult> {
  const response = await fetch(`${API_BASE_URL}/youtube/process`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ url }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response.json();
}

/** Ask a question about a processed YouTube video. */
export async function chatWithYoutube(
  videoId: string,
  question: string,
): Promise<ChatResult> {
  const response = await fetch(`${API_BASE_URL}/youtube/${videoId}/chat`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response.json();
}
