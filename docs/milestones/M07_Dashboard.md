# Milestone 07 – Dashboard

## Objective
Provide a central view of user learning activity and progress. This milestone gives users visibility into their resources, recent interactions, and study statistics, and is part of the MVP as a basic dashboard.

## Scope
- Display of recent user activity.
- Display of uploaded learning resources.
- Display of learning statistics relevant to user progress.
- Display of recent chat interactions.

## Out of Scope
- Advanced learning analytics and predictive insights.
- Customizable dashboard layouts and widgets.
- Cross-user or organizational reporting.
- Data export features.

## User Stories
- As a user, I want to see my recent activity, so that I can quickly resume studying.
- As a user, I want to see my uploaded resources, so that I can access them easily.
- As a user, I want to see my learning statistics, so that I can track my progress.
- As a user, I want to see my recent chats, so that I can continue previous sessions.

## Functional Requirements
- The system shall display recent user activity.
- The system shall display uploaded learning resources.
- The system shall display learning statistics relevant to user progress.
- The system shall display recent chat interactions.

## Non Functional Requirements
- Dashboard content should load with low latency.
- The interface must remain responsive across screen sizes.
- Displayed data must be presented in an understandable format.
- Failures must be handled gracefully with clear feedback.
- Only authorized user data must be shown to each user.

## Dependencies
- Authentication (Milestone 06) for user-scoped data.
- Learning modules that generate activity, resources, and chats.
- Shared services for retrieving user-scoped information.

## Deliverables
- Recent activity view.
- Uploaded resources view.
- Learning statistics view.
- Recent chats view.
- Associated tests for the module.

## Phase Breakdown
- Phase A: Recent activity display.
- Phase B: Uploaded resources display.
- Phase C: Learning statistics display.
- Phase D: Recent chats display.
- Phase E: Testing and acceptance verification.

## Acceptance Criteria
- Recent activity is visible to the user in the dashboard view.
- Uploaded resources are listed in dashboard context.
- Learning statistics are shown in an understandable format.
- Recent chats are accessible from the dashboard.

## Definition of Done
- Requirements are satisfied.
- Acceptance criteria are satisfied.
- Tests are passing.
- Documentation is updated.
- No known critical bugs remain.
- Code has been reviewed.
- No TODOs are left behind.

## Risks
- Aggregating data from multiple modules may introduce consistency challenges.
- Statistics may be limited by the availability of underlying data.
- Displaying stale data could reduce user trust if not handled carefully.

## Notes
The basic dashboard is part of the MVP. It must present only authorized, user-scoped data and reuse shared services rather than duplicating data-access logic.
