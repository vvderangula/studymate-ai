"""Service that aggregates user learning analytics for the dashboard."""

from app.models.user import User
from app.repositories.activity_repository import ActivityRepository
from app.schemas.dashboard import (
    ActivityItem,
    ContinueItem,
    DashboardResponse,
    InsightItem,
    StatCard,
)

# Maps event_type to its display module name.
_MODULE_MAP: dict[str, str] = {
    "pdf_uploaded": "Learn from PDF",
    "pdf_chat": "Learn from PDF",
    "youtube_processed": "Learn from YouTube",
    "youtube_chat": "Learn from YouTube",
    "quiz_generated": "AI Study Tools",
    "notes_generated": "AI Study Tools",
    "assistant_chat": "AI Assistant",
    "research_search": "Research Assistant",
    "research_asked": "Research Assistant",
}

_EVENT_LABELS: dict[str, str] = {
    "pdf_uploaded": "Uploaded a PDF",
    "pdf_chat": "Asked about a PDF",
    "youtube_processed": "Processed a YouTube video",
    "youtube_chat": "Asked about a YouTube video",
    "quiz_generated": "Generated a quiz",
    "notes_generated": "Generated study notes",
    "assistant_chat": "Used AI Assistant",
    "research_search": "Searched research papers",
    "research_asked": "Asked about a research paper",
}

_MOTIVATIONAL_MESSAGES = [
    "Keep pushing — every session brings you closer to mastery.",
    "Great learners are made one question at a time.",
    "Your curiosity is your superpower.",
    "Every study session is an investment in your future.",
]


class DashboardService:
    """Computes dashboard data from user activity and metadata."""

    def __init__(self, activity_repo: ActivityRepository) -> None:
        self._activity = activity_repo

    def build(self, user: User) -> DashboardResponse:
        counts = self._activity.count_by_event_types(user.id)
        recent = self._activity.get_recent(user.id, limit=15)
        study_days = self._activity.count_distinct_days(user.id)

        # --- Stats cards ---
        stats = [
            StatCard(label="PDFs Studied", value=counts.get("pdf_uploaded", 0)),
            StatCard(label="YouTube Videos", value=counts.get("youtube_processed", 0)),
            StatCard(label="AI Chats", value=counts.get("assistant_chat", 0)),
            StatCard(label="Research Papers", value=counts.get("research_search", 0)),
            StatCard(label="Quizzes Generated", value=counts.get("quiz_generated", 0)),
            StatCard(label="Notes Generated", value=counts.get("notes_generated", 0)),
        ]

        # --- Insights ---
        total_questions = sum(
            counts.get(t, 0)
            for t in ("pdf_chat", "youtube_chat", "assistant_chat", "research_asked")
        )

        # Most used module
        module_totals: dict[str, int] = {}
        for event_type, cnt in counts.items():
            module = _MODULE_MAP.get(event_type)
            if module:
                module_totals[module] = module_totals.get(module, 0) + cnt
        most_used_module = (
            max(module_totals, key=lambda m: module_totals[m])
            if module_totals
            else "None yet"
        )

        # Most used method (single event type)
        fav_event = max(counts, key=lambda t: counts[t]) if counts else None
        fav_method = _EVENT_LABELS.get(fav_event, "None yet") if fav_event else "None yet"

        # Recently active module
        recently_active = "None yet"
        if recent:
            recently_active = _MODULE_MAP.get(recent[0].event_type, "Unknown")

        insights = [
            InsightItem(label="Total Questions Asked", value=str(total_questions)),
            InsightItem(label="Total Study Days", value=str(study_days)),
            InsightItem(label="Most Used Module", value=most_used_module),
            InsightItem(label="Favorite Study Method", value=fav_method),
            InsightItem(label="Recently Active Module", value=recently_active),
        ]

        # --- Continue Learning ---
        continue_learning: list[ContinueItem] = []

        last_pdf = self._activity.get_latest_by_event_type(user.id, "pdf_uploaded")
        if last_pdf and last_pdf.resource_id:
            continue_learning.append(
                ContinueItem(
                    resource_type="pdf",
                    resource_id=last_pdf.resource_id,
                    title=last_pdf.resource_title or "Untitled PDF",
                    last_accessed=last_pdf.created_at.isoformat(),
                )
            )

        last_video = self._activity.get_latest_by_event_type(user.id, "youtube_processed")
        if last_video and last_video.resource_id:
            continue_learning.append(
                ContinueItem(
                    resource_type="youtube",
                    resource_id=last_video.resource_id,
                    title=last_video.resource_title or "Untitled Video",
                    last_accessed=last_video.created_at.isoformat(),
                )
            )

        last_paper = self._activity.get_latest_by_event_type(user.id, "research_search")
        if last_paper:
            continue_learning.append(
                ContinueItem(
                    resource_type="research",
                    resource_id=last_paper.resource_id or "search",
                    title=last_paper.resource_title or "Research Search",
                    last_accessed=last_paper.created_at.isoformat(),
                )
            )

        # --- Recent activity (last 10) ---
        activity_items = [
            ActivityItem(
                event_type=entry.event_type,
                description=_build_description(entry.event_type, entry.resource_title),
                created_at=entry.created_at.isoformat(),
            )
            for entry in recent[:10]
        ]

        return DashboardResponse(
            user_name=user.full_name,
            stats=stats,
            insights=insights,
            continue_learning=continue_learning,
            recent_activity=activity_items,
        )


def _build_description(event_type: str, resource_title: str | None) -> str:
    base = _EVENT_LABELS.get(event_type, event_type)
    if resource_title:
        return f"{base}: {resource_title}"
    return base
