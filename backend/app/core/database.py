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
    processing_status TEXT NOT NULL DEFAULT 'pending',
    processed_at TEXT,
    chunk_count INTEGER
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
        connection.execute(_CREATE_PDF_DOCUMENTS)
        _migrate_pdf_documents(connection)
        connection.execute(_CREATE_YOUTUBE_VIDEOS)
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
