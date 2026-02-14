"""
Crawl du lieu tu MongoDB (schools) -> luu vao data/
Moi URL crawl thanh 1 file: data/{school}_{url_slug}.txt
Ho tro crawl 1 URL don le hoac tat ca.
"""
import sys, os, re, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import urlparse, urljoin
from models.school import get_uncrawled_urls, mark_crawled, mark_failed, save_discovered_urls

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# --- BLACKLIST / WHITELIST ---
# Loai bo URL co chua cac path nay
BLACKLIST_PATHS = [
    "/tag/", "/category/", "/page/", "/author/", "/feed/", "/wp-json/", "/wp-admin/",
    # Khong lien quan den tuyen sinh / gioi thieu truong
    "/tuyen-dung/", "/tin-tuc-su-kien/", "/uncategorized/", "/cuu-sinh-vien/", "/tin-tuc/",
]
# Chi crawl URL co chua cac path nay (de trong [] = crawl tat ca)
WHITELIST_PATHS = []

# Cac cum tu nhan dien trang loi (soft 404, 403, v.v.)
ERROR_PATTERNS = [
    "không tìm thấy trang",
    "page not found",
    "lỗi 404",
    "error 404",
    "trang không tồn tại",
    "không tồn tại",
    "403 forbidden",
    "access denied",
]

# Noi dung qua ngan (chi co footer/menu) thi coi nhu khong co du lieu
MIN_CONTENT_LENGTH = 200


SKIP_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".doc", ".docx", ".xls", ".xlsx"}


def is_url_allowed(url):
    """Kiem tra URL co vuot qua blacklist/whitelist khong."""
    parsed = urlparse(url)
    path = parsed.path.lower()

    # Blacklist: loai bo neu path chua bat ky pattern nao
    for bp in BLACKLIST_PATHS:
        if bp in path:
            return False

    # Whitelist: neu co, chi cho phep path chua it nhat 1 pattern
    if WHITELIST_PATHS:
        return any(wp in path for wp in WHITELIST_PATHS)

    return True


def discover_links(soup, base_url):
    """Tim tat ca links cung domain trong trang. Tra ve set URLs."""
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc.lower()
    found = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
            continue
        full_url = urljoin(base_url, href).split("#")[0].split("?")[0].rstrip("/")
        parsed = urlparse(full_url)
        if parsed.netloc.lower() != base_domain:
            continue
        # Bo qua file tai lieu / hinh anh
        ext = os.path.splitext(parsed.path)[1].lower()
        if ext in SKIP_EXTENSIONS:
            continue
        # Ap dung blacklist/whitelist
        if not is_url_allowed(full_url):
            continue
        if full_url != base_url.rstrip("/"):
            found.add(full_url)
    return found


def crawl_page(url, timeout=15):
    """Crawl 1 trang. Tra ve (text, discovered_links) hoac (None, set())."""
    req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=req_headers, timeout=timeout)
        resp.encoding = "utf-8"
        if resp.status_code >= 400:
            print(f"  FAIL [{resp.status_code}] {url}")
            return None, set()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Lay title trang
        title = soup.title.get_text(strip=True) if soup.title else ""

        # Phat hien links cung domain TRUOC khi xoa tags
        links = discover_links(soup, url)

        # Phat hien trang listing (chi co danh sach tieu de + "Xem chi tiet", khong co noi dung thuc)
        listing_count = len(soup.find_all(string=re.compile(r"Xem chi tiết", re.IGNORECASE)))
        if listing_count >= 3:
            print(f"  SKIP (trang listing: {listing_count} lan 'Xem chi tiet') {url}")
            return None, links

        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
            tag.decompose()

        # Xoa cac block co class/id thuong chua noi dung rac
        JUNK_PATTERNS = ["sidebar", "breadcrumb", "related", "widget", "comment", "share", "social", "advert", "banner"]
        for tag in soup.find_all(True):
            classes = " ".join(tag.get("class", [])).lower()
            tag_id = (tag.get("id") or "").lower()
            for pattern in JUNK_PATTERNS:
                if pattern in classes or pattern in tag_id:
                    tag.decompose()
                    break

        # Chuyen HTML -> Markdown (giu heading, table, list)
        text = md(str(soup), heading_style="ATX", strip=["img"])
        # Lam sach: xoa dong trang thua, giu toi da 1 dong trang giua cac doan
        lines = [l.strip() for l in text.splitlines()]
        cleaned = []
        prev_blank = False
        for line in lines:
            if not line:
                if not prev_blank:
                    cleaned.append("")
                prev_blank = True
            else:
                cleaned.append(line)
                prev_blank = False
        text = "\n".join(cleaned).strip()

        # Kiem tra soft 404 / trang loi (chi check 1000 ky tu dau de tranh false positive)
        head_lower = text[:1000].lower()
        for pattern in ERROR_PATTERNS:
            if pattern in head_lower:
                print(f"  SKIP (soft error: '{pattern}') {url}")
                return None, links

        # Kiem tra noi dung qua ngan
        if len(text) < MIN_CONTENT_LENGTH:
            print(f"  SKIP (qua ngan: {len(text)} < {MIN_CONTENT_LENGTH}) {url}")
            return None, links

        # Them metadata vao dau file de giu ngu canh khi chunk
        metadata = f"[URL: {url}]"
        if title:
            metadata = f"[{title}]\n{metadata}"
        text = f"{metadata}\n\n{text}"

        return text, links
    except Exception as e:
        print(f"  FAIL crawl {url}: {e}")
        return None, set()


def url_to_filename(school_id, url):
    path = urlparse(url).path.strip("/").replace("/", "_") or "trangchu"
    safe = re.sub(r"[^\w\-]", "_", path)[:60]
    return f"{school_id}_{safe}.txt"


def crawl_single(school_id, url):
    """Crawl 1 URL don le. Tra ve dict ket qua."""
    os.makedirs(DATA_DIR, exist_ok=True)
    filename = url_to_filename(school_id, url)
    filepath = os.path.join(DATA_DIR, filename)

    text, links = crawl_page(url)
    # Luon luu discovered links (ke ca khi trang fail)
    if links:
        save_discovered_urls(school_id, links)
    if text:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        mark_crawled(school_id, url)
        print(f"  OK [{school_id}] {filename} ({len(text)} ky tu, {len(links)} links)")
        return {"success": True, "filename": filename, "chars": len(text), "discovered": len(links)}
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

        text, links = crawl_page(url)
        # Luon luu discovered links (ke ca khi trang fail)
        if links:
            save_discovered_urls(sid, links)
        if text:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)
            mark_crawled(sid, url)
            crawled.append({"school": sid, "filename": filename, "url": url, "chars": len(text)})
            print(f"  OK [{sid}] {filename} ({len(text)} ky tu, {len(links)} links)")
        else:
            mark_failed(sid, url)
            errors.append(f"Khong crawl duoc: {url}")
        time.sleep(1)

    return {"crawled": len(crawled), "failed": len(errors), "files": crawled, "errors": errors}


if __name__ == "__main__":
    print("Crawl du lieu tu MongoDB...")
    result = crawl_school()
    print(f"\nXong: {result['crawled']} trang, {result['failed']} loi")
