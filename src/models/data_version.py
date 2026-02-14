"""
Model DataVersion - Theo doi file da xu ly embedding
Collection: data_versions
Luu hash de phat hien file thay doi.
"""
from datetime import datetime, timezone
from models.db import get_db

COLLECTION_NAME = "data_versions"
_collection = None


def get_collection():
    global _collection
    if _collection is None:
        _collection = get_db()[COLLECTION_NAME]
    return _collection


def is_processed(filename):
    return get_collection().find_one({"filename": filename, "status": "done"}) is not None


def get_file_hash(filename):
    """Lay hash da luu cua file. Tra ve None neu chua co."""
    doc = get_collection().find_one({"filename": filename, "status": "done"})
    return doc.get("file_hash") if doc else None


def mark_processed(filename, school, chunks_count, file_hash=None):
    data = {
        "filename": filename, "school": school,
        "status": "done", "chunks_count": chunks_count,
        "processed_at": datetime.now(timezone.utc)
    }
    if file_hash:
        data["file_hash"] = file_hash
    get_collection().update_one(
        {"filename": filename},
        {"$set": data},
        upsert=True
    )


def get_all_versions():
    return list(get_collection().find({}, {"_id": 0}).sort("processed_at", -1))


def remove_version(filename):
    get_collection().delete_one({"filename": filename})
