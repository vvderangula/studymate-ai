# Milestone 03 – AI Quiz Generator

## Objective
Provide learners with assessment-oriented practice by generating quizzes from their study content. This milestone reinforces understanding and enables self-evaluation across supported learning sources.

## Scope
- Quiz generation from selected learning content.
- Support for multiple-choice (MCQ), True/False, and Short Answer formats.
- Difficulty level selection.
- Answer explanations for generated questions.

## Out of Scope
- Grading or scoring records tied to formal academic outcomes.
- Timed examinations or proctoring features.
- Collaborative or shared quiz sessions.
- Learning-source ingestion (handled by other milestones).

## User Stories
- As a student, I want quizzes generated from my study content, so that I can test my understanding.
- As a student, I want MCQ quizzes, so that I can practice exam-style objective questions.
- As a student, I want True/False questions, so that I can quickly assess core conceptual clarity.
- As a student, I want short-answer questions, so that I can improve descriptive recall.
- As a student, I want to choose quiz difficulty, so that practice matches my preparation level.
- As a student, I want answer explanations, so that I can learn from mistakes.

## Functional Requirements
- The system shall generate quizzes from selected learning content.
- The system shall support multiple-choice question (MCQ) format.
- The system shall support True/False question format.
- The system shall support Short Answer question format.
- The system shall allow users to select quiz difficulty level.
- The system shall provide answer explanations for generated questions.

## Non Functional Requirements
- Quiz generation should complete within acceptable response times.
- The interface must remain responsive during generation.
- Inputs must be validated before processing.
- Failures must be handled gracefully with clear feedback.
- Generated content must be produced consistently across formats.

## Dependencies
- Authentication (Milestone 06) for user-scoped access.
- Shared AI Engine and Quiz Service.
- Availability of learning content from prior milestones.

## Deliverables
- Quiz generation capability across supported formats.
- Difficulty selection capability.
- Answer explanations.
- Associated tests for the module.

## Phase Breakdown
- Phase A: Content selection and quiz request handling.
- Phase B: MCQ and True/False generation.
- Phase C: Short Answer generation and difficulty handling.
- Phase D: Answer explanations.
- Phase E: Testing and acceptance verification.

## Acceptance Criteria
- A user can generate a quiz from selected learning material.
- Quiz output includes MCQ, True/False, and Short Answer formats.
- A user can choose at least one difficulty level before generation.
- Every quiz question includes a corresponding correct answer.
- Answer explanations are available for generated questions.

## Definition of Done
- Requirements are satisfied.
- Acceptance criteria are satisfied.
- Tests are passing.
- Documentation is updated.
- No known critical bugs remain.
- Code has been reviewed.
- No TODOs are left behind.

## Risks
- Generated questions may vary in quality and require validation.
- Difficulty calibration may be inconsistent across topics.
- Content coverage gaps may limit quiz breadth.

## Notes
This milestone must build on the shared AI Engine and consume existing learning content. It must not introduce direct LLM access outside the AI Engine.
