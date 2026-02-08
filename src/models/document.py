"""
Model Document - Quản lý collection 'documents' trong MongoDB
Schema: { _id, content, embedding (Array 768) }
"""

from pymongo import MongoClient
from config import MONGO_URI, DB_NAME

COLLECTION_NAME = "documents"
VECTOR_INDEX_NAME = "vector_index"

_client = None
_collection = None


def get_collection():
    """Trả về collection 'documents' (kết nối 1 lần duy nhất)."""
    global _client, _collection
    if _collection is None:
        print("Đang kết nối MongoDB [documents]...")
        _client = MongoClient(MONGO_URI)
        _collection = _client[DB_NAME][COLLECTION_NAME]
        print("MongoDB [documents] đã kết nối!")
    return _collection
