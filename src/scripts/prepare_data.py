"""
Pipeline chuẩn bị dữ liệu cho Chatbot Tư vấn Tuyển sinh (RAG)
Quy trình: Load Document -> Chunking -> Embedding -> Lưu MongoDB
Theo cấu trúc báo cáo thực tập:
  - chunk_size=800, chunk_overlap=400
  - MongoDB schema: { _id, content, embedding (Array 768) }

Chạy: cd src && python scripts/prepare_data.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import DB_NAME
from models.document import get_collection, COLLECTION_NAME
from services.embedding import get_embedding_model


def main():
    # ==============================
    # 1. LOAD DOCUMENT
    # ==============================
    print("=" * 50)
    print("BƯỚC 1: Load Document")
    print("=" * 50)

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    loader_dir = DirectoryLoader(
        data_dir, glob="**/*.txt", loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    documents = loader_dir.load()

    print(f"Số lượng tài liệu đã tải: {len(documents)}")
    for i, doc in enumerate(documents):
        print(f"  - File {i+1}: {doc.metadata.get('source', 'N/A')} ({len(doc.page_content)} ký tự)")

    # ==============================
    # 2. CHUNKING
    # ==============================
    print("\n" + "=" * 50)
    print("BƯỚC 2: Chunking Document (chunk_size=800, overlap=400)")
    print("=" * 50)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=400
    )
    texts = text_splitter.split_documents(documents)

    print(f"Số lượng chunks sau khi chia: {len(texts)}")
    for i, chunk in enumerate(texts[:5]):
        print(f"\n--- Chunk {i+1} ({len(chunk.page_content)} ký tự) ---")
        print(chunk.page_content[:150] + "...")
    if len(texts) > 5:
        print(f"\n... và {len(texts) - 5} chunks khác")

    # ==============================
    # 3. EMBEDDING + LƯU MONGODB
    # ==============================
    print("\n" + "=" * 50)
    print("BƯỚC 3: Tạo Embedding và lưu vào MongoDB")
    print("=" * 50)

    embedding_model = get_embedding_model()

    # Kiểm tra kích thước vector
    test_vector = embedding_model.embed_query("test")
    print(f"Kích thước vector: {len(test_vector)} chiều")

    # Lấy collection từ model
    collection = get_collection()

    # Xóa dữ liệu cũ
    old_count = collection.count_documents({})
    if old_count > 0:
        print(f"Xóa {old_count} bản ghi cũ...")
        collection.delete_many({})

    # Tạo embedding và lưu từng chunk
    print(f"Đang tạo embedding và lưu {len(texts)} chunks vào MongoDB...")

    mongo_docs = []
    for i, chunk in enumerate(texts):
        vector = embedding_model.embed_query(chunk.page_content)
        mongo_doc = {
            "content": chunk.page_content,
            "embedding": vector
        }
        mongo_docs.append(mongo_doc)

        if (i + 1) % 10 == 0 or (i + 1) == len(texts):
            print(f"  Đã xử lý: {i+1}/{len(texts)} chunks")

    collection.insert_many(mongo_docs)
    print(f"\nĐã lưu {len(mongo_docs)} documents vào MongoDB")
    print(f"   Database: {DB_NAME}")
    print(f"   Collection: {COLLECTION_NAME}")
    print(f"   Schema: {{ _id, content, embedding (Array {len(test_vector)}) }}")

    # ==============================
    # 4. HƯỚNG DẪN TẠO VECTOR INDEX
    # ==============================
    print("\n" + "=" * 50)
    print("BƯỚC 4: Tạo Vector Search Index trên MongoDB Atlas")
    print("=" * 50)

    print("""
Bạn cần tạo Vector Search Index trên MongoDB Atlas:

1. Truy cập MongoDB Atlas -> Database -> Collection -> Search Indexes
2. Chọn "Create Search Index" -> JSON Editor
3. Đặt tên index: "vector_index"
4. Dán cấu hình sau:

{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 768,
      "similarity": "cosine"
    }
  ]
}

5. Nhấn "Create Search Index"
""")

    # ==============================
    # 5. TEST VECTOR SEARCH
    # ==============================
    print("=" * 50)
    print("BƯỚC 5: Test Vector Search")
    print("=" * 50)

    from services.vector_search import vector_search

    queries = [
        "Điểm chuẩn ngành Công nghệ thông tin là bao nhiêu?",
        "Học phí trường bao nhiêu?",
        "Có những phương thức tuyển sinh nào?",
    ]

    try:
        for query in queries:
            print(f"\nCâu hỏi: {query}")
            results = vector_search(query, num_candidates=150, limit=4)
            if results:
                for j, doc in enumerate(results):
                    score = doc.get("score", 0)
                    content = doc["content"][:120]
                    print(f"  Kết quả {j+1} (score: {score:.4f}): {content}...")
            else:
                print("  Không có kết quả. Hãy kiểm tra Vector Search Index.")
    except Exception as e:
        print(f"\nChưa thể test vector search: {e}")
        print("   -> Hãy tạo Vector Search Index trên MongoDB Atlas trước (xem Bước 4)")

    print("\nPipeline hoàn tất! MongoDB đã sẵn sàng cho chatbot RAG.")


if __name__ == "__main__":
    main()
