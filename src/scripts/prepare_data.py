"""
Pipeline: data/*.txt -> Clean -> Chunking -> Embedding -> MongoDB
- Tu dong phat hien file moi hoac file thay doi (so sanh hash)
- Lam sach noi dung truoc khi embed (xoa footer lap, trang rac)
- Nhan dien truong tu ten file: ptit_trangchu.txt -> school = ptit
"""
import sys, os, re, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_text_splitters import RecursiveCharacterTextSplitter
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
    """Lam sach noi dung: xoa footer lap, dong rac, khoang trang thua."""
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

    # Xoa cac dong rac
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Bo dong chi co "Xem chi tiết", "Facebook", "Youtube", v.v.
        if stripped.lower() in ("xem chi tiết", "facebook", "youtube", "xem chi tiet"):
            continue
        # Bo dong chi co ten tac gia lap lai
        if stripped in ("admindaotao", "ptit") and len(stripped) < 20:
            continue
        if stripped:
            cleaned.append(stripped)

    return "\n".join(cleaned)


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
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)

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

            # Chunk noi dung
            from langchain_core.documents import Document
            doc = Document(page_content=text, metadata={"source": filepath})
            chunks = splitter.split_documents([doc])
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
