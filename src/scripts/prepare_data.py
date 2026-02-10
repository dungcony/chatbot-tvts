"""
Pipeline: data/*.txt -> Chunking -> Embedding -> MongoDB
Chi xu ly file moi, khong xoa du lieu cu.
Nhan dien truong tu ten file: ptit_trangchu.txt -> school = ptit
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from models.document import get_collection, COLLECTION_NAME
from models.data_version import is_processed, mark_processed
from services.embedding import get_embedding_model

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def extract_school(filename):
    """ptit_trangchu.txt -> ptit"""
    return filename.split("_")[0] if "_" in filename else "unknown"


def get_unprocessed_files():
    if not os.path.exists(DATA_DIR):
        return []
    return [f for f in sorted(os.listdir(DATA_DIR)) if f.endswith(".txt") and not is_processed(f)]


def get_all_data_files():
    if not os.path.exists(DATA_DIR):
        return []
    files = []
    for f in sorted(os.listdir(DATA_DIR)):
        if f.endswith(".txt"):
            files.append({
                "filename": f,
                "school": extract_school(f),
                "size": os.path.getsize(os.path.join(DATA_DIR, f)),
                "processed": is_processed(f)
            })
    return files


def process_files(filenames=None):
    if filenames is None:
        filenames = get_unprocessed_files()
    if not filenames:
        return {"processed": 0, "chunks": 0, "files": [], "errors": []}

    embedding_model = get_embedding_model()
    collection = get_collection()
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=400)

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
            loader = TextLoader(filepath, encoding="utf-8")
            docs = loader.load()
            chunks = splitter.split_documents(docs)
            if not chunks:
                errors.append(f"File rong: {filename}")
                continue

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
            mark_processed(filename, school, len(mongo_docs))
            total_chunks += len(mongo_docs)
            processed.append({"filename": filename, "school": school, "chunks": len(mongo_docs)})
            print(f"  OK [{school}] {filename}: {len(mongo_docs)} chunks")
        except Exception as e:
            errors.append(f"Loi {filename}: {str(e)}")

    return {"processed": len(processed), "chunks": total_chunks, "files": processed, "errors": errors}


if __name__ == "__main__":
    unprocessed = get_unprocessed_files()
    if not unprocessed:
        print("Tat ca file da embed.")
    else:
        print(f"{len(unprocessed)} file chua xu ly")
        result = process_files(unprocessed)
        print(f"Xong: {result['processed']} files, {result['chunks']} chunks")
