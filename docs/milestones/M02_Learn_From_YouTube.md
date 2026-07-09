# Milestone 02 – Learn from YouTube

## Objective
Enable users to learn from video content by interacting with video transcripts conversationally. This milestone extends the platform's learning capabilities beyond PDFs while reusing the shared learning foundation.

## Scope
- Submission of a YouTube URL for learning.
- Retrieval of transcript-based content when available.
- Conversational AI chat over video content.
- AI explanations grounded in the available content context.
- Generation of concise study notes from the video material.

## Out of Scope
- Learning from PDFs or research papers within this milestone.
- Quiz generation and dedicated notes-generation module features.
- Video downloading, storage, or playback hosting.
- Support for sources other than YouTube.

## User Stories
- As a student, I want to paste a YouTube URL, so that I can learn from video content in a structured way.
- As a student, I want to ask questions about a video, so that I can clarify concepts without replaying entire sections.
- As a student, I want AI explanations from videos, so that I can simplify complex lectures.
- As a student, I want notes from videos, so that I can revise quickly before exams.

## Functional Requirements
- The system shall allow users to paste a YouTube URL for learning.
- The system shall retrieve transcript-based content when available.
- The system shall allow users to ask questions about the video content.
- The system shall provide AI explanations grounded in the available content context.
- The system shall generate concise study notes from the video material.

## Non Functional Requirements
- Transcript retrieval and response generation should be efficient.
- The interface must remain responsive during processing and chat.
- Inputs, including URLs, must be validated before processing.
- Failures, including unavailable transcripts, must be handled gracefully with clear feedback.
- Secure handling of external content sources must be respected.

## Dependencies
- Authentication (Milestone 06) for user-scoped sessions and history.
- Shared AI Engine, Retrieval Service, Embedding Service, and Chat Service.
- RAG pipeline as defined in the System Architecture.

## Deliverables
- Video content processing capability.
- AI chat over video content.
- Notes generated from video content.
- Citation support where applicable.
- Associated tests for the module.

## Phase Breakdown
- Phase A: YouTube URL submission and validation.
- Phase B: Transcript retrieval and content preparation.
- Phase C: AI chat with context-aligned answers.
- Phase D: Notes generation from video content.
- Phase E: Testing and acceptance verification.

## Acceptance Criteria
- A user can submit a valid YouTube URL for learning.
- Transcript-based content is retrieved when available.
- The user can ask questions specific to the submitted video.
- AI explanations remain context-aligned with the video content.
- Notes can be generated from the selected video content.

## Definition of Done
- Requirements are satisfied.
- Acceptance criteria are satisfied.
- Tests are passing.
- Documentation is updated.
- No known critical bugs remain.
- Code has been reviewed.
- No TODOs are left behind.

## Risks
- Transcripts may be unavailable or incomplete for some videos.
- External content availability may vary and affect reliability.
- Retrieval quality may affect the relevance of answers and notes.

## Notes
This milestone must reuse the shared chat, retrieval, and AI capabilities established earlier. It must not introduce duplicate AI or retrieval infrastructure.
