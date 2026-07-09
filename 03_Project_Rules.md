# StudyMate AI – Project Rules

This document is the engineering constitution for the StudyMate AI project. It defines how development must happen and is mandatory for every contributor, whether human or AI. It must be read and understood before any implementation work begins.

---

# 1. Purpose
This document defines the mandatory engineering standards for StudyMate AI. Its purpose is to ensure that the project remains maintainable, scalable, secure, and consistent throughout its entire lifecycle.

These standards exist to protect the long-term health of the codebase. By establishing shared expectations for how development is performed, they reduce risk, improve collaboration, and ensure that every contribution strengthens the project rather than eroding its quality. Compliance with these rules is not optional; they apply equally to all contributors and to all modules.

---

# 2. Core Engineering Principles
The following principles form the foundation of all engineering work on StudyMate AI:

- **Readability over cleverness** — Code should be easy to understand. Clarity always takes priority over clever or obscure solutions.
- **Simplicity first** — Favor the simplest approach that correctly solves the problem. Avoid unnecessary complexity.
- **Reuse before creating new code** — Prefer existing services and utilities over writing new implementations.
- **Consistency across modules** — Follow shared patterns and conventions so the entire codebase feels coherent.
- **Security by default** — Treat security as a baseline requirement, not an afterthought.
- **Test everything** — Verify behavior with appropriate tests as a standard part of development.
- **Document important decisions** — Capture meaningful decisions so future contributors understand the reasoning.
- **Build for maintainability** — Optimize for the long-term cost of change, not just immediate delivery.

---

# 3. General Development Rules
The following rules apply to all development activity:

- Never bypass the architecture.
- Never duplicate logic.
- Never hardcode secrets.
- Never commit temporary debugging code.
- Never leave TODOs without issue references.
- Keep methods focused on a single responsibility.
- Prefer composition over duplication.
- Every feature must have defined acceptance criteria.

These rules preserve the integrity, security, and clarity of the codebase. Violations undermine maintainability and are not acceptable regardless of time pressure.

---

# 4. Backend Rules
Backend development must adhere to the following standards:

- Business logic must exist only in the Service Layer.
- Routes must remain thin and delegate to services.
- Database access must occur only through the Repository Layer.
- Dependencies must be provided through dependency injection.
- Strong typing must be used consistently.
- Exceptions must be handled through centralized exception handling.
- Inputs must be validated before processing.
- Asynchronous execution must be used where appropriate.

These rules keep the backend layered, predictable, and testable, and prevent responsibilities from leaking across boundaries.

---

# 5. Frontend Rules
Frontend development must adhere to the following standards:

- Components must remain presentational.
- Services must contain frontend business logic.
- Components must never make direct API calls.
- UI must be built from reusable elements.
- All backend communication must go through a centralized API client.
- State management must be consistent across the application.
- The interface must be responsive across screen sizes.
- Accessibility considerations must be respected.

These rules ensure a consistent, maintainable, and user-friendly frontend that mirrors the platform's emphasis on separation of concerns.

---

# 6. AI Development Rules
All AI-related development must adhere to the following standards:

- No direct LLM calls may occur outside the AI Engine.
- Prompt templates must be reusable.
- Retrieval must precede generation when applicable.
- AI responses should include citations when possible.
- AI configuration must remain centralized.
- AI providers must be replaceable without broad code changes.
- Development must actively minimize hallucinations.

These rules keep AI behavior consistent, trustworthy, and adaptable, and ensure the platform can evolve its AI capabilities without disruption.

---

# 7. Testing Rules
Testing is a mandatory part of development. The following categories of tests apply:

- **Unit Tests** — Verify individual components in isolation.
- **Integration Tests** — Verify that components work correctly together.
- **API Tests** — Verify that interfaces behave according to their contracts.
- **Frontend Tests** — Verify user-facing behavior and interactions.
- **Regression Tests** — Verify that existing behavior remains intact after changes.

**No feature is considered complete without appropriate tests.** Testing is not optional and must accompany the work it validates.

---

# 8. Documentation Rules
Documentation must be kept current as part of every feature. Every feature must update the following where relevant:

- **README** — When user-facing or setup-relevant behavior changes.
- **CHANGELOG** — To record notable changes.
- **Relevant milestone** — To reflect progress and scope.
- **API documentation** — When interfaces are added or changed.
- **Architecture** — Only if the architecture actually changes, and only with explicit approval.
- **Decision Log** — For architectural or significant technical decisions.

Documentation is part of the definition of a complete feature, not a separate afterthought.

---

# 9. Git Rules
Version control must follow these standards:

- Work must occur on feature branches.
- Commits must be small and focused.
- Commit messages must be meaningful and descriptive.
- Direct commits to the main branch are not permitted.
- Every feature must be reviewed before it is merged.

These rules keep history clean, changes traceable, and quality controlled through review.

---

# 10. Code Review Checklist
Every change must be evaluated against the following checklist before approval:

- [ ] Architecture is respected.
- [ ] Tests are added.
- [ ] Naming is consistent.
- [ ] No duplicated code is introduced.
- [ ] Error handling is present.
- [ ] Logging is added where appropriate.
- [ ] Validation is present.
- [ ] Documentation is updated.

A change that fails any applicable item on this checklist must not be merged until the issue is resolved.

---

# 11. Definition of Done
A task is complete only if all of the following are true:

- Requirements are satisfied.
- Acceptance criteria are satisfied.
- Tests are passing.
- Documentation is updated.
- No known critical bugs remain.
- Code has been reviewed.
- No TODOs are left behind.

Work that does not meet every applicable condition is not done, regardless of how functional it may appear.

---

# 12. AI Coding Assistant Rules
This section applies specifically to AI coding assistants working on StudyMate AI.

**Always read these documents before coding:**

- 00_Project_Vision.md
- 01_Product_Requirements.md
- 02_System_Architecture.md
- 03_Project_Rules.md
- AI_CONTEXT.md
- The current milestone

**Mandatory rules for AI assistants:**

- Never redesign the architecture.
- Implement only the requested milestone.
- Never modify unrelated modules.
- Ask for clarification instead of making assumptions.
- Update documentation after implementation.
- Stop after completing the requested scope.

These rules ensure AI contributions remain aligned with the project's vision, architecture, and standards, and prevent unintended or out-of-scope changes.

---

# 13. Project Quality Gates
Before any feature is merged, it must pass all of the following quality gates:

- **Functional Review** — The feature behaves as required.
- **Architecture Review** — The change respects the defined architecture.
- **Testing** — Appropriate tests exist and pass.
- **Documentation** — Relevant documentation is updated.
- **Performance** — The change meets performance expectations.
- **Security** — The change meets security expectations.
- **Code Review** — The change has been reviewed and approved.

A feature that fails any quality gate must not be merged until the gate is satisfied.

---

# 14. Engineering Philosophy
StudyMate AI values maintainability over speed, consistency over shortcuts, and long-term quality over quick fixes.

Every contribution should improve the project, not merely make it work. Contributors are expected to leave the codebase stronger, clearer, and more reliable than they found it. This philosophy is the spirit behind every rule in this document, and it must guide every engineering decision made on the project.
# 15. Change Management

To maintain project stability, every change must be classified before implementation.

## Change Types

### Minor Change

Examples

- Bug fix
- UI improvement
- Documentation update
- Small refactoring

Approval Required

No

---

### Feature Change

Examples

- New API
- New module capability
- New UI screen

Approval Required

Product Review

---

### Architectural Change

Examples

- Database redesign
- New shared service
- Authentication redesign
- AI pipeline redesign
- Module restructuring

Approval Required

Architecture Review

Decision Log Update

Documentation Update

---

No architectural change may be implemented without updating:

- Decision Log
- System Architecture
- AI Context