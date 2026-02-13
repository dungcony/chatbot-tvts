"""
Model Chat History - Quản lý collection 'chat_history' trong MongoDB
Schema: { _id, session_id, role, message, timestamp }
"""

from pymongo import ASCENDING, DESCENDING
from models.db import get_db

COLLECTION_NAME = "chat_history"
_collection = None
_indexes_created = False


def get_collection():
    """Trả về collection 'chat_history' (kết nối 1 lần duy nhất)."""
    global _collection, _indexes_created
    if _collection is None:
        _collection = get_db()[COLLECTION_NAME]
        if not _indexes_created:
            # Index cho query theo session_id + sort timestamp
            _collection.create_index(
                [("session_id", ASCENDING), ("timestamp", DESCENDING)],
                background=True
            )
            # TTL index: tu dong xoa sau 7 ngay
            _collection.create_index(
                "timestamp",
                expireAfterSeconds=7 * 24 * 3600,
                background=True
            )
            _indexes_created = True
    return _collection


def get_recent_history(session_id, limit=6):
    """Lay lich su hoi thoai gan nhat cua session."""
    docs = list(
        get_collection()
        .find({"session_id": session_id}, {"_id": 0, "role": 1, "message": 1})
        .sort("timestamp", -1)
        .limit(limit)
    )
    docs.reverse()
    return docs
