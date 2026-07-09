# StudyMate AI – System Architecture

This document defines the architectural blueprint for StudyMate AI. It describes how the system is structured, how its layers and modules interact, and the rules that govern all future development. The architecture defined here is authoritative and must not change without explicit approval.

---

# 1. Architecture Overview
StudyMate AI is a modular, AI-powered learning platform. It is designed as a unified system in which every learning capability is delivered through a shared platform foundation rather than as an isolated application. This ensures consistency in behavior, reuse of core capabilities, and a coherent experience across all learning modules.

A central architectural requirement is that every feature must integrate into the common platform. Modules such as PDF learning, YouTube learning, quiz generation, and academic search are not standalone products; they are extensions built on top of shared services including authentication, chat, retrieval, storage, and configuration.

The architecture is intentionally structured to support future expansion without major refactoring. New modules should plug into existing layers and services, inherit established patterns, and avoid introducing parallel or duplicated infrastructure. This keeps the platform maintainable, scalable, and consistent as it grows.

---

# 2. Architecture Principles
The following principles guide all architectural and design decisions across StudyMate AI.

- **Separation of Concerns** — Each layer and module has a clearly defined responsibility and does not absorb responsibilities that belong elsewhere.
- **Modular Design** — Capabilities are organized as independent modules that build on shared services.
- **Single Responsibility** — Each component addresses one concern, making the system easier to reason about and evolve.
- **Layered Architecture** — The system is organized into distinct layers with controlled, one-directional dependencies.
- **Reusable Services** — Common capabilities are implemented once as shared services and reused everywhere.
- **API First** — Interfaces are defined clearly and consistently before and independently of internal implementation details.
- **Security by Design** — Security is built into the architecture from the start rather than added later.
- **Scalability** — The structure supports growth in users, content, and modules without redesign.
- **Testability** — Components are designed so they can be verified independently and reliably.
- **Maintainability** — The architecture favors clarity, consistency, and low coupling to reduce long-term cost of change.

---

# 3. High Level Architecture
At a high level, a request flows through a series of well-defined layers, each with a clear responsibility.

```
User
 ↓
React Frontend
 ↓
FastAPI Backend
 ↓
Application Services
 ↓
AI Engine
 ↓
Vector Database
 ↓
Relational Database
 ↓
Response
```

**Layer responsibilities:**

- **User** — The learner who initiates actions such as uploading content, asking questions, or requesting study material.
- **React Frontend** — Presents the user interface, captures user intent, and communicates with the backend through a defined API surface. It contains no business logic.
- **FastAPI Backend** — Serves as the entry point for all client requests. It handles request routing, validation, authentication enforcement, and delegation to application services.
- **Application Services** — Encapsulate the platform's business logic and orchestrate operations across modules and shared services.
- **AI Engine** — Coordinates AI-related capabilities such as retrieval, prompt assembly, and language model interaction to produce grounded responses.
- **Vector Database** — Stores and serves semantic representations of content used for relevant context retrieval.
- **Relational Database** — Stores structured platform data such as users, sessions, chat history, and metadata.
- **Response** — The final result returned to the user, assembled from processed logic and AI output.

This layered flow ensures that responsibilities remain isolated and that dependencies move in a single, predictable direction.
## 3.1 Architecture Style

StudyMate AI follows a **Modular Monolith Architecture**.

### Why Modular Monolith?

- Faster development during MVP.
- Easier debugging.
- Simple deployment.
- Shared codebase.
- Lower operational complexity.
- Clear module boundaries.

Each module owns its business logic while sharing common platform services.

Modules communicate through internal service interfaces rather than direct dependencies.

Future migration to microservices should be possible without major redesign because module boundaries are preserved from the beginning.
---

# 4. Backend Architecture
The backend follows a strict Layered Architecture. Each layer depends only on the layer directly beneath it, and responsibilities are never mixed across layers.

```
Presentation Layer
 ↓
API Layer
 ↓
Service Layer
 ↓
AI/RAG Layer
 ↓
Repository Layer
 ↓
Database
```

**Layer responsibilities:**

- **Presentation Layer** — Defines the externally exposed request and response contracts. It is concerned with how data enters and leaves the backend, not with how operations are performed.
- **API Layer** — Contains the route definitions. Routes must remain thin: they validate input, enforce authentication, and delegate to the Service Layer. Routes contain no business logic.
- **Service Layer** — The single home for business logic. All orchestration, decision-making, and coordination between modules and shared services occur here.
- **AI/RAG Layer** — Encapsulates AI-specific workflows including retrieval, prompt construction, and language model interaction. It is invoked by services and never directly by routes.
- **Repository Layer** — The only layer permitted to access the database. It abstracts data access behind clear interfaces so higher layers remain storage-agnostic.
- **Database** — Persists structured platform data.

**Key rules:**

- Business logic must exist only inside the Service Layer.
- Routes must remain thin and delegate all meaningful work.
- Database access must occur exclusively through the Repository Layer.

---

# 5. Frontend Architecture
The frontend is organized into clearly separated responsibilities that mirror the platform's emphasis on layering and reuse.

```
Pages
 ↓
Components
 ↓
Services
 ↓
API Client
 ↓
Backend
```

**Layer responsibilities:**

- **Pages** — Represent complete views or screens. They compose components and coordinate the overall structure of a user-facing experience.
- **Components** — Reusable, focused UI building blocks responsible for presentation and local interaction. Components must never call backend APIs directly.
- **Services** — Encapsulate frontend-side application logic and act as the bridge between UI components and the API client.
- **API Client** — The single, centralized mechanism for communicating with the backend, applying consistent request handling and response processing.
- **Backend** — The server-side platform that fulfills requests.

**Key rule:** Components must never call backend APIs directly. All backend communication flows through services and the centralized API client, ensuring consistency and separation of concerns.

---

# 6. Module Architecture
Each module builds on shared platform capabilities and owns a clearly bounded responsibility.

| Module | Responsibility |
|---|---|
| Authentication | Manages user identity, access control, and session validity across the platform. |
| Dashboard | Presents a unified view of user activity, resources, statistics, and recent interactions. |
| PDF Learning | Enables interactive, question-based learning from uploaded PDF materials. |
| YouTube Learning | Enables structured learning from video content through transcript-based interaction. |
| Quiz Generator | Produces assessment content in multiple formats to reinforce understanding. |
| Notes Generator | Produces summaries, key points, and revision-oriented study notes. |
| Academic Search | Enables discovery, summarization, and citation of research material. |
| Shared AI Engine | Provides common AI capabilities such as retrieval, prompt assembly, and model interaction for all modules. |
| Shared Chat Engine | Provides a reusable conversational interaction layer used across learning modules. |
| Shared File Manager | Provides consistent handling of uploaded and temporary files for all modules. |

---

# 7. Shared Services
Shared services are reusable capabilities consumed by multiple modules. They exist once and are reused everywhere to prevent duplication and ensure consistent behavior.

- **Authentication Service** — Manages registration, login, session validation, and access control decisions consistently across the platform.
- **Chat Service** — Provides a reusable conversational interaction capability, including managing conversation context and history for learning modules.
- **Retrieval Service** — Retrieves the most relevant content context for a given query to support grounded AI responses.
- **Embedding Service** — Produces and manages semantic representations of content used by the retrieval process.
- **Storage Service** — Handles storage and lifecycle management of uploaded and temporary files in a consistent manner.
- **Quiz Service** — Encapsulates the logic for generating and structuring quizzes across formats and difficulty levels.
- **Notes Service** — Encapsulates the logic for generating summaries, key points, and revision notes.
- **Logging Service** — Provides consistent, centralized logging to support observability, diagnostics, and reliability.
- **Configuration Service** — Provides centralized access to configuration values and platform settings for all modules and services.
## 7.1 Shared AI Engine

The AI Engine is the central intelligence layer used by every AI-powered module.

Responsibilities include:

- Prompt Construction
- Retrieval Orchestration
- Context Assembly
- Model Invocation
- Response Validation
- Citation Generation
- Conversation Memory
- AI Configuration

The AI Engine must remain independent of any specific module.

Every module (PDF, YouTube, Quiz, Notes, Academic Search) consumes the AI Engine instead of implementing its own AI workflow.
---

# 8. RAG Pipeline
The Retrieval-Augmented Generation (RAG) pipeline defines how source content becomes grounded, cited responses.

```
Upload
 ↓
Validation
 ↓
Extraction
 ↓
Chunking
 ↓
Embedding
 ↓
Vector Storage
 ↓
Retrieval
 ↓
Prompt Assembly
 ↓
LLM
 ↓
Response
 ↓
Citation Generation
```

**Stage responsibilities:**

- **Upload** — Accepts source content submitted by the user for learning.
- **Validation** — Confirms the content is acceptable and safe to process before further steps.
- **Extraction** — Extracts usable textual content from the source material.
- **Chunking** — Divides extracted content into manageable, semantically coherent segments.
- **Embedding** — Converts chunks into semantic representations suitable for similarity-based retrieval.
- **Vector Storage** — Persists embeddings and their associated chunks for later retrieval.
- **Retrieval** — Selects the most relevant chunks in response to a user query.
- **Prompt Assembly** — Combines retrieved context with the user query into a structured prompt.
- **LLM** — Generates a response grounded in the assembled context.
- **Response** — Delivers the generated answer for return to the user.
- **Citation Generation** — Associates the response with its supporting source references to ensure transparency and verifiability.
## AI Pipeline Principles

Every AI request must follow these rules.

- AI answers must be grounded whenever source material exists.
- Hallucination should be minimized through retrieval.
- Citations should accompany grounded responses.
- Prompt construction must be centralized.
- LLM providers must be replaceable without affecting business logic.
- Embedding models must be configurable.
---

# 9. Data Flow
This section describes the lifecycle of a request as it moves through the platform.

**Question-answering flow:**

```
User asks question
 ↓
Backend validates request
 ↓
Retrieve relevant context
 ↓
Generate prompt
 ↓
LLM
 ↓
Return answer
```

- The user submits a question through the frontend.
- The backend validates the request and enforces authentication and input rules.
- The retrieval process gathers the most relevant context for the query.
- A structured prompt is generated from the query and retrieved context.
- The language model produces a grounded response.
- The answer is returned to the user, along with supporting citations where applicable.

**PDF processing flow (separate):**

```
User uploads PDF
 ↓
Backend validates file
 ↓
Content is extracted
 ↓
Content is chunked
 ↓
Chunks are embedded
 ↓
Embeddings are stored for retrieval
```

- The user uploads a PDF through the frontend.
- The backend validates the file before processing.
- Content is extracted, chunked, and embedded.
- The resulting embeddings and chunks are stored so the material becomes available for later question-answering.

These two flows are distinct: PDF processing prepares content for learning, while the question-answering flow consumes that prepared content to produce responses.

---

# 10. Data Storage Responsibilities
This section describes storage responsibilities only, not implementation details.

**Relational Database** stores:

- Users
- Sessions
- Chat History
- Metadata

**Vector Database** stores:

- Embeddings
- Chunks
- Semantic Index

**File Storage** stores:

- Uploaded PDFs
- Temporary Files

Each storage responsibility is isolated. Structured platform data, semantic representations, and raw files are managed distinctly so that each concern can evolve independently.
## Data Ownership

Each layer owns only its own data.

Frontend

- UI State

Backend

- Business Rules

Relational Database

- Structured Data

Vector Database

- Semantic Data

File Storage

- Original Documents

No layer may directly manipulate another layer's internal responsibilities.
---

# 11. API Design Principles
All platform interfaces adhere to consistent API design principles:

- **REST APIs** — Interfaces follow REST-oriented conventions for predictability and clarity.
- **Versioned APIs** — APIs are versioned to allow controlled evolution without breaking existing consumers.
- **Consistent responses** — Responses follow a consistent structure across the platform.
- **Centralized error handling** — Errors are handled consistently through a centralized approach.
- **Validation** — All inbound requests are validated before processing.
- **Authentication** — Protected interfaces enforce authentication consistently.
- **No business logic in routes** — Routes delegate to services and never contain business logic.

---

# 12. Folder Organization
The project is organized into clearly separated areas of responsibility. This section describes the intent of each area rather than an actual folder tree.

- **Backend** — Contains the layered server-side platform, including API, service, AI/RAG, and repository responsibilities. It exists to host all business logic and platform capabilities in a structured, maintainable form.
- **Frontend** — Contains the user-facing application organized into pages, components, services, and the API client. It exists to deliver a consistent and reusable user experience.
- **Docs** — Contains authoritative product and architecture documentation. It exists to preserve the single source of truth for vision, requirements, and architectural decisions.
- **Tests** — Contains verification assets across the platform. It exists to ensure correctness, reliability, and confidence in changes.
- **Shared Resources** — Contains cross-cutting assets and definitions reused across the platform. It exists to prevent duplication and promote consistency.

Separating these areas keeps concerns isolated, supports reuse, and makes the system easier to navigate and maintain.

---

# 13. Design Rules
The following rules are mandatory for all development on the platform:

- Never duplicate business logic.
- Never access the database from routes.
- Never call the LLM directly from controllers.
- Reuse existing services rather than reimplementing capabilities.
- Keep modules independent and loosely coupled.
- Prefer shared services first before creating new logic.
- Use dependency injection to manage component relationships.
- Use strong typing to improve safety and clarity.
## Dependency Rules

Allowed

Frontend
↓

API

↓

Service

↓

Repository

↓

Database

Not Allowed

Route → Database

Frontend → Database

Frontend → LLM

Repository → LLM

Controller → Repository + Business Logic
---

# 14. Extensibility
New modules must be added by building on the existing architecture rather than duplicating it. A new module should reuse the established shared capabilities instead of creating parallel implementations.

Future modules must reuse:

- Authentication
- Chat Engine
- Retrieval
- Storage
- Logging
- Configuration

By reusing these shared foundations, new modules inherit consistent behavior, reduce maintenance overhead, and integrate cleanly into the platform. Creating duplicate versions of these capabilities is not permitted.

---

# 15. Architecture Constraints
The following constraints protect the integrity of the architecture and must be upheld:

- No module-specific hacks.
- No tight coupling between modules or layers.
- No duplicated APIs.
- No circular dependencies.
- No business logic in the frontend.
- No direct database access outside repositories.

These constraints ensure the platform remains modular, predictable, and maintainable as it evolves.

---

# 16. Future Evolution
The architecture is designed so that future modules plug into the existing structure without requiring redesign. New capabilities should adopt the established layers, reuse shared services, and follow the defined design rules and constraints.

As long as future development respects this blueprint, the platform can expand in scope and capability while preserving consistency, stability, and long-term maintainability. This document remains the permanent architectural reference for StudyMate AI and must not be changed without explicit approval.
# 17. Architecture Decision Records

Major architectural decisions must be documented in the project's Decision Log.

Examples include:

- New shared services
- Database changes
- Authentication strategy
- AI model changes
- Retrieval strategy
- Vector database changes

No major architectural decision should be implemented without first updating the Decision Log.