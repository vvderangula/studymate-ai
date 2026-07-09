# AI_CONTEXT.md

This is a living project context document. It is not a requirements or architecture document. It represents the current memory and state of the StudyMate AI project and is updated continuously throughout development. Every AI coding session must read this file before making any change.

---

# Project Information

| Field | Value |
|---|---|
| Project Name | StudyMate AI |
| Current Version | v0.1.0 |
| Project Status | In Development |
| Current Milestone | Milestone 01 – Learn from PDF |
| Current Phase | Phase 4 – PDF Chat Experience (Frontend) |

---

# Project Goal
StudyMate AI aims to turn static study materials into an interactive learning experience, allowing learners to ask questions and receive clear, source-grounded explanations so they can understand content faster and study with more confidence.

---

# Technology Stack

**Frontend**

- React
- TypeScript
- Vite

**Backend**

- FastAPI
- Python

**Vector Database**

- ChromaDB

**Database**

- SQLite (MVP)
- PostgreSQL (Future)

**Authentication**

- JWT

**Architecture**

- Layered Architecture
- Modular Monolith
- REST API
- RAG

---

# Completed Documents

- [x] Project Vision
- [x] Product Requirements
- [x] System Architecture
- [x] Project Rules
- [x] AI Context
- [ ] Roadmap
- [ ] Decision Log
- [ ] Milestones

---

# Completed Features
- **Milestone 01 – Phase 1: PDF Upload & Storage** — PDF upload endpoint with type, size, and magic-byte validation; UUID generation; file storage; SQLite metadata persistence; and a frontend upload page with drag & drop, progress, and error handling.
- **Milestone 01 – Phase 2: PDF Processing Pipeline** — processing endpoint that extracts per-page text, normalizes whitespace, filters empty pages, chunks the text, and stores chunks as local JSON; extended metadata schema with status tracking and migration; failure handling for missing/corrupted/scanned PDFs; and a frontend flow that auto-processes after upload with progress, a completion summary, and retry.
- **Milestone 01 – Phase 3: Embeddings, Retrieval & Cited Chat** — reusable ChromaDB vector store service (add/update/search/count/delete); embedding generation for processed chunks with page/chunk-id citation metadata, a configurable provider, and skip-on-reindex; semantic retrieval with configurable top_k; a centralized RAG pipeline producing grounded answers with page citations; and a `POST /pdf/{id}/chat` endpoint returning answer, citations, and metadata with proper HTTP errors.
- **Milestone 01 – Phase 4: PDF Chat Experience (Frontend)** — redesigned chat interface (user/AI bubbles, auto-scroll, Enter-to-send, Shift+Enter newline, input disabled while generating); per-PDF conversation history with resume and clear; citation display with page badges and an expand/collapse sources panel; lightweight loading states (Uploading/Processing/Searching/Generating); friendly error and empty states; and UI polish for spacing, typography, and mobile responsiveness.

---

# Current Work
Milestone 01 is nearly complete. Phases 1 (PDF Upload & Storage), 2 (PDF Processing Pipeline), 3 (Embeddings, Retrieval & Cited Chat), and 4 (PDF Chat Experience) are complete. Authentication remains out of scope; server-side conversation history persistence is a future enhancement (history is currently persisted client-side).

---

# Upcoming Work

- Roadmap
- Decision Log
- Milestone 01
- Backend Implementation
- Frontend Implementation
- Testing
- Deployment

---

# Active Decisions
The following architectural decisions are currently in effect:

- Layered Architecture
- Modular Monolith
- Shared AI Engine
- Shared Services
- REST APIs
- JWT Authentication
- RAG Pipeline
- Open Source Models

---

# Coding Instructions for AI
Every AI assistant working on this project must:

- Read all documentation.
- Respect the architecture.
- Respect the project rules.
- Implement only the current milestone.
- Do not redesign existing modules.
- Do not modify unrelated code.
- Stop after the requested work is complete.

---

# Current Folder Structure
At a high level, the project is organized into the following areas:

- **Backend** — Layered server-side platform containing API, service, AI/RAG, and repository responsibilities.
- **Frontend** — User-facing application organized into pages, components, services, and a centralized API client.
- **Docs** — Authoritative product and engineering documentation serving as the single source of truth.
- **Tests** — Verification assets across the platform to ensure correctness and reliability.
- **Shared Resources** — Cross-cutting assets and definitions reused across the platform.

---

# Known Issues
Currently: None

---

# Technical Debt
Currently: None

---

# Next Immediate Task
Milestone 01 – acceptance verification and wrap-up, then planning the next milestone.

---
# Session Startup Checklist

Before starting any implementation session, every AI coding assistant must perform the following steps:

1. Read `AI_CONTEXT.md`.
2. Read `03_Project_Rules.md`.
3. Read the current milestone document.
4. If architecture changes are involved, read `02_System_Architecture.md`.
5. If requirements are involved, read `01_Product_Requirements.md`.
6. Understand the requested scope.
7. Implement only the requested scope.
8. Update documentation if required.
9. Stop after completing the requested work.
# Notes
This file must always represent the latest state of the project.

- Every completed milestone must update this document.
- Every major architectural decision must also update this document.
