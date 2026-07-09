# Milestone 01 – Learn from PDF

## Objective
Deliver the core PDF-based learning experience that allows users to upload study materials and interact with them conversationally. This milestone establishes the foundational learning capability of StudyMate AI and represents the primary value of the MVP.

## Scope
- PDF upload and management (upload, view list, delete).
- Processing of uploaded PDFs so their content becomes queryable.
- Conversational AI chat over uploaded PDF content.
- Context-aware answers grounded in the selected PDF.
- Citation support for answers derived from source material.
- Conversation history for PDF study sessions.

## Out of Scope
- Learning from any source other than PDFs (e.g., YouTube, research papers).
- Quiz generation, notes generation, and academic search.
- Collaborative or multi-user shared study sessions.
- Mobile application experience.

## User Stories
- As a student, I want to upload my PDF, so that I can study it interactively.
- As a student, I want to view all my uploaded PDFs, so that I can choose what to study.
- As a student, I want to delete outdated PDFs, so that my library stays organized.
- As a student, I want to ask questions from a PDF, so that I can understand difficult topics faster.
- As a student, I want answers with citations, so that I can verify the information.
- As a student, I want my chat history saved, so that I can continue learning without losing context.

## Functional Requirements
- The system shall allow users to upload PDF files for study use.
- The system shall allow users to view a list of their uploaded PDFs.
- The system shall allow users to delete previously uploaded PDFs.
- The system shall process uploaded PDFs so content becomes searchable and queryable.
- The system shall allow users to ask questions related to PDF content.
- The system shall provide context-aware answers based on the selected PDF content.
- The system shall display citation support for answers derived from source material.
- The system shall maintain conversation history for PDF study sessions.

## Non Functional Requirements
- Responses to common actions should be delivered with low latency.
- Retrieval of relevant content context should be efficient.
- The interface must remain responsive during upload and chat interactions.
- File upload handling must follow secure upload practices.
- Inputs must be validated before processing.
- Failures must be handled gracefully with clear user feedback.

## Dependencies
- Authentication (Milestone 06) for user-scoped resources and history.
- Shared AI Engine, Retrieval Service, Embedding Service, and Storage Service.
- RAG pipeline as defined in the System Architecture.

## Deliverables
- PDF upload capability.
- PDF processing capability.
- AI chat over PDF content.
- Citation-supported answers.
- Conversation history.
- Associated tests for the module.

## Phase Breakdown
- Phase A: PDF upload and management. **(Phase 1: PDF Upload & Storage — Completed)**
- Phase B: PDF processing and content preparation for retrieval. **(Phase 2: PDF Processing Pipeline — Completed)**
- Phase C: AI chat with context-aware, cited answers. **(Phase 3: Embeddings, Retrieval & Cited Chat — Completed)**
- Phase D: Conversation history persistence. **(Phase 4: PDF Chat Experience — Completed, client-side history)**
- Phase E: Testing and acceptance verification.

## Progress
- **Phase 1 — PDF Upload & Storage: Completed.** Upload endpoint with content-type, extension, size, and magic-byte validation; UUID generation; file storage; SQLite metadata persistence; and a frontend upload page with drag & drop, progress, success, and error handling. Covered by backend and frontend tests.
- **Phase 2 — PDF Processing Pipeline: Completed.** Processing endpoint that extracts per-page text, normalizes whitespace, filters empty pages, chunks the text, and stores chunks as local JSON; extended metadata schema (`processing_status`, `processed_at`, `page_count`, `chunk_count`) with in-place migration; failure handling for missing, corrupted, and scanned/image-only PDFs; and a frontend flow that auto-processes after upload with progress, a completion summary, and retry. Covered by backend and frontend tests.
- **Phase 3 — Embeddings, Retrieval & Cited Chat: Completed.** Reusable ChromaDB vector store service (add/update/search/count/delete); embedding generation for processed chunks with page and chunk-id citation metadata, a configurable embedding provider, and skip-on-reindex to avoid duplicate vectors; semantic retrieval with configurable `top_k`; a centralized RAG pipeline (retrieve → assemble prompt → LLM → answer → page citations); and a `POST /pdf/{id}/chat` endpoint returning answer, citations, and metadata with 400/404/422/502 error handling. Covered by backend tests (vector store, embedding, retrieval, RAG, and chat API).
- **Phase 4 — PDF Chat Experience (Frontend): Completed.** Redesigned chat interface (user/AI bubbles, auto-scroll, Enter-to-send, Shift+Enter newline, input disabled while generating); per-PDF conversation history persisted client-side with resume and clear; citation display with page badges and an expand/collapse sources panel; lightweight loading states (Uploading/Processing/Searching/Generating); friendly error handling (network, empty question, processing failure, missing PDF); contextual empty states; and UI polish for spacing, typography, and mobile responsiveness. Covered by frontend tests (chat flow, conversation history, citation rendering, loading states, and error handling).

## Acceptance Criteria
- A user can upload a valid PDF and receive a success confirmation.
- The uploaded PDF appears in the user's resource list.
- The PDF becomes available for question-answer interaction after processing.
- The user receives relevant answers to PDF-related questions.
- Citations are displayed with answers when source grounding is used.
- Conversation history is saved and can be reopened by the user.

## Definition of Done
- Requirements are satisfied.
- Acceptance criteria are satisfied.
- Tests are passing.
- Documentation is updated.
- No known critical bugs remain.
- Code has been reviewed.
- No TODOs are left behind.

## Risks
- Variability in PDF quality may affect content extraction reliability.
- Large files may impact processing time and user experience.
- Retrieval quality may affect answer relevance and citation accuracy.

## Notes
This milestone is the cornerstone of the MVP and must strictly follow the defined architecture and project rules. It should reuse shared services rather than introducing module-specific infrastructure.
