"""
Test Vector Search - Chế độ tương tác
Nhập câu hỏi để test tìm kiếm, gõ 'exit' để thoát.

Chạy: cd src && python test.py
"""

from services.vector_search import vector_search


def main():
    print("=" * 50)
    print("TEST VECTOR SEARCH - Chatbot Tư vấn Tuyển sinh")
    print("Gõ câu hỏi để tìm kiếm, gõ 'exit' để thoát")
    print("=" * 50)

    while True:
        query = input("\nNhập câu hỏi: ").strip()
        if query.lower() in ("exit", "quit", "q"):
            break
        if not query:
            continue

        try:
            results = vector_search(query, num_candidates=150, limit=4)
            if results:
                for j, doc in enumerate(results):
                    score = doc.get("score", 0)
                    content = doc["content"][:200]
                    print(f"  Kết quả {j+1} (score: {score:.4f}): {content}...")
            else:
                print("  Không có kết quả.")
        except Exception as e:
            print(f"  Lỗi: {e}")

    print("\nĐã thoát!")


if __name__ == "__main__":
    main()
