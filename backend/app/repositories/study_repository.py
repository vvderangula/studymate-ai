"""Repositories for saved quizzes and notes."""

from __future__ import annotations

import uuid

from pymongo import DESCENDING

from app.core.database import Collections
from app.models.study import SavedNote, SavedQuiz
from app.repositories.base import MongoRepository, as_utc, utcnow


class QuizRepository(MongoRepository):
    """The only component that reads or writes ``quizzes``."""

    collection_name = Collections.QUIZZES

    def save(
        self,
        *,
        user_id: str,
        source_type: str,
        source_id: str,
        source_title: str,
        question_type: str,
        difficulty: str,
        count: int,
        questions: list[dict],
    ) -> SavedQuiz:
        doc = {
            "_id": uuid.uuid4().hex,
            "user_id": user_id,
            "source_type": source_type,
            "source_id": source_id,
            "source_title": source_title,
            "question_type": question_type,
            "difficulty": difficulty,
            "count": count,
            "questions": questions,
            "created_at": utcnow(),
        }
        self.collection.insert_one(doc)
        return _to_quiz(doc)

    def list(self, user_id: str, limit: int = 50) -> list[SavedQuiz]:
        cursor = self.collection.find({"user_id": user_id}).sort("created_at", DESCENDING).limit(limit)
        return [_to_quiz(doc) for doc in cursor]

    def get(self, quiz_id: str, user_id: str) -> SavedQuiz | None:
        doc = self.collection.find_one({"_id": quiz_id, "user_id": user_id})
        return _to_quiz(doc) if doc else None

    def delete(self, quiz_id: str, user_id: str) -> bool:
        return bool(self.collection.delete_one({"_id": quiz_id, "user_id": user_id}).deleted_count)

    def count(self) -> int:
        return self.collection.count_documents({})


class NoteRepository(MongoRepository):
    """The only component that reads or writes ``notes``."""

    collection_name = Collections.NOTES

    def save(
        self,
        *,
        user_id: str,
        source_type: str,
        source_id: str,
        source_title: str,
        note_type: str,
        content: str,
    ) -> SavedNote:
        doc = {
            "_id": uuid.uuid4().hex,
            "user_id": user_id,
            "source_type": source_type,
            "source_id": source_id,
            "source_title": source_title,
            "note_type": note_type,
            "content": content,
            "created_at": utcnow(),
        }
        self.collection.insert_one(doc)
        return _to_note(doc)

    def list(self, user_id: str, limit: int = 50) -> list[SavedNote]:
        cursor = self.collection.find({"user_id": user_id}).sort("created_at", DESCENDING).limit(limit)
        return [_to_note(doc) for doc in cursor]

    def get(self, note_id: str, user_id: str) -> SavedNote | None:
        doc = self.collection.find_one({"_id": note_id, "user_id": user_id})
        return _to_note(doc) if doc else None

    def delete(self, note_id: str, user_id: str) -> bool:
        return bool(self.collection.delete_one({"_id": note_id, "user_id": user_id}).deleted_count)

    def count(self) -> int:
        return self.collection.count_documents({})


def _to_quiz(doc: dict) -> SavedQuiz:
    return SavedQuiz(
        id=doc["_id"],
        user_id=doc["user_id"],
        source_type=doc["source_type"],
        source_id=doc["source_id"],
        source_title=doc.get("source_title", ""),
        question_type=doc["question_type"],
        difficulty=doc["difficulty"],
        count=doc.get("count", len(doc.get("questions", []))),
        created_at=as_utc(doc["created_at"]),
        questions=doc.get("questions", []),
    )


def _to_note(doc: dict) -> SavedNote:
    return SavedNote(
        id=doc["_id"],
        user_id=doc["user_id"],
        source_type=doc["source_type"],
        source_id=doc["source_id"],
        source_title=doc.get("source_title", ""),
        note_type=doc["note_type"],
        content=doc["content"],
        created_at=as_utc(doc["created_at"]),
    )
