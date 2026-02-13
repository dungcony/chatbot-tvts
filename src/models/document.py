"""
Model Document - Quản lý collection 'documents' trong MongoDB
Schema: { _id, content, embedding (Array 768) }
"""

from models.db import get_db

COLLECTION_NAME = "documents"
VECTOR_INDEX_NAME = "vector_index"
_collection = None


def get_collection():
    """Trả về collection 'documents' (kết nối 1 lần duy nhất)."""
    global _collection
    if _collection is None:
        _collection = get_db()[COLLECTION_NAME]
    return _collection
