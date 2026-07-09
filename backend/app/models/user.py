"""Domain model for an authenticated user."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    """A registered StudyMate AI user.

    Attributes:
        id: Unique identifier (UUID hex).
        full_name: Display name provided at registration.
        email: Unique email address (stored lowercase).
        password_hash: bcrypt hash of the user's password.
        created_at: Timestamp when the account was created.
    """

    id: str
    full_name: str
    email: str
    password_hash: str
    created_at: datetime
