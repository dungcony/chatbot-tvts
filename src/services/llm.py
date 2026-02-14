"""
LLM Service - Ollama
Tổng hợp thông tin từ context và sinh câu trả lời cho người dùng.
Hỗ trợ cả model local (Ollama server) và cloud (Ollama Cloud API).
"""

import requests
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_API_KEY, IS_CLOUD_MODEL


def generate_answer(query: str, context_docs: list, history: list = None) -> str:
    """
    Dùng Ollama tổng hợp thông tin từ context và sinh câu trả lời.

    Args:
        query: Câu hỏi của người dùng
        context_docs: Danh sách documents từ vector search
        history: Lịch sử hội thoại gần nhất [{role, message}]

    Returns:
        str: Câu trả lời từ Ollama
    """
    context = "\n\n---\n\n".join([doc["content"] for doc in context_docs])

    # Xay dung lich su hoi thoai
    history_text = ""
    if history:
        history_lines = []
        for msg in history:
            role = "Người dùng" if msg["role"] == "user" else "Trợ lý"
            history_lines.append(f"{role}: {msg['message']}")
        history_text = "\n".join(history_lines)

    prompt = f"""Bạn là trợ lý tư vấn tuyển sinh đại học. Hãy trả lời câu hỏi của người dùng
dựa trên thông tin được cung cấp bên dưới. Trả lời bằng tiếng Việt, chính xác và dễ hiểu.

Nếu thông tin không đủ để trả lời, hãy nói rõ là bạn không có đủ thông tin.
Không bịa thông tin. Chỉ trả lời dựa trên dữ liệu được cung cấp.
Khi người dùng xác nhận (ví dụ: "có", "đúng", "ok"), hãy cung cấp thông tin tuyển sinh tổng quan dựa trên dữ liệu.

LỊCH SỬ HỘI THOẠI:
{history_text if history_text else "(Không có)"}

THÔNG TIN THAM KHẢO:
{context}

CÂU HỎI HIỆN TẠI: {query}

TRẢ LỜI:"""

    headers = {}
    if IS_CLOUD_MODEL and OLLAMA_API_KEY:
        headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        headers=headers,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 1024
            }
        },
        timeout=120
    )
    response.raise_for_status()
    return response.json()["response"]
