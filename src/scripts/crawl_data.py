"""
Crawl du lieu tu MongoDB (schools) -> luu vao data/
Moi URL crawl thanh 1 file: data/{school}_{url_slug}.txt
Ho tro crawl 1 URL don le hoac tat ca.
"""
import sys, os, re, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from models.school import get_uncrawled_urls, mark_crawled, mark_failed

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def crawl_page(url, timeout=15):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.encoding = "utf-8"
        if resp.status_code >= 400:
            print(f"  FAIL [{resp.status_code}] {url}")
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return "\n".join(lines)
    except Exception as e:
        print(f"  FAIL crawl {url}: {e}")
        return None


def url_to_filename(school_id, url):
    path = urlparse(url).path.strip("/").replace("/", "_") or "trangchu"
    safe = re.sub(r"[^\w\-]", "_", path)[:60]
    return f"{school_id}_{safe}.txt"


def crawl_single(school_id, url):
    """Crawl 1 URL don le. Tra ve dict ket qua."""
    os.makedirs(DATA_DIR, exist_ok=True)
    filename = url_to_filename(school_id, url)
    filepath = os.path.join(DATA_DIR, filename)

    text = crawl_page(url)
    if text:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        mark_crawled(school_id, url)
        print(f"  OK [{school_id}] {filename} ({len(text)} ky tu)")
        return {"success": True, "filename": filename, "chars": len(text)}
    else:
        mark_failed(school_id, url)
        return {"success": False, "error": f"Khong crawl duoc: {url}"}


def crawl_school(school_id=None):
    """Crawl tat ca URL chua crawl (bo qua failed). Tra ve dict ket qua."""
    uncrawled = get_uncrawled_urls(school_id)
    if not uncrawled:
        return {"crawled": 0, "failed": 0, "files": [], "errors": []}

    os.makedirs(DATA_DIR, exist_ok=True)
    crawled = []
    errors = []

    for item in uncrawled:
        sid = item["school_id"]
        url = item["url"]
        filename = url_to_filename(sid, url)
        filepath = os.path.join(DATA_DIR, filename)

        text = crawl_page(url)
        if text:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)
            mark_crawled(sid, url)
            crawled.append({"school": sid, "filename": filename, "url": url, "chars": len(text)})
            print(f"  OK [{sid}] {filename} ({len(text)} ky tu)")
        else:
            mark_failed(sid, url)
            errors.append(f"Khong crawl duoc: {url}")
        time.sleep(1)

    return {"crawled": len(crawled), "failed": len(errors), "files": crawled, "errors": errors}


if __name__ == "__main__":
    print("Crawl du lieu tu MongoDB...")
    result = crawl_school()
    print(f"\nXong: {result['crawled']} trang, {result['failed']} loi")
