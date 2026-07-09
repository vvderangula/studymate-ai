/** Base URL of the StudyMate AI backend API. */
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** Error thrown when an API request returns a non-OK response. */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Extract a human-readable error message from a failed response.
 * Falls back to the status text when no detail is provided.
 */
export async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      return body.detail;
    }
  } catch {
    // Ignore JSON parse errors and fall through to the status text.
  }
  return response.statusText || "Request failed";
}
