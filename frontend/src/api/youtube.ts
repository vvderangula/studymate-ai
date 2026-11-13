import { API_BASE_URL, ApiError, authHeaders, readErrorDetail, request } from "./client";
import type { MessagesResult } from "./history";
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

/** A processed video in the user's library. */
export interface VideoItem {
  video_id: string;
  url: string;
  title: string;
  duration: number | null;
  thumbnail: string | null;
  processed_at: string | null;
  chunk_count: number | null;
  message_count: number;
  last_active: string;
}

/** The user's processed videos, most recently active first. */
export async function listVideos(): Promise<VideoItem[]> {
  const result = await request<{ videos: VideoItem[] }>("GET", "/youtube/videos");
  return result.videos;
}

/** The saved conversation about one video. */
export function getVideoMessages(videoId: string): Promise<MessagesResult> {
  return request("GET", `/youtube/${videoId}/messages`);
}

/** Clear the saved conversation about one video. */
export function clearVideoMessages(videoId: string): Promise<void> {
  return request("DELETE", `/youtube/${videoId}/messages`);
}

/** Remove a video (and its conversation) from the user's library. */
export function deleteVideo(videoId: string): Promise<void> {
  return request("DELETE", `/youtube/${videoId}`);
}
