import { useRef, useState } from "react";

import { ApiError } from "../api/client";
import {
  processPdf,
  uploadPdf,
  type ProcessResult,
  type UploadResult,
} from "../api/pdf";

type Status = "idle" | "uploading" | "success" | "error";
type ProcessStatus = "idle" | "processing" | "done" | "failed";

const ACCEPTED_TYPE = "application/pdf";

interface PdfUploadProps {
  /** Called when a PDF has been uploaded and fully processed. */
  onProcessed?: (fileId: string, result: ProcessResult) => void;
  /** Called as the upload/processing lifecycle status changes. */
  onStatusChange?: (
    status: "idle" | "uploading" | "processing" | "ready" | "failed",
  ) => void;
}

/**
 * PDF upload panel with drag & drop, a browse button, upload progress,
 * and success / error feedback. After a successful upload it automatically
 * runs the processing pipeline, reporting progress and offering a retry.
 */
export default function PdfUpload({ onProcessed, onStatusChange }: PdfUploadProps) {
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
      void startProcessing(uploaded.id);
    } catch (err) {
      setStatus("error");
      setError(err instanceof ApiError ? err.message : "Upload failed.");
      onStatusChange?.("failed");
    }
  }

  async function startProcessing(fileId: string) {
    setProcessStatus("processing");
    setProcessError("");
    setProcessResult(null);
    onStatusChange?.("processing");

    try {
      const processed = await processPdf(fileId);
      setProcessResult(processed);
      setProcessStatus("done");
      onStatusChange?.("ready");
      onProcessed?.(fileId, processed);
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

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload PDF by dragging a file here or pressing to browse"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        className={
          "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors " +
          (dragActive
            ? "border-orange-400 bg-orange-50"
            : "border-slate-300 hover:border-orange-300")
        }
      >
        <p className="text-sm font-medium text-slate-700">
          Drag &amp; drop your PDF here
        </p>
        <p className="text-xs text-slate-400">or</p>
        <button
          type="button"
          disabled={isUploading}
          onClick={(event) => {
            event.stopPropagation();
            inputRef.current?.click();
          }}
          className="rounded-lg bg-orange-500 px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-orange-600 disabled:opacity-50"
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

      {isUploading && (
        <div className="mt-4" aria-live="polite">
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-orange-500 transition-all"
              style={{ width: `${progress}%` }}
              role="progressbar"
              aria-valuenow={progress}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
          <p className="mt-2 text-xs text-slate-500">Uploading… {progress}%</p>
        </div>
      )}

      {status === "success" && result && (
        <p className="mt-4 text-sm text-green-600" role="status">
          "{result.original_name}" uploaded successfully.
        </p>
      )}

      {status === "error" && (
        <p className="mt-4 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {processStatus === "processing" && (
        <p className="mt-2 text-sm text-slate-500" role="status">
          Processing…
        </p>
      )}

      {processStatus === "done" && processResult && (
        <p className="mt-2 text-sm text-green-600" role="status">
          Processing complete. {processResult.page_count ?? 0} pages,{" "}
          {processResult.chunk_count ?? 0} chunks.
        </p>
      )}

      {processStatus === "failed" && (
        <div className="mt-2">
          <p className="text-sm text-red-600" role="alert">
            {processError || "Processing failed."}
          </p>
          {result && (
            <button
              type="button"
              onClick={() => void startProcessing(result.id)}
              className="mt-2 rounded-lg bg-orange-500 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-orange-600"
            >
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
}
