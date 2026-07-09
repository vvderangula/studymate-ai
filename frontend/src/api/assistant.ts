import { API_BASE_URL, ApiError, authHeaders, readErrorDetail } from "./client";

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface GeneralChatResult {
  answer: string;
}

/** Send a message to the general-purpose AI assistant. */
export async function generalChat(
  message: string,
  history: ChatTurn[] = [],
): Promise<GeneralChatResult> {
  const response = await fetch(`${API_BASE_URL}/assistant/chat`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ message, history }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response.json();
}
