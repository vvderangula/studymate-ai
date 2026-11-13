"""Repository for user accounts."""

from __future__ import annotations

from app.core.database import Collections
from app.models.user import User
from app.repositories.base import MongoRepository, as_utc


class UserRepository(MongoRepository):
    """The only component that reads or writes the ``users`` collection."""

    collection_name = Collections.USERS

    def create(self, user: User) -> None:
        """Insert a new user."""

        self.collection.insert_one(
            {
                "_id": user.id,
                "full_name": user.full_name,
                "email": user.email.lower(),
                "password_hash": user.password_hash,
                "created_at": user.created_at,
            }
        )

    def get(self, user_id: str) -> User | None:
        """Return the user with ``user_id``, or ``None``."""

        return _to_user(self.collection.find_one({"_id": user_id}))

    def get_by_email(self, email: str) -> User | None:
        """Return the user with ``email`` (case-insensitive), or ``None``."""

        return _to_user(self.collection.find_one({"email": email.lower()}))


def _to_user(doc: dict | None) -> User | None:
    if doc is None:
        return None
    return User(
        id=doc["_id"],
        full_name=doc["full_name"],
        email=doc["email"],
        password_hash=doc["password_hash"],
        created_at=as_utc(doc["created_at"]),
    )
