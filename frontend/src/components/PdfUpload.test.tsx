import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { processPdf, uploadPdf } from "../api/pdf";
import PdfUpload from "./PdfUpload";

vi.mock("../api/pdf", () => ({
  uploadPdf: vi.fn(),
  processPdf: vi.fn(),
}));

const mockedUploadPdf = vi.mocked(uploadPdf);
const mockedProcessPdf = vi.mocked(processPdf);

function makePdf(): File {
  return new File(["%PDF-1.4 data"], "notes.pdf", { type: "application/pdf" });
}

function uploadedMeta() {
  return {
    id: "abc123",
    filename: "abc123.pdf",
    original_name: "notes.pdf",
    size: 13,
    upload_time: "2026-07-10T00:00:00+00:00",
    status: "uploaded",
    user_id: null,
  };
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("PdfUpload", () => {
  it("shows a success message after a successful upload", async () => {
    mockedUploadPdf.mockResolvedValue(uploadedMeta());
    mockedProcessPdf.mockResolvedValue({
      id: "abc123",
      processing_status: "completed",
      processed_at: "2026-07-10T00:00:01+00:00",
      page_count: 3,
      chunk_count: 5,
    });

    render(<PdfUpload />);

    const input = screen.getByTestId("file-input");
    await userEvent.upload(input, makePdf());

    await waitFor(() =>
      expect(
        screen.getByText(/uploaded successfully/i),
      ).toBeInTheDocument(),
    );
    expect(mockedUploadPdf).toHaveBeenCalledOnce();
  });

  it("shows an error message when the upload fails", async () => {
    mockedUploadPdf.mockRejectedValue(new ApiError(400, "File is not a valid PDF."));

    render(<PdfUpload />);

    const input = screen.getByTestId("file-input");
    await userEvent.upload(input, makePdf());

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "File is not a valid PDF.",
      ),
    );
  });

  it("processes the PDF and reports page and chunk counts", async () => {
    mockedUploadPdf.mockResolvedValue(uploadedMeta());
    mockedProcessPdf.mockResolvedValue({
      id: "abc123",
      processing_status: "completed",
      processed_at: "2026-07-10T00:00:01+00:00",
      page_count: 4,
      chunk_count: 12,
    });

    render(<PdfUpload />);

    await userEvent.upload(screen.getByTestId("file-input"), makePdf());

    await waitFor(() =>
      expect(
        screen.getByText(/Processing complete\. 4 pages, 12 chunks\./i),
      ).toBeInTheDocument(),
    );
    expect(mockedProcessPdf).toHaveBeenCalledWith("abc123");
  });

  it("shows a retry button when processing fails and retries on click", async () => {
    mockedUploadPdf.mockResolvedValue(uploadedMeta());
    mockedProcessPdf
      .mockRejectedValueOnce(new ApiError(422, "PDF appears to be scanned."))
      .mockResolvedValueOnce({
        id: "abc123",
        processing_status: "completed",
        processed_at: "2026-07-10T00:00:02+00:00",
        page_count: 2,
        chunk_count: 3,
      });

    render(<PdfUpload />);

    await userEvent.upload(screen.getByTestId("file-input"), makePdf());

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "PDF appears to be scanned.",
      ),
    );

    await userEvent.click(screen.getByRole("button", { name: /retry/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/Processing complete\. 2 pages, 3 chunks\./i),
      ).toBeInTheDocument(),
    );
    expect(mockedProcessPdf).toHaveBeenCalledTimes(2);
  });
});
