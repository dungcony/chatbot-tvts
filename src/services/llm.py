"""
LLM Service - Ollama (Gemma2 9B)
Tổng hợp thông tin từ context và sinh câu trả lời cho người dùng.
Chạy local qua Ollama, không cần API key.
"""

import requests
from config import OLLAMA_BASE_URL, OLLAMA_MODEL


def generate_answer(query: str, context_docs: list) -> str:
    """
    Dùng Ollama tổng hợp thông tin từ context và sinh câu trả lời.

    Args:
        query: Câu hỏi của người dùng
        context_docs: Danh sách documents từ vector search

    Returns:
        str: Câu trả lời từ Ollama
    """
    context = "\n\n---\n\n".join([doc["content"] for doc in context_docs])

    prompt = f"""Bạn là trợ lý tư vấn tuyển sinh đại học. Hãy trả lời câu hỏi của người dùng
dựa trên thông tin được cung cấp bên dưới. Trả lời bằng tiếng Việt, chính xác và dễ hiểu.

Nếu thông tin không đủ để trả lời, hãy nói rõ là bạn không có đủ thông tin.
Không bịa thông tin. Chỉ trả lời dựa trên dữ liệu được cung cấp.

THÔNG TIN THAM KHẢO:
{context}

CÂU HỎI: {query}

TRẢ LỜI:"""

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )
    response.raise_for_status()
    return response.json()["response"]
