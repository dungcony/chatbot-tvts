"""
Pipeline: data/*.txt -> Clean -> Chunking -> Embedding -> MongoDB
- Tu dong phat hien file moi hoac file thay doi (so sanh hash)
- Lam sach noi dung truoc khi embed (xoa footer lap, trang rac)
- Nhan dien truong tu ten file: ptit_trangchu.txt -> school = ptit
"""
import sys, os, re, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from models.document import get_collection, COLLECTION_NAME
from models.data_version import is_processed, mark_processed, get_file_hash
from services.embedding import get_embedding_model

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# --- NOI DUNG RAC CAN XOA ---
# Cac dong bat dau footer (xoa tu dong nay den het file)
FOOTER_MARKERS = [
    "ĐỊA CHỈ HỌC VIỆN",
    "THÔNG TIN LIÊN HỆ",
    "VỀ CHÚNG TÔI",
    "ĐƯỜNG DẪN",
    "© Copyright",
    "All rights reserved",
]

# Noi dung toi thieu sau khi clean (file ngan hon thi bo qua)
MIN_CLEAN_LENGTH = 150

# --- MARKDOWN-AWARE CHUNKING ---
HEADERS_TO_SPLIT_ON = [("#", "h1"), ("##", "h2"), ("###", "h3")]

# --- KIEM TRA NOI DUNG LIEN QUAN ---
# File phai chua it nhat 1 keyword de duoc embed
RELEVANCE_KEYWORDS = [
    # Tuyen sinh
    "tuyển sinh", "điểm chuẩn", "xét tuyển", "chỉ tiêu", "mã ngành",
    "học phí", "phương thức", "trúng tuyển", "nhập học", "nguyện vọng",
    "đăng ký xét tuyển", "điểm trúng tuyển",
    # Thong tin truong
    "giới thiệu", "đào tạo", "cơ sở", "chương trình", "học bổng",
    "câu hỏi thường gặp", "ngành học", "cơ sở vật chất", "triết lý giáo dục",
    "sứ mạng", "tầm nhìn",
]


def extract_school(filename):
    """ptit_trangchu.txt -> ptit"""
    return filename.split("_")[0] if "_" in filename else "unknown"


def file_hash(filepath):
    """Tinh MD5 hash cua file."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_content(text):
    """Lam sach noi dung Markdown: xoa footer lap, dong rac.
    Giu dong trang truoc/sau heading de bao toan cau truc Markdown."""
    lines = text.splitlines()

    # Tim vi tri bat dau footer va cat bo
    cut_index = len(lines)
    for i, line in enumerate(lines):
        stripped = line.strip()
        for marker in FOOTER_MARKERS:
            if marker in stripped:
                cut_index = i
                break
        if cut_index < len(lines):
            break
    lines = lines[:cut_index]

    # Xoa cac dong rac, giu dong trang co y nghia cho Markdown
    JUNK_LINES = {"xem chi tiết", "facebook", "youtube", "xem chi tiet"}
    JUNK_AUTHORS = {"admindaotao", "ptit"}
    cleaned = []
    prev_blank = False
    for line in lines:
        stripped = line.strip()

        # Bo dong rac
        if stripped.lower() in JUNK_LINES:
            continue
        if stripped in JUNK_AUTHORS:
            continue

        # Dong trang: giu toi da 1 dong trang lien tiep
        if not stripped:
            if not prev_blank and cleaned:
                cleaned.append("")
                prev_blank = True
            continue

        # Dam bao co dong trang TRUOC heading Markdown (# ## ###)
        if stripped.startswith("#") and cleaned and cleaned[-1] != "":
            cleaned.append("")

        cleaned.append(stripped)
        prev_blank = False

    # Dam bao co dong trang SAU heading Markdown
    result = []
    for i, line in enumerate(result_lines := cleaned):
        result.append(line)
        # Neu dong hien tai la heading va dong tiep theo khong phai dong trang
        if line.startswith("#") and i + 1 < len(result_lines) and result_lines[i + 1] != "":
            result.append("")

    # Xoa dong trang dau/cuoi thua
    text = "\n".join(result).strip()
    return text


def is_relevant_content(text):
    """Kiem tra noi dung co lien quan den tuyen sinh / thong tin truong khong.
    Tra ve True neu co it nhat 1 keyword lien quan."""
    text_lower = text.lower()
    for kw in RELEVANCE_KEYWORDS:
        if kw in text_lower:
            return True
    return False


def heading_aware_chunk(text, chunk_size=800, chunk_overlap=150):
    """
    Chia noi dung theo heading Markdown, giu heading prefix cho moi chunk.
    Neu chunk van qua dai (> chunk_size), dung RecursiveCharacterTextSplitter
    de tach tiep nhung van giu heading prefix.
    Fallback: neu khong co heading Markdown, split binh thuong.
    """
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT_ON,
        strip_headers=True,
    )
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    md_docs = md_splitter.split_text(text)

    # Fallback: khong co heading markdown -> split binh thuong
    has_headers = any(
        key in doc.metadata
        for doc in md_docs
        for _, key in HEADERS_TO_SPLIT_ON
    )
    if not has_headers:
        return text_splitter.create_documents([text])

    final_chunks = []
    for doc in md_docs:
        # Build heading prefix tu metadata (h1 > h2 > h3)
        prefix_parts = []
        for level, key in HEADERS_TO_SPLIT_ON:
            if key in doc.metadata:
                prefix_parts.append(f"{level} {doc.metadata[key]}")
        heading_prefix = "\n".join(prefix_parts)

        content = doc.page_content
        full_text = f"{heading_prefix}\n\n{content}" if heading_prefix else content

        if len(full_text) <= chunk_size:
            final_chunks.append(Document(page_content=full_text))
        else:
            # Tach tiep body, giu heading prefix cho moi sub-chunk
            sub_docs = text_splitter.create_documents([content])
            for sub_doc in sub_docs:
                sub_text = (
                    f"{heading_prefix}\n\n{sub_doc.page_content}"
                    if heading_prefix
                    else sub_doc.page_content
                )
                final_chunks.append(Document(page_content=sub_text))

    return final_chunks


def get_unprocessed_files():
    """Lay file chua xu ly HOAC file da thay doi (hash khac)."""
    if not os.path.exists(DATA_DIR):
        return []
    result = []
    for f in sorted(os.listdir(DATA_DIR)):
        if not f.endswith(".txt"):
            continue
        filepath = os.path.join(DATA_DIR, f)
        current_hash = file_hash(filepath)
        stored_hash = get_file_hash(f)
        if stored_hash != current_hash:
            result.append(f)
    return result


def get_all_data_files():
    if not os.path.exists(DATA_DIR):
        return []
    files = []
    for f in sorted(os.listdir(DATA_DIR)):
        if f.endswith(".txt"):
            filepath = os.path.join(DATA_DIR, f)
            current_hash = file_hash(filepath)
            stored_hash = get_file_hash(f)
            files.append({
                "filename": f,
                "school": extract_school(f),
                "size": os.path.getsize(filepath),
                "processed": current_hash == stored_hash if stored_hash else False
            })
    return files


def process_files(filenames=None):
    if filenames is None:
        filenames = get_unprocessed_files()
    if not filenames:
        return {"processed": 0, "chunks": 0, "files": [], "errors": []}

    embedding_model = get_embedding_model()
    collection = get_collection()

    total_chunks = 0
    processed = []
    errors = []

    for filename in filenames:
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            errors.append(f"Khong ton tai: {filename}")
            continue
        try:
            school = extract_school(filename)

            # Doc va lam sach noi dung
            with open(filepath, "r", encoding="utf-8") as f:
                raw_text = f.read()
            text = clean_content(raw_text)

            # Bo qua file qua ngan sau khi clean (trang listing, footer-only)
            if len(text) < MIN_CLEAN_LENGTH:
                print(f"  SKIP [{school}] {filename}: qua ngan sau khi clean ({len(text)} ky tu)")
                current_hash = file_hash(filepath)
                mark_processed(filename, school, 0, current_hash)
                continue

            # Bo qua file khong lien quan (khong chua keyword tuyen sinh/truong)
            if not is_relevant_content(text):
                print(f"  SKIP [{school}] {filename}: khong chua keyword lien quan")
                current_hash = file_hash(filepath)
                mark_processed(filename, school, 0, current_hash)
                continue

            # Chunk noi dung (heading-aware neu co Markdown headers)
            chunks = heading_aware_chunk(text)
            if not chunks:
                errors.append(f"File rong sau khi split: {filename}")
                continue

            # Xoa embedding cu cua file nay (neu re-process)
            collection.delete_many({"source_file": filename})

            mongo_docs = []
            for chunk in chunks:
                vector = embedding_model.embed_query(chunk.page_content)
                mongo_docs.append({
                    "content": chunk.page_content,
                    "embedding": vector,
                    "school": school,
                    "source_file": filename
                })
            collection.insert_many(mongo_docs)
            current_hash = file_hash(filepath)
            mark_processed(filename, school, len(mongo_docs), current_hash)
            total_chunks += len(mongo_docs)
            processed.append({"filename": filename, "school": school, "chunks": len(mongo_docs)})
            print(f"  OK [{school}] {filename}: {len(mongo_docs)} chunks")
        except Exception as e:
            errors.append(f"Loi {filename}: {str(e)}")

    return {"processed": len(processed), "chunks": total_chunks, "files": processed, "errors": errors}


if __name__ == "__main__":
    unprocessed = get_unprocessed_files()
    if not unprocessed:
        print("Tat ca file da embed va chua thay doi.")
    else:
        print(f"{len(unprocessed)} file can xu ly")
        result = process_files(unprocessed)
        print(f"Xong: {result['processed']} files, {result['chunks']} chunks")
