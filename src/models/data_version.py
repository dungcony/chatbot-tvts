"""
Model DataVersion - Theo doi file da xu ly embedding
Collection: data_versions
"""
from datetime import datetime, timezone
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME

COLLECTION_NAME = "data_versions"
_client = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = MongoClient(MONGO_URI)
        _collection = _client[DB_NAME][COLLECTION_NAME]
    return _collection


def is_processed(filename):
    return get_collection().find_one({"filename": filename, "status": "done"}) is not None


def mark_processed(filename, school, chunks_count):
    get_collection().update_one(
        {"filename": filename},
        {"$set": {
            "filename": filename, "school": school,
            "status": "done", "chunks_count": chunks_count,
            "processed_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )


def get_all_versions():
    return list(get_collection().find({}, {"_id": 0}).sort("processed_at", -1))


def remove_version(filename):
    get_collection().delete_one({"filename": filename})
