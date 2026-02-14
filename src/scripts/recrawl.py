"""
Re-crawl: Reset trang thai crawl + xoa data cu + crawl lai + embed lai.
Chay: python scripts/recrawl.py
"""
import sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models.db import get_db
from scripts.crawl_data import crawl_school, DATA_DIR
from scripts.prepare_data import process_files, get_unprocessed_files

db = get_db()

print("=" * 50)
print("  Re-crawl & Re-embed du lieu")
print("=" * 50)

# 1. Reset trang thai crawled trong MongoDB
result = db["schools"].update_many({}, {"$set": {"crawled": [], "failed": []}})
print(f"\n[1/5] Reset crawled status: {result.modified_count} truong")

# 2. Xoa data_versions (de embed lai)
result = db["data_versions"].delete_many({})
print(f"[2/5] Xoa data_versions: {result.deleted_count} records")

# 3. Xoa documents cu (embeddings)
result = db["documents"].delete_many({})
print(f"[3/5] Xoa documents: {result.deleted_count} records")

# 4. Xoa file data cu
if os.path.exists(DATA_DIR):
    count = len([f for f in os.listdir(DATA_DIR) if f.endswith(".txt")])
    shutil.rmtree(DATA_DIR)
    print(f"[4/5] Xoa {count} file data cu")
else:
    print("[4/5] Khong co file data cu")

# 5. Crawl lai
print("\n[5/5] Dang crawl lai tat ca...")
crawl_result = crawl_school()
print(f"  Crawl xong: {crawl_result['crawled']} trang, {crawl_result['failed']} loi")

# 6. Embed lai
print("\n[6/6] Dang embed lai...")
unprocessed = get_unprocessed_files()
if unprocessed:
    embed_result = process_files(unprocessed)
    print(f"  Embed xong: {embed_result['processed']} files, {embed_result['chunks']} chunks")
else:
    print("  Khong co file nao can embed")

print("\n" + "=" * 50)
print("  Hoan tat!")
print("=" * 50)
