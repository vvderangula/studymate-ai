import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import {
  loadConversation,
  saveConversation,
  setLastPdfId,
  type StoredMessage,
} from "../api/conversations";
import { chatWithPdf } from "../api/pdf";
import PdfChat from "./PdfChat";

vi.mock("../api/pdf", () => ({
  uploadPdf: vi.fn(),
  processPdf: vi.fn(),
  chatWithPdf: vi.fn(),
}));

const mockedChat = vi.mocked(chatWithPdf);

const FILE_ID = "abc123";

/** Seed a ready PDF so the chat resumes as usable on mount. */
function seedReady(messages: StoredMessage[] = []): void {
  setLastPdfId(FILE_ID);
  saveConversation(FILE_ID, messages);
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

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe("PdfChat", () => {
  it("shows an empty state when no PDF has been uploaded", () => {
    render(<PdfChat />);

    expect(
      screen.getByText(/no pdf yet\. upload one above/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: /ask a question/i }),
    ).toBeDisabled();
  });

  it("sends a question and shows the AI answer", async () => {
    seedReady();
    mockedChat.mockResolvedValue(answerWithCitations());
    render(<PdfChat />);

    const box = screen.getByRole("textbox", { name: /ask a question/i });
    await userEvent.type(box, "What is photosynthesis?");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("What is photosynthesis?")).toBeInTheDocument();
    await waitFor(() =>
      expect(
        screen.getByText(/photosynthesis converts light into energy/i),
      ).toBeInTheDocument(),
    );
    expect(mockedChat).toHaveBeenCalledWith(FILE_ID, "What is photosynthesis?");
  });

  it("renders citation page badges and expands the sources", async () => {
    seedReady();
    mockedChat.mockResolvedValue(answerWithCitations());
    render(<PdfChat />);

    await userEvent.type(
      screen.getByRole("textbox", { name: /ask a question/i }),
      "Explain it",
    );
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
    render(<PdfChat />);

    const box = screen.getByRole("textbox", { name: /ask a question/i });
    await userEvent.type(box, "Question?");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByRole("status")).toHaveTextContent(/searching your pdf/i);
    expect(box).toBeDisabled();

    resolve(answerWithCitations());
    await screen.findByText(/photosynthesis converts light/i);
  });

  it("shows a friendly message when the chat request fails", async () => {
    seedReady();
    mockedChat.mockRejectedValue(new ApiError(404, "File not found."));
    render(<PdfChat />);

    await userEvent.type(
      screen.getByRole("textbox", { name: /ask a question/i }),
      "Where is it?",
    );
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        /this pdf could not be found/i,
      ),
    );
  });

  it("rejects an empty question with a friendly message", async () => {
    seedReady();
    render(<PdfChat />);

    const box = screen.getByRole("textbox", { name: /ask a question/i });
    await userEvent.type(box, "   {Enter}");

    expect(screen.getByRole("alert")).toHaveTextContent(/please enter a question/i);
    expect(mockedChat).not.toHaveBeenCalled();
  });

  it("does not send on Shift+Enter and keeps a newline", async () => {
    seedReady();
    render(<PdfChat />);

    const box = screen.getByRole("textbox", { name: /ask a question/i });
    await userEvent.type(box, "line one{Shift>}{Enter}{/Shift}line two");

    expect(mockedChat).not.toHaveBeenCalled();
    expect((box as HTMLTextAreaElement).value).toContain("\n");
  });

  it("resumes a stored conversation on mount", () => {
    seedReady([
      { id: 1, role: "user", text: "Earlier question" },
      { id: 2, role: "assistant", text: "Earlier answer" },
    ]);

    render(<PdfChat />);

    expect(screen.getByText("Earlier question")).toBeInTheDocument();
    expect(screen.getByText("Earlier answer")).toBeInTheDocument();
  });

  it("clears the conversation and its stored history", async () => {
    seedReady([
      { id: 1, role: "user", text: "Kept until cleared" },
      { id: 2, role: "assistant", text: "Answer here" },
    ]);

    render(<PdfChat />);
    expect(screen.getByText("Kept until cleared")).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: /clear conversation/i }),
    );

    expect(screen.queryByText("Kept until cleared")).not.toBeInTheDocument();
    expect(loadConversation(FILE_ID)).toEqual([]);
    const log = screen.getByRole("log");
    expect(
      within(log).getByText(/no messages yet\. ask your first question/i),
    ).toBeInTheDocument();
  });
});
