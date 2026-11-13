"""Repository for conversations and their messages."""

from __future__ import annotations

import uuid

from pymongo import ASCENDING, DESCENDING

from app.core.database import Collections, get_db
from app.models.conversation import Conversation, Message
from app.repositories.base import MongoRepository, as_utc, utcnow

_PREVIEW_CHARS = 160


class ConversationRepository(MongoRepository):
    """The only component that reads or writes ``conversations`` and ``messages``."""

    collection_name = Collections.CONVERSATIONS

    @property
    def messages_collection(self):
        return (self._db if self._db is not None else get_db())[Collections.MESSAGES]

    # -- conversations ---------------------------------------------------
    def create(
        self, user_id: str, kind: str, title: str, source_id: str | None = None
    ) -> Conversation:
        now = utcnow()
        doc = {
            "_id": uuid.uuid4().hex,
            "user_id": user_id,
            "kind": kind,
            "source_id": source_id,
            "title": title.strip()[:200] or "Untitled",
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "preview": "",
        }
        self.collection.insert_one(doc)
        return _to_conversation(doc)

    def find_for_source(self, user_id: str, kind: str, source_id: str) -> Conversation | None:
        """The conversation about one source (PDF, video, paper), if any."""

        return _to_conversation(
            self.collection.find_one({"user_id": user_id, "kind": kind, "source_id": source_id})
        )

    def get_or_create_for_source(
        self, user_id: str, kind: str, source_id: str, title: str
    ) -> Conversation:
        existing = self.find_for_source(user_id, kind, source_id)
        return existing or self.create(user_id, kind, title, source_id=source_id)

    def get(self, conversation_id: str, user_id: str) -> Conversation | None:
        """A conversation, only if ``user_id`` owns it."""

        return _to_conversation(
            self.collection.find_one({"_id": conversation_id, "user_id": user_id})
        )

    def list(self, user_id: str, kind: str, limit: int = 50) -> list[Conversation]:
        """The user's conversations of one kind, most recently active first."""

        cursor = (
            self.collection.find({"user_id": user_id, "kind": kind})
            .sort("updated_at", DESCENDING)
            .limit(limit)
        )
        return [_to_conversation(doc) for doc in cursor]

    def count(self, user_id: str | None = None) -> int:
        return self.collection.count_documents({"user_id": user_id} if user_id else {})

    def rename(self, conversation_id: str, user_id: str, title: str) -> None:
        self.collection.update_one(
            {"_id": conversation_id, "user_id": user_id},
            {"$set": {"title": title.strip()[:200] or "Untitled"}},
        )

    def delete(self, conversation_id: str, user_id: str) -> bool:
        """Delete a conversation and its messages. Returns False if not found."""

        result = self.collection.delete_one({"_id": conversation_id, "user_id": user_id})
        if result.deleted_count:
            self.messages_collection.delete_many({"conversation_id": conversation_id})
        return bool(result.deleted_count)

    def delete_for_source(self, user_id: str, kind: str, source_id: str) -> None:
        conversation = self.find_for_source(user_id, kind, source_id)
        if conversation:
            self.delete(conversation.id, user_id)

    # -- messages ----------------------------------------------------------
    def add_message(
        self,
        conversation: Conversation,
        role: str,
        text: str,
        citations: list[dict] | None = None,
    ) -> Message:
        now = utcnow()
        doc = {
            "_id": uuid.uuid4().hex,
            "conversation_id": conversation.id,
            "user_id": conversation.user_id,
            "role": role,
            "text": text,
            "citations": citations or [],
            "created_at": now,
        }
        self.messages_collection.insert_one(doc)
        self.collection.update_one(
            {"_id": conversation.id},
            {
                "$set": {"updated_at": now, "preview": " ".join(text.split())[:_PREVIEW_CHARS]},
                "$inc": {"message_count": 1},
            },
        )
        return _to_message(doc)

    def messages(self, conversation_id: str, limit: int | None = None) -> list[Message]:
        """Messages oldest first; with ``limit``, only the latest ``limit``."""

        if limit:
            cursor = (
                self.messages_collection.find({"conversation_id": conversation_id})
                .sort("created_at", DESCENDING)
                .limit(limit)
            )
            return [_to_message(doc) for doc in reversed(list(cursor))]
        cursor = self.messages_collection.find({"conversation_id": conversation_id}).sort(
            "created_at", ASCENDING
        )
        return [_to_message(doc) for doc in cursor]

    def clear(self, conversation_id: str, user_id: str) -> None:
        """Remove every message but keep the conversation."""

        if self.get(conversation_id, user_id) is None:
            return
        self.messages_collection.delete_many({"conversation_id": conversation_id})
        self.collection.update_one(
            {"_id": conversation_id},
            {"$set": {"message_count": 0, "preview": "", "updated_at": utcnow()}},
        )

    def count_messages(self) -> int:
        return self.messages_collection.count_documents({})


def _to_conversation(doc: dict | None) -> Conversation | None:
    if doc is None:
        return None
    return Conversation(
        id=doc["_id"],
        user_id=doc["user_id"],
        kind=doc["kind"],
        title=doc.get("title", "Untitled"),
        created_at=as_utc(doc["created_at"]),
        updated_at=as_utc(doc["updated_at"]),
        source_id=doc.get("source_id"),
        message_count=doc.get("message_count", 0),
        preview=doc.get("preview", ""),
    )


def _to_message(doc: dict) -> Message:
    return Message(
        id=doc["_id"],
        conversation_id=doc["conversation_id"],
        role=doc["role"],
        text=doc["text"],
        created_at=as_utc(doc["created_at"]),
        citations=doc.get("citations") or [],
    )
