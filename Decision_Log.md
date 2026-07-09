# StudyMate AI – Decision Log

## Purpose
This document records all major engineering and architectural decisions made throughout the StudyMate AI project. It serves as the authoritative history of why the system is built the way it is. Each decision is captured as an Architectural Decision Record (ADR) with consistent fields so that current and future contributors can understand the reasoning behind every significant choice.

Each decision contains the following fields:

- **Decision ID**
- **Date**
- **Status**
- **Decision**
- **Context**
- **Alternatives Considered**
- **Reason**
- **Impact**

---

## ADR-001 — Use Modular Monolith

| Field | Detail |
|---|---|
| Decision ID | ADR-001 |
| Date | 2026-07-10 |
| Status | Accepted |
| Decision | Adopt a modular monolith as the overall system structure. |

**Context:** StudyMate AI is an early-stage platform with multiple planned modules that must share common capabilities. The team needs a structure that supports fast, coordinated development while keeping modules well organized.

**Alternatives Considered:** Microservices architecture; multiple independent applications.

**Reason:** A modular monolith provides clear module boundaries and reuse of shared services without the operational overhead and complexity of distributed systems at this stage. It supports coherent development and a unified platform experience.

**Impact:** All modules live within a single, well-structured application and reuse shared services. Future extraction into separate services remains possible if scale demands it.

---

## ADR-002 — Use Layered Architecture

| Field | Detail |
|---|---|
| Decision ID | ADR-002 |
| Date | 2026-07-10 |
| Status | Accepted |
| Decision | Organize the backend using a strict layered architecture. |

**Context:** The platform requires clear separation of responsibilities to remain maintainable and testable as modules grow.

**Alternatives Considered:** Unstructured/ad-hoc organization; fully event-driven architecture.

**Reason:** Layered architecture enforces separation of concerns, keeps business logic isolated in the service layer, and ensures predictable, one-directional dependencies.

**Impact:** Routes remain thin, business logic is centralized in services, and database access is confined to repositories. This improves consistency, testability, and long-term maintainability.

---

## ADR-003 — Use React + FastAPI

| Field | Detail |
|---|---|
| Decision ID | ADR-003 |
| Date | 2026-07-10 |
| Status | Accepted |
| Decision | Use React for the frontend and FastAPI for the backend. |

**Context:** The platform needs a responsive, modern user interface and a capable backend suitable for AI-oriented workloads and clear API design.

**Alternatives Considered:** Alternative frontend frameworks; alternative backend frameworks.

**Reason:** React provides a robust, component-based frontend model, while FastAPI supports clear, well-typed API development that aligns with the platform's API-first and layered principles.

**Impact:** Establishes the core frontend and backend foundations, with a centralized API client bridging the two.

---

## ADR-004 — Use ChromaDB for Vector Storage

| Field | Detail |
|---|---|
| Decision ID | ADR-004 |
| Date | 2026-07-10 |
| Status | Accepted |
| Decision | Use ChromaDB as the vector storage solution. |

**Context:** The RAG pipeline requires semantic storage and retrieval of content embeddings to support grounded responses.

**Alternatives Considered:** Other vector database solutions; custom similarity storage.

**Reason:** ChromaDB provides a straightforward, capable vector storage option well suited to the platform's retrieval needs during early development.

**Impact:** Embeddings, chunks, and the semantic index are managed in ChromaDB, supporting the retrieval stage of the RAG pipeline.

---

## ADR-005 — Use SQLite for MVP

| Field | Detail |
|---|---|
| Decision ID | ADR-005 |
| Date | 2026-07-10 |
| Status | Accepted |
| Decision | Use SQLite as the relational database for the MVP. |

**Context:** The MVP requires structured storage for users, sessions, chat history, and metadata with minimal setup overhead.

**Alternatives Considered:** PostgreSQL from the outset; other relational databases.

**Reason:** SQLite offers simplicity and low operational overhead for the MVP while keeping a clear path to migrate to PostgreSQL as scale increases.

**Impact:** MVP relational storage runs on SQLite. A future migration to PostgreSQL is anticipated and must follow the decision-recording process.

---

## ADR-006 — Use JWT Authentication

| Field | Detail |
|---|---|
| Decision ID | ADR-006 |
| Date | 2026-07-10 |
| Status | Accepted |
| Decision | Use JWT-based authentication for user identity and access control. |

**Context:** The platform requires secure, stateless authentication that integrates cleanly with the API-first backend.

**Alternatives Considered:** Server-side session-based authentication; third-party-only identity providers.

**Reason:** JWT supports stateless, scalable authentication that fits the platform's REST and layered design and enables consistent access control across modules.

**Impact:** Authentication is handled through JWT via the shared Authentication Service and enforced consistently on protected interfaces.

---

## ADR-007 — Use RAG Architecture

| Field | Detail |
|---|---|
| Decision ID | ADR-007 |
| Date | 2026-07-10 |
| Status | Accepted |
| Decision | Use a Retrieval-Augmented Generation (RAG) architecture for AI responses. |

**Context:** Users need trustworthy, source-grounded answers rather than ungrounded AI output.

**Alternatives Considered:** Direct LLM generation without retrieval; static answer templates.

**Reason:** RAG grounds responses in relevant source content and enables citations, improving accuracy and trust while reducing hallucinations.

**Impact:** AI responses flow through the defined RAG pipeline, and citations are produced where applicable.

---

## ADR-008 — Use Shared AI Engine

| Field | Detail |
|---|---|
| Decision ID | ADR-008 |
| Date | 2026-07-10 |
| Status | Accepted |
| Decision | Provide AI capabilities through a shared AI Engine used by all modules. |

**Context:** Multiple modules require AI capabilities such as retrieval, prompt assembly, and model interaction.

**Alternatives Considered:** Per-module AI implementations; direct LLM calls from individual modules.

**Reason:** A shared AI Engine prevents duplication, centralizes AI configuration, and ensures consistent, replaceable AI behavior across the platform.

**Impact:** No direct LLM calls occur outside the AI Engine; all modules consume AI capabilities through this shared component.

---

## ADR-009 — Use Shared Services

| Field | Detail |
|---|---|
| Decision ID | ADR-009 |
| Date | 2026-07-10 |
| Status | Accepted |
| Decision | Implement common capabilities as reusable shared services. |

**Context:** Modules repeatedly require capabilities such as authentication, chat, retrieval, storage, logging, and configuration.

**Alternatives Considered:** Duplicating capabilities within each module.

**Reason:** Shared services eliminate duplication, ensure consistent behavior, and reduce maintenance cost as the platform grows.

**Impact:** Modules build on shared services rather than reimplementing capabilities. Duplicate implementations of shared capabilities are not permitted.

---

## ADR-010 — Use Open Source AI Models

| Field | Detail |
|---|---|
| Decision ID | ADR-010 |
| Date | 2026-07-10 |
| Status | Accepted |
| Decision | Use open source AI models for the platform's AI capabilities. |

**Context:** The platform values flexibility, transparency, and cost control in its AI capabilities.

**Alternatives Considered:** Proprietary, closed AI providers only.

**Reason:** Open source models support the platform's open-source-friendly principle, provide flexibility, and align with the requirement that AI providers remain replaceable.

**Impact:** AI capabilities are built to work with open source models through the shared AI Engine, keeping providers interchangeable.

---

## Decision Log Rules

- Every architectural decision must be recorded here before implementation.
- No architectural change is allowed without updating this document.
