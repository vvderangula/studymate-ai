# Changelog

All notable changes to StudyMate AI are documented in this file.

The format is based on Keep a Changelog, and the project adheres to
semantic versioning.

## [Unreleased]

### Added
- **Milestone 01 – Phase 1: PDF Upload & Storage**
  - Backend `POST /pdf/upload` endpoint that validates, stores, and records PDF uploads.
  - PDF validation: content type, `.pdf` extension, configurable max file size, and PDF magic-byte signature checks to reject corrupted files.
  - UUID generation for each upload and storage of the file in the uploads directory.
  - SQLite database layer with a `pdf_documents` table and a repository for metadata persistence (`id`, `filename`, `original_name`, `size`, `upload_time`, `status`, `user_id`).
  - `PdfService` orchestrating validated storage and metadata persistence.
  - Metadata response returned to the client on successful upload.
  - Frontend upload page with drag & drop, browse button, upload progress, success message, and error handling.
  - Backend tests: valid upload, invalid extension, invalid MIME, corrupted PDF, oversized file, and service/API coverage.
  - Frontend tests: successful upload and upload error handling.
- **Milestone 01 – Phase 2: PDF Processing Pipeline**
  - `POST /pdf/{file_id}/process` endpoint that extracts, cleans, chunks, and locally stores a previously uploaded PDF's text.
  - `ProcessingService` orchestrating per-page text extraction, whitespace normalization, empty-page filtering, chunking, and chunk persistence.
  - Per-page extraction via `PDFExtractor.extract_pages`, tolerating pages without text and raising only on unreadable files.
  - `ChunkStorageService` persisting processed chunks as local JSON files under the configurable `chunks_dir`.
  - Extended `pdf_documents` schema (`processing_status`, `processed_at`, `page_count`, `chunk_count`) with an in-place column migration and a `update_processing` repository method.
  - Failure handling that marks documents as `failed` for missing, corrupted, or scanned/image-only PDFs (HTTP 422) and unknown ids (HTTP 404).
  - Frontend automatic processing after upload with a progress message, completion summary (page and chunk counts), failure message, and a retry button.
  - Backend tests: valid/scanned/corrupted/large PDF processing, whitespace normalization, status transitions, unknown id, real-extractor corruption, and API 200/422/404 coverage.
  - Frontend tests: processing completion summary and processing-failure-then-retry flow.
- **Milestone 01 – Phase 3: Embeddings, Retrieval & Cited Chat**
  - Reusable vector store service: extended `ChromaService` with `add_documents`, `update_documents`, `search`, `count`, and `delete_document` over per-PDF collections.
  - `PdfEmbeddingService` that embeds processed chunks into ChromaDB with citation metadata (page number and chunk id), using the configurable embedding provider and skipping already embedded documents to avoid duplicate vectors.
  - Semantic retrieval with citations via `Retriever.retrieve_with_citations`, returning ranked chunks with page and chunk-id metadata and a configurable `top_k`.
  - Centralized cited prompt assembly (`PromptBuilder.user_prompt_cited`) and an enhanced RAG pipeline (`RAGService.answer_with_citations`) that verifies the PDF, ensures it is embedded, retrieves context, generates an answer, and assembles page citations.
  - `POST /pdf/{file_id}/chat` endpoint returning `answer`, `citations` (page number, chunk id, source reference), and `metadata`, with 400 (empty question), 404 (unknown PDF), 422 (not processed), and 502 (embedding/LLM backend) errors.
  - Backend tests: reusable Chroma vector store operations, embedding generation with page mapping and skip-on-reindex, citation retrieval mapping, cited RAG pipeline, and chat API success/empty/unknown/unprocessed coverage.
- **Milestone 01 – Phase 4: PDF Chat Experience (Frontend)**
  - Redesigned chat interface with user/AI bubbles, auto-scroll to the latest message, a multi-line composer supporting Enter-to-send and Shift+Enter for a new line, and input disabled while an answer is generating.
  - Per-PDF conversation history persisted in the browser, with resume of the most recent conversation on load and a clear-conversation action.
  - Citation display for every grounded answer: page-number badges and an expand/collapse sources panel listing each source reference and chunk id.
  - Lightweight loading states (Uploading…, Processing…, Searching…, Generating answer…) with no streaming.
  - Friendly error handling for network errors, empty questions, processing failures, and missing PDFs.
  - Contextual empty states for no PDF uploaded, PDF still processing, and no messages yet.
  - UI polish for spacing, typography, and mobile responsiveness within the existing design.
  - Frontend tests: chat flow, conversation history (resume and clear), citation rendering, loading states, and error handling.

