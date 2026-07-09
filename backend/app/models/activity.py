"""Domain model for a user activity event."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ActivityEntry:
    """A single user activity event for dashboard analytics.

    Attributes:
        id: Unique identifier (UUID hex).
        user_id: Owning user's identifier.
        event_type: Category of activity (e.g. ``pdf_uploaded``).
        created_at: Timestamp of the event.
        resource_id: Optional identifier of the related resource.
        resource_title: Optional human-readable title of the resource.
    """

    id: str
    user_id: str
    event_type: str
    created_at: datetime
    resource_id: str | None = None
    resource_title: str | None = None
