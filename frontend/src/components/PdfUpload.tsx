import { useRef, useState } from "react";

import { ApiError } from "../api/client";
import {
  processPdf,
  uploadPdf,
  type ProcessResult,
  type UploadResult,
} from "../api/pdf";
import { IconUpload } from "./icons";
import { ErrorNotice, ProgressNotice, SuccessNotice } from "./ui";

type Status = "idle" | "uploading" | "success" | "error";
type ProcessStatus = "idle" | "processing" | "done" | "failed";

const ACCEPTED_TYPE = "application/pdf";

interface PdfUploadProps {
  /** Called when a PDF has been uploaded and fully processed. */
  onProcessed?: (fileId: string, result: ProcessResult, name: string) => void;
  /** Called as the upload/processing lifecycle status changes. */
  onStatusChange?: (
    status: "idle" | "uploading" | "processing" | "ready" | "failed",
  ) => void;
  /** Slim single-row variant shown once a document is already loaded. */
  compact?: boolean;
}

/**
 * PDF upload panel with drag & drop, a browse button, upload progress,
 * and success / error feedback. After a successful upload it automatically
 * runs the processing pipeline, reporting progress and offering a retry.
 */
export default function PdfUpload({ onProcessed, onStatusChange, compact = false }: PdfUploadProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [progress, setProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<UploadResult | null>(null);
  const [processStatus, setProcessStatus] = useState<ProcessStatus>("idle");
  const [processResult, setProcessResult] = useState<ProcessResult | null>(null);
  const [processError, setProcessError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function startUpload(file: File) {
    if (file.type !== ACCEPTED_TYPE) {
      setStatus("error");
      setError("Only PDF files are allowed.");
      return;
    }

    setStatus("uploading");
    setProgress(0);
    setError("");
    setResult(null);
    setProcessStatus("idle");
    setProcessResult(null);
    setProcessError("");
    onStatusChange?.("uploading");

    try {
      const uploaded = await uploadPdf(file, setProgress);
      setResult(uploaded);
      setStatus("success");
      void startProcessing(uploaded.id, uploaded.original_name);
    } catch (err) {
      setStatus("error");
      setError(err instanceof ApiError ? err.message : "Upload failed.");
      onStatusChange?.("failed");
    }
  }

  async function startProcessing(fileId: string, name = result?.original_name ?? "") {
    setProcessStatus("processing");
    setProcessError("");
    setProcessResult(null);
    onStatusChange?.("processing");

    try {
      const processed = await processPdf(fileId);
      setProcessResult(processed);
      setProcessStatus("done");
      onStatusChange?.("ready");
      onProcessed?.(fileId, processed, name);
    } catch (err) {
      setProcessStatus("failed");
      setProcessError(
        err instanceof ApiError ? err.message : "Processing failed.",
      );
      onStatusChange?.("failed");
    }
  }

  function handleInputChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) {
      void startUpload(file);
    }
    event.target.value = "";
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);
    const file = event.dataTransfer.files?.[0];
    if (file) {
      void startUpload(file);
    }
  }

  function handleDragOver(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(true);
  }

  function handleDragLeave() {
    setDragActive(false);
  }

  const isUploading = status === "uploading";
  const busy = isUploading || processStatus === "processing";

  const openPicker = () => {
    if (!busy) inputRef.current?.click();
  };

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload PDF by dragging a file here or pressing to browse"
        aria-disabled={busy}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={openPicker}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openPicker();
          }
        }}
        className={
          "flex cursor-pointer rounded-panel border border-dashed transition-colors duration-150 " +
          (compact
            ? "items-center gap-3 px-4 py-3 text-left "
            : "flex-col items-center justify-center gap-2 px-6 py-10 text-center ") +
          (dragActive
            ? "border-accent bg-accent-soft"
            : "border-line-strong bg-canvas hover:border-accent/60 hover:bg-accent-soft/40")
        }
      >
        <IconUpload
          className={
            "shrink-0 transition-colors " +
            (compact ? "h-5 w-5 " : "mb-1 h-6 w-6 ") +
            (dragActive ? "text-accent" : "text-faint")
          }
        />
        <div className={compact ? "min-w-0 flex-1" : ""}>
          <p className="text-sm font-medium text-ink">
            {compact ? "Replace with another PDF" : "Drag & drop your PDF here"}
          </p>
          <p className="text-xs text-muted">
            {compact ? "Drop a file here or browse" : "PDF with selectable text, up to 25 MB"}
          </p>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={(event) => {
            event.stopPropagation();
            openPicker();
          }}
          className={compact ? "btn-quiet" : "btn-secondary mt-2"}
        >
          Browse files
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          onChange={handleInputChange}
          className="hidden"
          data-testid="file-input"
        />
      </div>

      {(isUploading ||
        (status === "success" && result) ||
        status === "error" ||
        processStatus !== "idle") && (
        <div className="mt-3 space-y-2" aria-live="polite">
          {isUploading && (
            <div>
              <div className="flex items-center justify-between text-xs text-muted">
                <span>Uploading…</span>
                <span className="tabular-nums">{progress}%</span>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-sunken">
                <div
                  className="h-full rounded-full bg-accent transition-[width] duration-300 ease-out"
                  style={{ width: `${progress}%` }}
                  role="progressbar"
                  aria-valuenow={progress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                />
              </div>
            </div>
          )}

          {status === "success" && result && (
            <SuccessNotice>"{result.original_name}" uploaded successfully.</SuccessNotice>
          )}

          {status === "error" && <ErrorNotice>{error}</ErrorNotice>}

          {processStatus === "processing" && (
            <ProgressNotice>Reading and indexing your PDF…</ProgressNotice>
          )}

          {processStatus === "done" && processResult && (
            <SuccessNotice>
              Processing complete. {processResult.page_count ?? 0} pages,{" "}
              {processResult.chunk_count ?? 0} chunks.
            </SuccessNotice>
          )}

          {processStatus === "failed" && (
            <div className="space-y-2">
              <ErrorNotice>{processError || "Processing failed."}</ErrorNotice>
              {result && (
                <button
                  type="button"
                  onClick={() => void startProcessing(result.id)}
                  className="btn-secondary w-full"
                >
                  Retry
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
