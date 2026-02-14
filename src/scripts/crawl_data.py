"""
Crawl du lieu tu MongoDB (schools) -> luu vao data/
Moi URL crawl thanh 1 file: data/{school}_{url_slug}.txt
Ho tro crawl 1 URL don le, tat ca, hoac deep crawl (tim link con).

CACH SU DUNG WHITELIST/BLACKLIST:
- BLACKLIST_PATHS: Loai bo URL co chua cac path nay (vd: /tag/, /category/)
- WHITELIST_PATHS: CHI crawl URL co chua cac path nay. 
  + Neu WHITELIST_PATHS = [] thi crawl tat ca (tru blacklist)
  + Neu WHITELIST_PATHS = ['/tuyen-sinh', '/tin-tuc'] thi CHI crawl 2 path nay
"""
import sys, os, re, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from models.school import get_uncrawled_urls, mark_crawled, mark_failed, add_urls, get_all_schools

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# Cac cum tu nhan dien trang loi (soft 404, 403, v.v.)
ERROR_PATTERNS = [
    "không tìm thấy trang",
    "page not found",
    "404",
    "trang không tồn tại",
    "không tồn tại",
    "403 forbidden",
    "access denied",
]

# Noi dung qua ngan (chi co footer/menu) thi coi nhu khong co du lieu
MIN_CONTENT_LENGTH = 200


def crawl_page(url, timeout=15):
    """Crawl 1 trang, tra ve (content, soup) hoac (None, None)."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.encoding = "utf-8"
        if resp.status_code >= 400:
            print(f"  FAIL [{resp.status_code}] {url}")
            return None, None
        soup = BeautifulSoup(resp.text, "html.parser")
        raw_soup = BeautifulSoup(resp.text, "html.parser")  # Giu ban goc de tim links

        # Check soft 404 tu <title>
        title = soup.title.string.strip().lower() if soup.title and soup.title.string else ""
        for pattern in ERROR_PATTERNS:
            if pattern in title:
                print(f"  FAIL [soft-404 title] {url}")
                return None, None

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        content = "\n".join(lines)

        # Check soft 404 tu noi dung
        content_lower = content.lower()
        for pattern in ERROR_PATTERNS:
            if pattern in content_lower[:500]:  # Chi check 500 ky tu dau
                print(f"  FAIL [soft-404 content] {url}")
                return None, None

        # Check noi dung qua ngan
        if len(content) < MIN_CONTENT_LENGTH:
            print(f"  FAIL [too short: {len(content)} chars] {url}")
            return None, None

        return content, raw_soup
    except Exception as e:
        print(f"  FAIL crawl {url}: {e}")
        return None, None


# Cac path nen bo qua khi discover links
SKIP_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.svg', '.pdf', '.doc', '.docx',
                   '.xls', '.xlsx', '.zip', '.rar', '.mp3', '.mp4', '.css', '.js'}
SKIP_PATTERNS = ['#', 'mailto:', 'tel:', 'javascript:', 'facebook.com', 'youtube.com',
                 'google.com', 'zalo.me', 'twitter.com', 'instagram.com', 'linkedin.com']

# Blacklist - Cac path KHONG nen crawl (thuong la trang ngoai lai)
BLACKLIST_PATHS = [
    '/tag/', '/tags/',
    '/category/', '/categories/',
    '/author/', '/authors/',
    '/search', '/tim-kiem',
    '/archive/', '/archives/',
    '/page/', '/p/',
    '/comment/', '/comments/',
    '/feed/', '/rss',
    '/wp-admin/', '/wp-content/', '/wp-includes/',  # WordPress
    '/admin/', '/login/', '/register/',
    '/cart/', '/checkout/', '/account/',  # E-commerce
]

# Whitelist - CHỈ crawl cac path nay (neu la []) thi crawl tat ca)
# Vi du: ['/tuyen-sinh', '/gioi-thieu', '/tin-tuc', '/thong-bao']
WHITELIST_PATHS = []


def discover_links(soup, base_url, same_domain_only=True):
    """Tim tat ca links trong trang, loc cung domain."""
    if not soup:
        return []

    base_parsed = urlparse(base_url)
    base_domain = base_parsed.netloc
    found = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()

        # Bo qua cac link khong hop le
        if any(skip in href.lower() for skip in SKIP_PATTERNS):
            continue

        # Chuyen relative -> absolute
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        # Bo qua file khong phai HTML
        ext = os.path.splitext(parsed.path)[1].lower()
        if ext in SKIP_EXTENSIONS:
            continue

        # Chi giu cung domain
        if same_domain_only and parsed.netloc != base_domain:
            continue

        # Check blacklist paths (bo qua neu trung)
        path_lower = parsed.path.lower()
        if any(blacklist in path_lower for blacklist in BLACKLIST_PATHS):
            continue

        # Check whitelist paths (neu co whitelist thi CHI lay URL trong whitelist)
        if WHITELIST_PATHS:
            if not any(whitelist in path_lower for whitelist in WHITELIST_PATHS):
                continue

        # Chuan hoa: bo fragment, bo trailing slash
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        clean_url = clean_url.rstrip("/")
        if clean_url and clean_url != base_url.rstrip("/"):
            found.add(clean_url)

    return sorted(found)


def url_to_filename(school_id, url):
    path = urlparse(url).path.strip("/").replace("/", "_") or "trangchu"
    safe = re.sub(r"[^\w\-]", "_", path)[:60]
    return f"{school_id}_{safe}.txt"


def crawl_single(school_id, url):
    """Crawl 1 URL don le. Tra ve dict ket qua."""
    os.makedirs(DATA_DIR, exist_ok=True)
    filename = url_to_filename(school_id, url)
    filepath = os.path.join(DATA_DIR, filename)

    text, _ = crawl_page(url)
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

        text, _ = crawl_page(url)
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


def deep_crawl(school_id, start_url, max_pages=30):
    """
    Deep crawl: bat dau tu 1 URL, tim cac link cung domain va crawl tiep.
    Tu dong them URLs moi vao truong trong MongoDB.

    Args:
        school_id: ID truong
        start_url: URL bat dau
        max_pages: So trang toi da de crawl (tranh crawl qua nhieu)

    Returns:
        dict ket qua
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    # Lay danh sach URLs da co cua truong
    schools = get_all_schools()
    school = next((s for s in schools if s["school_id"] == school_id), None)
    if not school:
        return {"error": f"Khong tim thay truong: {school_id}"}

    existing_urls = set(school.get("urls", []))
    crawled_urls = set(school.get("crawled", []))
    failed_urls = set(school.get("failed", []))

    # Queue cac URL can crawl
    queue = [start_url]
    visited = set()
    crawled = []
    errors = []
    new_urls_found = []

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        url_clean = url.rstrip("/")

        # Bo qua neu da visit
        if url_clean in visited:
            continue
        visited.add(url_clean)

        print(f"  [{len(visited)}/{max_pages}] Crawling: {url}")

        text, soup = crawl_page(url)
        if text:
            filename = url_to_filename(school_id, url)
            filepath = os.path.join(DATA_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)

            # Them URL vao truong neu chua co
            if url not in existing_urls:
                add_urls(school_id, [url])
                existing_urls.add(url)
                new_urls_found.append(url)

            mark_crawled(school_id, url)
            crawled_urls.add(url)
            crawled.append({"school": school_id, "filename": filename, "url": url, "chars": len(text)})
            print(f"    OK {filename} ({len(text)} ky tu)")

            # Tim links moi trong trang
            links = discover_links(soup, url)
            for link in links:
                link_clean = link.rstrip("/")
                if (link_clean not in visited
                        and link_clean not in {u.rstrip("/") for u in failed_urls}):
                    queue.append(link)
        else:
            mark_failed(school_id, url)
            failed_urls.add(url)
            errors.append(url)

        time.sleep(1)  # Politeness delay

    return {
        "crawled": len(crawled),
        "failed": len(errors),
        "new_urls_found": len(new_urls_found),
        "files": crawled,
        "errors": errors,
        "new_urls": new_urls_found
    }


if __name__ == "__main__":
    print("Crawl du lieu tu MongoDB...")
    result = crawl_school()
    print(f"\nXong: {result['crawled']} trang, {result['failed']} loi")
