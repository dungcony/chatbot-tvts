"""
Model Chat History - Quản lý collection 'chat_history' trong MongoDB
Schema: { _id, session_id, role, message, timestamp }
"""

from pymongo import MongoClient
from config import MONGO_URI, DB_NAME

COLLECTION_NAME = "chat_history"

_client = None
_collection = None


def get_collection():
    """Trả về collection 'chat_history' (kết nối 1 lần duy nhất)."""
    global _client, _collection
    if _collection is None:
        print("Đang kết nối MongoDB [chat_history]...")
        _client = MongoClient(MONGO_URI)
        _collection = _client[DB_NAME][COLLECTION_NAME]
        print("MongoDB [chat_history] đã kết nối!")
    return _collection
