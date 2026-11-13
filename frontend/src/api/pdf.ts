import { API_BASE_URL, ApiError, authHeaders, getToken, readErrorDetail, request } from "./client";
import type { MessagesResult } from "./history";

export interface UploadResult {
  id: string;
  filename: string;
  original_name: string;
  size: number;
  upload_time: string;
  status: string;
  user_id: string | null;
}

export interface ProcessResult {
  id: string;
  processing_status: string;
  processed_at: string | null;
  page_count: number | null;
  chunk_count: number | null;
}

export interface Citation {
  page: number | null;
  chunk_id: string;
  source_reference: string;
}

export interface ChatResult {
  answer: string;
  citations: Citation[];
  metadata: Record<string, unknown>;
  conversation_id?: string | null;
}

/** A PDF in the user's library. */
export interface DocumentItem {
  id: string;
  original_name: string;
  size: number;
  upload_time: string;
  processing_status: string;
  processed_at: string | null;
  page_count: number | null;
  chunk_count: number | null;
  message_count: number;
  last_active: string;
}

/**
 * Upload a PDF file and return its stored metadata.
 *
 * Uses XMLHttpRequest so upload progress can be reported to the caller.
 */
export function uploadPdf(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<UploadResult> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE_URL}/pdf/upload`);
    const token = getToken();
    if (token) {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    }

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as UploadResult);
        } catch {
          reject(new ApiError(xhr.status, "Received an invalid server response."));
        }
        return;
      }

      let detail = xhr.statusText || "Upload failed.";
      try {
        const body = JSON.parse(xhr.responseText);
        if (typeof body?.detail === "string") {
          detail = body.detail;
        }
      } catch {
        // Ignore parse errors and use the status text fallback.
      }
      reject(new ApiError(xhr.status, detail));
    };

    xhr.onerror = () => reject(new ApiError(0, "Network error during upload."));

    xhr.send(form);
  });
}

/** Extract, clean, and chunk a previously uploaded PDF for local storage. */
export async function processPdf(fileId: string): Promise<ProcessResult> {
  const response = await fetch(`${API_BASE_URL}/pdf/${fileId}/process`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response.json();
}

/** Ask a question about a processed PDF. */
export async function chatWithPdf(
  fileId: string,
  question: string,
): Promise<ChatResult> {
  const response = await fetch(`${API_BASE_URL}/pdf/${fileId}/chat`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response.json();
}

/** Every PDF the user uploaded, most recently active first. */
export async function listDocuments(): Promise<DocumentItem[]> {
  const result = await request<{ documents: DocumentItem[] }>("GET", "/pdf/documents");
  return result.documents;
}

/** The saved conversation about one PDF. */
export function getPdfMessages(fileId: string): Promise<MessagesResult> {
  return request("GET", `/pdf/${fileId}/messages`);
}

/** Clear the saved conversation about one PDF. */
export function clearPdfMessages(fileId: string): Promise<void> {
  return request("DELETE", `/pdf/${fileId}/messages`);
}

/** Delete a PDF with its text, index and conversation. */
export function deleteDocument(fileId: string): Promise<void> {
  return request("DELETE", `/pdf/${fileId}`);
}
