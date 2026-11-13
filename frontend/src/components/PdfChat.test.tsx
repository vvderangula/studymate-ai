import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import type { StoredMessageDto } from "../api/history";
import {
  chatWithPdf,
  clearPdfMessages,
  getPdfMessages,
  listDocuments,
  type DocumentItem,
} from "../api/pdf";
import PdfChat from "./PdfChat";

vi.mock("../api/pdf", () => ({
  uploadPdf: vi.fn(),
  processPdf: vi.fn(),
  chatWithPdf: vi.fn(),
  listDocuments: vi.fn(),
  getPdfMessages: vi.fn(),
  clearPdfMessages: vi.fn(),
  deleteDocument: vi.fn(),
}));

const mockedChat = vi.mocked(chatWithPdf);
const mockedList = vi.mocked(listDocuments);
const mockedMessages = vi.mocked(getPdfMessages);
const mockedClear = vi.mocked(clearPdfMessages);

const FILE_ID = "abc123";

function doc(): DocumentItem {
  return {
    id: FILE_ID,
    original_name: "notes.pdf",
    size: 1000,
    upload_time: "2026-11-01T10:00:00Z",
    processing_status: "completed",
    processed_at: "2026-11-01T10:00:05Z",
    page_count: 6,
    chunk_count: 12,
    message_count: 0,
    last_active: "2026-11-01T10:00:05Z",
  };
}

function stored(id: string, role: "user" | "assistant", text: string): StoredMessageDto {
  return { id, role, text, created_at: "2026-11-01T10:01:00Z", citations: [] };
}

/** The server has one processed PDF with the given saved conversation. */
function seedReady(messages: StoredMessageDto[] = []): void {
  mockedList.mockResolvedValue([doc()]);
  mockedMessages.mockResolvedValue({ conversation_id: "conv1", messages });
}

/** Render and wait until the saved PDF is open and the composer is usable. */
async function renderReady() {
  render(<PdfChat />);
  const box = screen.getByRole("textbox", { name: /ask a question/i });
  await waitFor(() => expect(box).toBeEnabled());
  return box;
}

function answerWithCitations() {
  return {
    answer: "Photosynthesis converts light into energy.",
    citations: [
      { page: 3, chunk_id: "abc123-0", source_reference: "notes.pdf, page 3" },
      { page: 5, chunk_id: "abc123-1", source_reference: "notes.pdf, page 5" },
    ],
    metadata: { file_id: FILE_ID, chunks_retrieved: 2, top_k: 4 },
  };
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("PdfChat", () => {
  it("shows an empty state when no PDF has been uploaded", async () => {
    mockedList.mockResolvedValue([]);
    render(<PdfChat />);

    expect(await screen.findByText(/no pdf yet\. upload one/i)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /ask a question/i })).toBeDisabled();
  });

  it("lists the saved PDFs from the server", async () => {
    seedReady();
    render(<PdfChat />);

    const list = await screen.findByRole("region", { name: "Your PDFs" });
    expect(await within(list).findByText("notes.pdf")).toBeInTheDocument();
  });

  it("sends a question and shows the AI answer", async () => {
    seedReady();
    mockedChat.mockResolvedValue(answerWithCitations());
    const box = await renderReady();

    await userEvent.type(box, "What is photosynthesis?");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("What is photosynthesis?")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText(/photosynthesis converts light into energy/i)).toBeInTheDocument(),
    );
    expect(mockedChat).toHaveBeenCalledWith(FILE_ID, "What is photosynthesis?");
  });

  it("renders citation page badges and expands the sources", async () => {
    seedReady();
    mockedChat.mockResolvedValue(answerWithCitations());
    const box = await renderReady();

    await userEvent.type(box, "Explain it");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await screen.findByText(/photosynthesis converts light/i);
    expect(screen.getByRole("button", { name: "Page 3" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Page 5" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /sources \(2\)/i }));

    expect(screen.getByText(/notes\.pdf, page 3/i)).toBeInTheDocument();
    expect(screen.getByText(/notes\.pdf, page 5/i)).toBeInTheDocument();
  });

  it("shows a searching indicator while the answer is generated", async () => {
    seedReady();
    let resolve!: (value: ReturnType<typeof answerWithCitations>) => void;
    mockedChat.mockReturnValue(
      new Promise((res) => {
        resolve = res;
      }),
    );
    const box = await renderReady();

    await userEvent.type(box, "Question?");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText(/searching your pdf/i)).toBeInTheDocument();
    expect(box).toBeDisabled();

    resolve(answerWithCitations());
    await screen.findByText(/photosynthesis converts light/i);
  });

  it("shows a friendly message when the chat request fails", async () => {
    seedReady();
    mockedChat.mockRejectedValue(new ApiError(404, "File not found."));
    const box = await renderReady();

    await userEvent.type(box, "Where is it?");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/this pdf could not be found/i),
    );
  });

  it("rejects an empty question with a friendly message", async () => {
    seedReady();
    const box = await renderReady();

    await userEvent.type(box, "   {Enter}");

    expect(screen.getByRole("alert")).toHaveTextContent(/please enter a question/i);
    expect(mockedChat).not.toHaveBeenCalled();
  });

  it("does not send on Shift+Enter and keeps a newline", async () => {
    seedReady();
    const box = await renderReady();

    await userEvent.type(box, "line one{Shift>}{Enter}{/Shift}line two");

    expect(mockedChat).not.toHaveBeenCalled();
    expect((box as HTMLTextAreaElement).value).toContain("\n");
  });

  it("reopens the saved conversation on mount", async () => {
    seedReady([stored("1", "user", "Earlier question"), stored("2", "assistant", "Earlier answer")]);

    render(<PdfChat />);

    expect(await screen.findByText("Earlier question")).toBeInTheDocument();
    expect(screen.getByText("Earlier answer")).toBeInTheDocument();
    expect(mockedMessages).toHaveBeenCalledWith(FILE_ID);
  });

  it("clears the conversation on the server", async () => {
    seedReady([stored("1", "user", "Kept until cleared"), stored("2", "assistant", "Answer here")]);
    mockedClear.mockResolvedValue(undefined);

    render(<PdfChat />);
    expect(await screen.findByText("Kept until cleared")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /clear conversation/i }));

    await waitFor(() => expect(screen.queryByText("Kept until cleared")).not.toBeInTheDocument());
    expect(mockedClear).toHaveBeenCalledWith(FILE_ID);
    const log = screen.getByRole("log");
    expect(within(log).getByText(/no messages yet\. ask your first question/i)).toBeInTheDocument();
  });
});
