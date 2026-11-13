import { request } from "./client";
import type { ConversationDetail, ConversationSummary } from "./history";

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface GeneralChatResult {
  answer: string;
  conversation_id: string;
  title: string;
}

/**
 * Send a message to the assistant. Pass ``conversationId`` to continue a
 * saved chat; omit it to start a new one (the reply carries its id).
 */
export function generalChat(
  message: string,
  conversationId?: string | null,
): Promise<GeneralChatResult> {
  return request("POST", "/assistant/chat", {
    message,
    conversation_id: conversationId ?? null,
  });
}

/** The user's saved chats, most recently active first. */
export function listConversations(): Promise<ConversationSummary[]> {
  return request("GET", "/assistant/conversations");
}

/** One saved chat with its messages. */
export function getConversation(id: string): Promise<ConversationDetail> {
  return request("GET", `/assistant/conversations/${id}`);
}

/** Delete a saved chat. */
export function deleteConversation(id: string): Promise<void> {
  return request("DELETE", `/assistant/conversations/${id}`);
}
