"""
LLM Service - Gemini 2.0 Flash
Tổng hợp thông tin từ context và sinh câu trả lời cho người dùng.
"""

import google.generativeai as genai
from config import GEMINI_API_KEY

_llm = None


def get_llm():
    """Trả về Gemini model (khởi tạo 1 lần duy nhất)."""
    global _llm
    if _llm is None:
        print("Đang khởi tạo Gemini...")
        genai.configure(api_key=GEMINI_API_KEY)
        _llm = genai.GenerativeModel("gemini-2.0-flash")
        print("Gemini sẵn sàng!")
    return _llm


def generate_answer(query: str, context_docs: list) -> str:
    """
    Dùng Gemini tổng hợp thông tin từ context và sinh câu trả lời.

    Args:
        query: Câu hỏi của người dùng
        context_docs: Danh sách documents từ vector search

    Returns:
        str: Câu trả lời từ Gemini
    """
    llm = get_llm()

    context = "\n\n---\n\n".join([doc["content"] for doc in context_docs])

    prompt = f"""Bạn là trợ lý tư vấn tuyển sinh đại học. Hãy trả lời câu hỏi của người dùng
dựa trên thông tin được cung cấp bên dưới. Trả lời bằng tiếng Việt, chính xác và dễ hiểu.

Nếu thông tin không đủ để trả lời, hãy nói rõ là bạn không có đủ thông tin.
Không bịa thông tin. Chỉ trả lời dựa trên dữ liệu được cung cấp.

THÔNG TIN THAM KHẢO:
{context}

CÂU HỎI: {query}

TRẢ LỜI:"""

    response = llm.generate_content(prompt)
    return response.text
