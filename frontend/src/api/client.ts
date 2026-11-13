/** Base URL of the StudyMate AI backend API. */
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

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

// ---------------------------------------------------------------------------
// Auth token helpers
// ---------------------------------------------------------------------------

const TOKEN_KEY = "studymate_token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Ignore storage errors.
  }
}

export function removeToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Ignore storage errors.
  }
}

/**
 * Return headers that include Authorization when a token is stored.
 * Merge with additional headers as needed.
 */
export function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = { ...extra };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * JSON request to the API with the stored auth token.
 * Throws ApiError on a non-OK response; resolves to undefined for 204.
 */
export async function request<T>(
  method: "GET" | "POST" | "DELETE",
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: authHeaders(body !== undefined ? { "Content-Type": "application/json" } : {}),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}
