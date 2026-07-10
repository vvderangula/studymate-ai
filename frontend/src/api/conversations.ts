import type { Citation } from "./pdf";

/**
 * Local persistence for PDF chat conversations.
 *
 * Conversation history is stored per uploaded PDF in the browser's
 * ``localStorage`` so a user can resume a previous conversation. This module
 * contains the frontend business logic for reading and writing that history;
 * components stay presentational and never touch storage directly.
 */

export interface StoredMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
}

const CONVERSATION_PREFIX = "studymate:conversation:";
const LAST_PDF_KEY = "studymate:last-pdf";

function scopedConversationKey(scope: string, userId: string, resourceId: string): string {
  return `${CONVERSATION_PREFIX}${scope}:${userId}:${resourceId}`;
}

function legacyConversationKey(resourceId: string): string {
  return `${CONVERSATION_PREFIX}${resourceId}`;
}

function scopedLastPdfKey(userId: string): string {
  return `${LAST_PDF_KEY}:${userId}`;
}

/** Return the stored conversation for a PDF, or an empty list. */
export function loadConversation(
  fileId: string,
  userId?: string,
  scope: "pdf" | "youtube" = "pdf",
): StoredMessage[] {
  try {
    const key = userId
      ? scopedConversationKey(scope, userId, fileId)
      : legacyConversationKey(fileId);
    const raw = localStorage.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as StoredMessage[]) : [];
  } catch {
    return [];
  }
}

/** Persist the conversation for a PDF. */
export function saveConversation(
  fileId: string,
  messages: StoredMessage[],
  userId?: string,
  scope: "pdf" | "youtube" = "pdf",
): void {
  try {
    const key = userId
      ? scopedConversationKey(scope, userId, fileId)
      : legacyConversationKey(fileId);
    localStorage.setItem(
      key,
      JSON.stringify(messages),
    );
  } catch {
    // Ignore storage quota or serialization errors; history is best-effort.
  }
}

/** Remove the stored conversation for a PDF. */
export function clearConversation(
  fileId: string,
  userId?: string,
  scope: "pdf" | "youtube" = "pdf",
): void {
  try {
    const key = userId
      ? scopedConversationKey(scope, userId, fileId)
      : legacyConversationKey(fileId);
    localStorage.removeItem(key);
  } catch {
    // Ignore storage errors.
  }
}

/** Return the id of the most recently active PDF, if any. */
export function getLastPdfId(userId?: string): string | null {
  try {
    return localStorage.getItem(userId ? scopedLastPdfKey(userId) : LAST_PDF_KEY);
  } catch {
    return null;
  }
}

/** Record the most recently active PDF so it can be resumed later. */
export function setLastPdfId(fileId: string, userId?: string): void {
  try {
    localStorage.setItem(userId ? scopedLastPdfKey(userId) : LAST_PDF_KEY, fileId);
  } catch {
    // Ignore storage errors.
  }
}
