"""
Chatbot Tư vấn Tuyển sinh - Flask Backend
Kiến trúc RAG:
  1. Người dùng gửi câu hỏi
  2. Embedding Model chuyển câu hỏi thành vector
  3. MongoDB Vector Search tìm thông tin liên quan
  4. Gemini LLM tổng hợp và sinh câu trả lời
  5. Flask trả kết quả về giao diện
"""

from flask import Flask, request, jsonify, render_template
from services import vector_search, generate_answer

app = Flask(__name__)


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
    3. Gemini sinh câu trả lời
    """
    data = request.get_json()
    query = data.get("message", "").strip()

    if not query:
        return jsonify({"error": "Vui lòng nhập câu hỏi"}), 400

    try:
        # Bước 1: Vector Search tìm thông tin liên quan
        context_docs = vector_search(query, num_candidates=150, limit=4)

        if not context_docs:
            return jsonify({
                "answer": "Xin lỗi, tôi không tìm thấy thông tin liên quan. Vui lòng thử câu hỏi khác.",
                "sources": []
            })

        # Bước 2: Gemini sinh câu trả lời
        answer = generate_answer(query, context_docs)

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
