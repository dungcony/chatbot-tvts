"""
Model School - Quan ly thong tin truong trong MongoDB
Collection: schools
Document: {school_id, name, keywords, urls, crawled, failed}
"""
import re
from models.db import get_db

COLLECTION_NAME = "schools"
_collection = None


def get_collection():
    global _collection
    if _collection is None:
        _collection = get_db()[COLLECTION_NAME]
    return _collection


def get_all_schools():
    """Tra ve list cac truong."""
    docs = list(get_collection().find({}, {"_id": 0}))
    # Dam bao luon co field failed
    for d in docs:
        if "failed" not in d:
            d["failed"] = []
    return docs


def detect_school(query, schools=None):
    """Nhan dien truong tu cau hoi. Tra ve school_id hoac None.
    Truyen schools vao de tranh goi get_all_schools nhieu lan."""
    q = query.lower()
    if schools is None:
        schools = get_all_schools()
    for s in schools:
        for kw in s.get("keywords", []):
            # Dung word boundary de tranh match substring
            # vd: 'ai' khong match 'dai', 'hcm' khong match 'pham'
            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', q):
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
            "crawled": [],
            "failed": []
        })


def add_url(school_id, url):
    """Them 1 URL vao truong."""
    col = get_collection()
    # Xoa khoi failed neu co (cho phep retry)
    col.update_one({"school_id": school_id}, {"$pull": {"failed": url}})
    result = col.update_one(
        {"school_id": school_id, "urls": {"$ne": url}},
        {"$push": {"urls": url}}
    )
    return result.modified_count > 0


def add_urls(school_id, urls):
    """Them nhieu URL vao truong."""
    col = get_collection()
    for url in urls:
        col.update_one({"school_id": school_id}, {"$pull": {"failed": url}})
        col.update_one(
            {"school_id": school_id, "urls": {"$ne": url}},
            {"$push": {"urls": url}}
        )
    return True


def mark_crawled(school_id, url):
    """Danh dau URL da crawl thanh cong."""
    col = get_collection()
    col.update_one(
        {"school_id": school_id, "crawled": {"$ne": url}},
        {"$push": {"crawled": url}}
    )
    # Xoa khoi failed neu co
    col.update_one({"school_id": school_id}, {"$pull": {"failed": url}})


def mark_failed(school_id, url):
    """Danh dau URL crawl that bai."""
    col = get_collection()
    col.update_one(
        {"school_id": school_id, "failed": {"$ne": url}},
        {"$push": {"failed": url}}
    )


def unmark_failed(school_id, url):
    """Xoa URL khoi danh sach failed (de retry)."""
    get_collection().update_one(
        {"school_id": school_id},
        {"$pull": {"failed": url}}
    )


def get_uncrawled_urls(school_id=None):
    """Lay URLs chua crawl VA khong bi loi. None = tat ca truong."""
    result = []
    schools = get_all_schools()
    for s in schools:
        if school_id and s["school_id"] != school_id:
            continue
        crawled = set(s.get("crawled", []))
        failed = set(s.get("failed", []))
        for url in s.get("urls", []):
            if url not in crawled and url not in failed:
                result.append({"school_id": s["school_id"], "url": url})
    return result


def remove_school(school_id):
    """Xoa truong."""
    get_collection().delete_one({"school_id": school_id})


def remove_url(school_id, url):
    """Xoa 1 URL khoi truong."""
    get_collection().update_one(
        {"school_id": school_id},
        {"$pull": {"urls": url, "crawled": url, "failed": url}}
    )
