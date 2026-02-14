"""
Crawl du lieu tu MongoDB (schools) -> luu vao data/
Moi URL crawl thanh 1 file: data/{school}_{url_slug}.md (noi dung dang Markdown)
Ho tro crawl 1 URL don le hoac tat ca.
"""
import sys, os, re, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import urlparse, urljoin
from models.school import get_uncrawled_urls, mark_crawled, mark_failed, save_discovered_urls

# Playwright (tuy chon): dung khi trang load noi dung bang JavaScript
try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    sync_playwright = None
    _PLAYWRIGHT_AVAILABLE = False

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


# So giay cho them sau khi trang load de noi dung load bang fetch/XHR kip hien
PLAYWRIGHT_WAIT_AFTER_LOAD_MS = 3500


def _fetch_html_playwright(url, timeout=15000):
    """Lay HTML sau khi JavaScript chay (can cai: pip install playwright && playwright install chromium)."""
    if not _PLAYWRIGHT_AVAILABLE:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout)
            # Cho them de trang SPA load noi dung qua API/fetch
            page.wait_for_timeout(PLAYWRIGHT_WAIT_AFTER_LOAD_MS)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print(f"    WARN Playwright fetch loi: {e}")
        return None


def _html_to_text_and_links(html, url):
    """
    Parse HTML thanh (text_cleaned, links, title).
    Khong kiem tra MIN_CONTENT_LENGTH hay error pattern - do crawl_page xu ly.
    """
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    links = discover_links(soup, url)

    listing_count = len(soup.find_all(string=re.compile(r"Xem chi tiết", re.IGNORECASE)))
    if listing_count >= 3:
        return None, links, title

    # Chi xoa theo ten the nhung thu that su la rac; giu header/nav de tranh xoa mat noi dung chinh (nhieu trang SPA de noi dung trong header)
    for tag in soup(["script", "style", "footer", "aside", "iframe", "noscript"]):
        tag.decompose()

    # Xoa block theo class/id (ke ca header/nav neu la thanh tren dau trang).
    # KHONG dung "widget" don vi trang Elementor/WordPress dat noi dung chinh trong elementor-widget-text-editor.
    JUNK_PATTERNS = [
        "sidebar", "breadcrumb", "related", "comment", "share", "social", "advert", "banner",
        "site-header", "main-nav", "top-nav", "navbar", "page-header", "menu-nav", "header-nav",
        "sidebar-widget", "widget-sidebar", "footer-widget", "widget-footer", "wp-widget",
    ]
    tags_to_remove = []
    for tag in soup.find_all(True):
        try:
            classes = " ".join(tag.get("class", [])).lower()
            tag_id = (tag.get("id") or "").lower()
        except (AttributeError, TypeError):
            continue
        if any(p in classes or p in tag_id for p in JUNK_PATTERNS):
            tags_to_remove.append(tag)
    for tag in tags_to_remove:
        try:
            tag.decompose()
        except Exception:
            pass

    try:
        text = md(str(soup), heading_style="ATX", strip=["img"])
    except Exception:
        text = soup.get_text(separator="\n")

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
    return text, links, title


def crawl_page(url, timeout=15):
    """Crawl 1 trang. Tra ve (text, discovered_links) hoac (None, set())."""
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=req_headers, timeout=timeout)
        resp.encoding = "utf-8"
        if resp.status_code >= 400:
            print(f"  FAIL [{resp.status_code}] {url}")
            return None, set()
        raw_html_len = len(resp.text)
        text, links, title = _html_to_text_and_links(resp.text, url)
        if text is None:
            print(f"  SKIP (trang listing) {url}")
            return None, links

        head_lower = text[:1000].lower()
        for pattern in ERROR_PATTERNS:
            if pattern in head_lower:
                print(f"  SKIP (soft error: '{pattern}') {url}")
                return None, links

        text_len = len(text)
        skip_display_len = text_len
        if text_len < MIN_CONTENT_LENGTH:
            # Thu lai bang Playwright neu trang co ve load bang JS
            if raw_html_len > 3000 and text_len < 100 and _PLAYWRIGHT_AVAILABLE:
                print(f"  Thu lai voi Playwright (trang JS): {url}")
                html_js = _fetch_html_playwright(url, timeout=timeout * 1000)
                if html_js:
                    text_js, links_js, title_js = _html_to_text_and_links(html_js, url)
                    if text_js is not None and len(text_js) >= MIN_CONTENT_LENGTH:
                        metadata = f"[URL: {url}]"
                        if title_js:
                            metadata = f"[{title_js}]\n{metadata}"
                        return f"{metadata}\n\n{text_js}", links_js
                    if text_js is not None:
                        skip_display_len = len(text_js)
            reason = f"  SKIP (qua ngan: {skip_display_len} < {MIN_CONTENT_LENGTH}) {url}"
            if raw_html_len > 3000 and text_len < 100:
                reason += " [Ly do: trang co the load noi dung bang JavaScript - requests chi lay duoc HTML khung]"
            if not _PLAYWRIGHT_AVAILABLE and raw_html_len > 3000 and text_len < 100:
                reason += " [Go y: cai Playwright de thu crawl lai: pip install playwright && playwright install chromium]"
            print(reason)
            return None, links

        metadata = f"[URL: {url}]"
        if title:
            metadata = f"[{title}]\n{metadata}"
        text = f"{metadata}\n\n{text}"
        return text, links
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  FAIL crawl {url}: {e}")
        return None, set()


def url_to_filename(school_id, url):
    path = urlparse(url).path.strip("/").replace("/", "_") or "trangchu"
    safe = re.sub(r"[^\w\-]", "_", path)[:60]
    return f"{school_id}_{safe}.md"


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
