"""SQLite database connection and schema initialization.

Provides the low-level connection factory used by the repository layer.
Higher layers must access persistence only through repositories, never
through this module directly.
"""

import sqlite3
from pathlib import Path

from app.core.config import settings

_CREATE_PDF_DOCUMENTS = """
CREATE TABLE IF NOT EXISTS pdf_documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    original_name TEXT NOT NULL,
    size INTEGER NOT NULL,
    upload_time TEXT NOT NULL,
    status TEXT NOT NULL,
    user_id TEXT,
    processing_status TEXT NOT NULL DEFAULT 'pending',
    processed_at TEXT,
    page_count INTEGER,
    chunk_count INTEGER
)
"""

# Columns added after the initial schema, applied to existing databases.
_PDF_DOCUMENTS_ADDED_COLUMNS = {
    "processing_status": "TEXT NOT NULL DEFAULT 'pending'",
    "processed_at": "TEXT",
    "page_count": "INTEGER",
    "chunk_count": "INTEGER",
}

_CREATE_YOUTUBE_VIDEOS = """
CREATE TABLE IF NOT EXISTS youtube_videos (
    video_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    duration INTEGER,
    thumbnail TEXT,
    created_at TEXT,
    user_id TEXT,
    processing_status TEXT NOT NULL DEFAULT 'pending',
    processed_at TEXT,
    chunk_count INTEGER
)
"""

_YOUTUBE_VIDEOS_ADDED_COLUMNS = {
    "user_id": "TEXT",
}

_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

_CREATE_ACTIVITY_LOG = """
CREATE TABLE IF NOT EXISTS activity_log (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resource_id TEXT,
    resource_title TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
"""


def connect() -> sqlite3.Connection:
    """Open a SQLite connection to the configured database file.

    The parent directory is created if it does not yet exist. Rows are
    returned as ``sqlite3.Row`` for name-based access.
    """

    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """Create database tables and apply column migrations if needed."""

    connection = connect()
    try:
        connection.execute(_CREATE_USERS)
        connection.execute(_CREATE_ACTIVITY_LOG)
        connection.execute(_CREATE_PDF_DOCUMENTS)
        _migrate_pdf_documents(connection)
        connection.execute(_CREATE_YOUTUBE_VIDEOS)
        _migrate_youtube_videos(connection)
        connection.commit()
    finally:
        connection.close()


def _migrate_pdf_documents(connection: sqlite3.Connection) -> None:
    """Add any missing ``pdf_documents`` columns to an existing table."""

    existing = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(pdf_documents)")
    }
    for column, ddl in _PDF_DOCUMENTS_ADDED_COLUMNS.items():
        if column not in existing:
            connection.execute(
                f"ALTER TABLE pdf_documents ADD COLUMN {column} {ddl}"
            )


def _migrate_youtube_videos(connection: sqlite3.Connection) -> None:
    """Add any missing ``youtube_videos`` columns to an existing table."""

    existing = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(youtube_videos)")
    }
    for column, ddl in _YOUTUBE_VIDEOS_ADDED_COLUMNS.items():
        if column not in existing:
            connection.execute(
                f"ALTER TABLE youtube_videos ADD COLUMN {column} {ddl}"
            )
