"""
Crawl du lieu tu MongoDB (schools) -> luu vao data/
Moi URL crawl thanh 1 file: data/{school}_{url_slug}.txt
Ho tro crawl 1 URL don le hoac tat ca.
"""
import sys, os, re, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from models.school import get_uncrawled_urls, mark_crawled, mark_failed, save_discovered_urls

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def table_to_text(table_tag):
    """Chuyen <table> HTML thanh text co cau truc.
    Moi dong du lieu duoc ghep voi header tuong ung.
    Vd: "Ma nganh: 7480201 | Ten nganh: CNTT | THPT: 26.4"
    """
    rows = table_tag.find_all("tr")
    if not rows:
        return ""

    # Tim hang header (uu tien hang co <th>, fallback sang hang dau tien)
    headers = []
    data_start = 0
    for i, row in enumerate(rows):
        ths = row.find_all("th")
        if ths:
            headers = [th.get_text(strip=True) for th in ths]
            data_start = i + 1
            break
    if not headers:
        # Khong co <th>, dung hang dau lam header
        headers = [td.get_text(strip=True) for td in rows[0].find_all("td")]
        data_start = 1

    # Xu ly cac hang du lieu
    lines = []
    for row in rows[data_start:]:
        cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
        if not any(cells):
            continue
        if headers and len(cells) == len(headers):
            pairs = [f"{h}: {c}" for h, c in zip(headers, cells) if c and c != "–"]
            lines.append(" | ".join(pairs))
        else:
            # Fallback: noi cells bang dau |
            non_empty = [c for c in cells if c and c != "–"]
            if non_empty:
                lines.append(" | ".join(non_empty))

    return "\n".join(lines)


SKIP_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".doc", ".docx", ".xls", ".xlsx"}


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

        # Phat hien links cung domain TRUOC khi xoa tags
        links = discover_links(soup, url)

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Xu ly bang HTML: chuyen thanh text co cau truc truoc khi get_text()
        for table in soup.find_all("table"):
            formatted = table_to_text(table)
            if formatted:
                table.replace_with(BeautifulSoup(formatted, "html.parser"))
            else:
                table.decompose()  # Xoa bang rong

        text = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return "\n".join(lines), links
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
    if text:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        mark_crawled(school_id, url)
        if links:
            save_discovered_urls(school_id, links)
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
        if text:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)
            mark_crawled(sid, url)
            if links:
                save_discovered_urls(sid, links)
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
