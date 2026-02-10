"""
Chatbot Tư vấn Tuyển sinh - Flask Backend
Kiến trúc RAG:
  1. Người dùng gửi câu hỏi
  2. Embedding Model chuyển câu hỏi thành vector
  3. MongoDB Vector Search tìm thông tin liên quan
  4. OLLAMA LLM tổng hợp và sinh câu trả lời
  5. Flask trả kết quả về giao diện
"""

from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template
from services import vector_search, generate_answer
from models.chat_history import get_collection as get_chat_collection

app = Flask(__name__)

# Từ khóa nhận diện trường
PTIT_KEYWORDS = {"ptit", "bưu chính", "viễn thông", "học viện", "bưu điện", "hvbcvt"}
HUST_KEYWORDS = {"bách khoa", "bach khoa", "hust", "bk", "đhbk", "bkhn"}
GREETING_KEYWORDS = {"xin chào", "hello", "hi", "chào", "hey", "chào bạn", "alo", "xin chao"}


def is_greeting(query: str) -> bool:
    """Kiểm tra câu hỏi có phải lời chào không."""
    return query.lower().strip().rstrip("!.") in GREETING_KEYWORDS


def mentions_school(query: str) -> bool:
    """Kiểm tra câu hỏi có nhắc đến trường cụ thể không."""
    q = query.lower()
    for kw in PTIT_KEYWORDS | HUST_KEYWORDS:
        if kw in q:
            return True
    return False


def save_chat(session_id, role, message):
    """Lưu tin nhắn vào chat_history collection."""
    get_chat_collection().insert_one({
        "session_id": session_id,
        "role": role,
        "message": message,
        "timestamp": datetime.now(timezone.utc)
    })


@app.route("/")
def index():
    """Trang chủ - giao diện chat."""
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """
    API endpoint xử lý câu hỏi:
    1. Nhận câu hỏi từ người dùng
    2. Vector search tìm context
    3. OLLAMA sinh câu trả lời
    """
    data = request.get_json()
    query = data.get("message", "").strip()
    session_id = data.get("session_id", "default")

    if not query:
        return jsonify({"error": "Vui lòng nhập câu hỏi"}), 400

    try:
        # Lưu câu hỏi người dùng
        save_chat(session_id, "user", query)

        # Kiểm tra lời chào
        if is_greeting(query):
            answer = "Xin chào! 👋 Tôi là trợ lý tư vấn tuyển sinh. Tôi có thể hỗ trợ thông tin về:\n\n• **PTIT** - Học viện Công nghệ Bưu chính Viễn thông\n• **Bách Khoa Hà Nội** - Đại học Bách Khoa Hà Nội\n\nBạn muốn tìm hiểu về trường nào?"
            save_chat(session_id, "bot", answer)
            return jsonify({"answer": answer, "sources": []})

        # Kiểm tra có nhắc đến trường không
        if not mentions_school(query):
            answer = "Bạn muốn hỏi thông tin này của trường nào?\n\n• **PTIT** - Học viện Công nghệ Bưu chính Viễn thông\n• **Bách Khoa Hà Nội** - Đại học Bách Khoa Hà Nội\n\nHãy cho tôi biết để tôi tìm thông tin chính xác nhé!"
            save_chat(session_id, "bot", answer)
            return jsonify({"answer": answer, "sources": []})

        # Bước 1: Vector Search tìm thông tin liên quan
        context_docs = vector_search(query, num_candidates=150, limit=4)

        if not context_docs:
            return jsonify({
                "answer": "Xin lỗi, tôi không tìm thấy thông tin liên quan. Vui lòng thử câu hỏi khác.",
                "sources": []
            })

        # Bước 2: Ollama sinh câu trả lời
        answer = generate_answer(query, context_docs)

        # Lưu câu trả lời bot
        save_chat(session_id, "bot", answer)

        # Trả về kết quả
        sources = [
            {"content": doc["content"][:200], "score": round(doc.get("score", 0), 4)}
            for doc in context_docs
        ]

        return jsonify({
            "answer": answer,
            "sources": sources
        })

    except Exception as e:
        return jsonify({"error": f"Lỗi xử lý: {str(e)}"}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("Chatbot Tư vấn Tuyển sinh đã sẵn sàng!")
    print("Truy cập: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)
