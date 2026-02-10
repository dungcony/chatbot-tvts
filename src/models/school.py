"""
Model School - Quan ly thong tin truong trong MongoDB
Collection: schools
Document: {school_id, name, keywords, urls, crawled}
"""
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME

COLLECTION_NAME = "schools"
_client = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = MongoClient(MONGO_URI)
        _collection = _client[DB_NAME][COLLECTION_NAME]
    return _collection


def get_all_schools():
    """Tra ve list cac truong: [{school_id, name, keywords, urls, crawled}]"""
    docs = list(get_collection().find({}, {"_id": 0}))
    return docs


def detect_school(query):
    """Nhan dien truong tu cau hoi. Tra ve school_id hoac None."""
    q = query.lower()
    for s in get_all_schools():
        for kw in s.get("keywords", []):
            if kw.lower() in q:
                return s["school_id"]
    return None


def add_school(school_id, name, keywords):
    """Them truong moi (hoac cap nhat neu da ton tai)."""
    col = get_collection()
    existing = col.find_one({"school_id": school_id})
    if existing:
        col.update_one(
            {"school_id": school_id},
            {"$set": {"name": name, "keywords": keywords}}
        )
    else:
        col.insert_one({
            "school_id": school_id,
            "name": name,
            "keywords": keywords,
            "urls": [],
            "crawled": []
        })


def add_url(school_id, url):
    """Them 1 URL vao truong."""
    result = get_collection().update_one(
        {"school_id": school_id, "urls": {"$ne": url}},
        {"$push": {"urls": url}}
    )
    return result.modified_count > 0


def add_urls(school_id, urls):
    """Them nhieu URL vao truong (chi them URL chua co)."""
    col = get_collection()
    for url in urls:
        col.update_one(
            {"school_id": school_id, "urls": {"$ne": url}},
            {"$push": {"urls": url}}
        )
    return True


def mark_crawled(school_id, url):
    """Danh dau URL da crawl."""
    get_collection().update_one(
        {"school_id": school_id, "crawled": {"$ne": url}},
        {"$push": {"crawled": url}}
    )


def get_uncrawled_urls(school_id=None):
    """Lay URLs chua crawl. None = tat ca truong."""
    result = []
    schools = get_all_schools()
    for s in schools:
        if school_id and s["school_id"] != school_id:
            continue
        crawled = set(s.get("crawled", []))
        for url in s.get("urls", []):
            if url not in crawled:
                result.append({"school_id": s["school_id"], "url": url})
    return result


def remove_school(school_id):
    """Xoa truong."""
    get_collection().delete_one({"school_id": school_id})


def remove_url(school_id, url):
    """Xoa 1 URL khoi truong."""
    get_collection().update_one(
        {"school_id": school_id},
        {"$pull": {"urls": url, "crawled": url}}
    )
