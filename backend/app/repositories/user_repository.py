"""Repository for persisting and retrieving user accounts."""

import sqlite3
from collections.abc import Callable
from datetime import datetime

from app.core.database import connect
from app.models.user import User


class UserRepository:
    """Data-access layer for the ``users`` table.

    This is the only component permitted to read from or write to the
    users table. A connection factory is injected to keep the repository
    testable against an isolated database.
    """

    def __init__(
        self,
        connection_factory: Callable[[], sqlite3.Connection] = connect,
    ) -> None:
        self._connect = connection_factory

    def create(self, user: User) -> None:
        """Insert a new user record."""

        connection = self._connect()
        try:
            connection.execute(
                """
                INSERT INTO users (id, full_name, email, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user.id,
                    user.full_name,
                    user.email,
                    user.password_hash,
                    user.created_at.isoformat(),
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def get(self, user_id: str) -> User | None:
        """Return the user with the given ``user_id``, or ``None``."""

        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT id, full_name, email, password_hash, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        finally:
            connection.close()

        return _row_to_user(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        """Return the user with the given ``email`` (case-insensitive), or ``None``."""

        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT id, full_name, email, password_hash, created_at FROM users WHERE email = ?",
                (email.lower(),),
            ).fetchone()
        finally:
            connection.close()

        return _row_to_user(row) if row else None


def _row_to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        full_name=row["full_name"],
        email=row["email"],
        password_hash=row["password_hash"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )
