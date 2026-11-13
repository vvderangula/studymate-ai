"""One-off copy of the old SQLite data (and chunk JSON files) into MongoDB.

Run from backend/:  python -m scripts.migrate_sqlite_to_mongo [--dry-run]

Idempotent: records are upserted by id, so running it twice is harmless.
Accounts created by the test suite (anything @example.com)
are skipped, along with everything they own.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.core.database import Collections, get_db, init_db

SQLITE_PATH = Path("storage/studymate.db")
CHUNKS_DIR = Path("storage/chunks")
_TEST_EMAIL = re.compile(r"@example\.com$")  # every test-suite sign-up uses example.com


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def migrate(dry_run: bool) -> None:
    if not SQLITE_PATH.is_file():
        print(f"No SQLite database at {SQLITE_PATH}; nothing to migrate.")
        return

    sql = sqlite3.connect(SQLITE_PATH)
    sql.row_factory = sqlite3.Row
    db = get_db()
    init_db()

    users = [row for row in sql.execute("SELECT * FROM users") if not _TEST_EMAIL.search(row["email"])]
    keep = {row["id"] for row in users}
    pdfs = [row for row in sql.execute("SELECT * FROM pdf_documents") if row["user_id"] in keep]
    videos = [row for row in sql.execute("SELECT * FROM youtube_videos") if row["user_id"] in keep]
    activity = [row for row in sql.execute("SELECT * FROM activity_log") if row["user_id"] in keep]
    sources = [row["id"] for row in pdfs] + [row["video_id"] for row in videos]

    print(f"users {len(users)}, pdfs {len(pdfs)}, videos {len(videos)}, activity {len(activity)}")
    if dry_run:
        print("Dry run: nothing written.")
        return

    for row in users:
        db[Collections.USERS].update_one(
            {"_id": row["id"]},
            {"$set": {
                "full_name": row["full_name"],
                "email": row["email"].lower(),
                "password_hash": row["password_hash"],
                "created_at": _dt(row["created_at"]),
            }},
            upsert=True,
        )

    for row in pdfs:
        db[Collections.PDFS].update_one(
            {"_id": row["id"]},
            {"$set": {
                "filename": row["filename"],
                "original_name": row["original_name"],
                "size": row["size"],
                "upload_time": _dt(row["upload_time"]),
                "status": row["status"],
                "user_id": row["user_id"],
                "processing_status": row["processing_status"],
                "processed_at": _dt(row["processed_at"]),
                "page_count": row["page_count"],
                "chunk_count": row["chunk_count"],
            }},
            upsert=True,
        )

    for row in videos:
        db[Collections.VIDEOS].update_one(
            {"user_id": row["user_id"], "video_id": row["video_id"]},
            {"$set": {
                "url": row["url"],
                "title": row["title"],
                "duration": row["duration"],
                "thumbnail": row["thumbnail"],
                "created_at": _dt(row["created_at"]),
                "processing_status": row["processing_status"],
                "processed_at": _dt(row["processed_at"]),
                "chunk_count": row["chunk_count"],
            }},
            upsert=True,
        )

    for row in activity:
        db[Collections.ACTIVITY].update_one(
            {"_id": row["id"]},
            {"$set": {
                "user_id": row["user_id"],
                "event_type": row["event_type"],
                "resource_id": row["resource_id"],
                "resource_title": row["resource_title"],
                "created_at": _dt(row["created_at"]),
            }},
            upsert=True,
        )

    copied = 0
    for source_id in sources:
        path = CHUNKS_DIR / f"{source_id}.json"
        if not path.is_file():
            continue
        chunks = json.loads(path.read_text(encoding="utf-8"))
        db[Collections.CHUNKS].delete_many({"source_id": source_id})
        if chunks:
            db[Collections.CHUNKS].insert_many(
                [{"source_id": source_id, "index": i, "text": text} for i, text in enumerate(chunks)]
            )
            copied += 1
    print(f"chunk sets copied: {copied}")
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="count only, write nothing")
    migrate(parser.parse_args().dry_run)
