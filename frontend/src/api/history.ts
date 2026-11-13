import type { Citation } from "./pdf";

/** A message as stored on the server. */
export interface StoredMessageDto {
  id: string;
  role: "user" | "assistant";
  text: string;
  created_at: string;
  citations: Citation[];
}

/** The stored conversation about one source (PDF, video). */
export interface MessagesResult {
  conversation_id: string | null;
  messages: StoredMessageDto[];
}

/** A saved conversation as listed in history. */
export interface ConversationSummary {
  id: string;
  kind: string;
  title: string;
  source_id: string | null;
  message_count: number;
  preview: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: StoredMessageDto[];
}
