"""
LLM Service - Ollama (Gemma2 9B)
Tổng hợp thông tin từ context và sinh câu trả lời cho người dùng.
Chạy local qua Ollama, không cần API key.
"""

import requests
from config import OLLAMA_BASE_URL, OLLAMA_MODEL


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

    prompt = f"""Bạn là trợ lý tư vấn tuyển sinh thân thiện và chuyên nghiệp. Nhiệm vụ của bạn là trả lời câu hỏi của sinh viên dựa trên thông tin được cung cấp.

HƯỚNG DẪN:
- Trả lời bằng tiếng Việt, rõ ràng và dễ hiểu
- Sử dụng thông tin từ THÔNG TIN THAM KHẢO bên dưới để trả lời chính xác
- Nếu có bảng số liệu (điểm, học phí...), trình bày rõ ràng
- Khi người dùng xác nhận ("có", "được", "ok"), cung cấp thông tin chi tiết
- CHỈ khi THẬT SỰ không có thông tin liên quan thì mới nói không có dữ liệu
- Không bịa đặt thông tin không có trong tài liệu

QUAN TRỌNG - PHÂN BIỆT CÁC KHÁI NIỆM:
- ĐIỂM CHUẨN / ĐIỂM TRÚNG TUYỂN: Điểm thi tối thiểu để đỗ (thang 30 điểm, thường 20-30). 
  VD: "Điểm chuẩn CNTT PTIT 2024 là 26.4 điểm"
- CHỈ TIÊU TUYỂN SINH: Số lượng sinh viên nhận (đơn vị: sinh viên).
  VD: "Chỉ tiêu 120 nghĩa là nhận 120 sinh viên", KHÔNG phải "điểm chuẩn 120"
- HỌC PHÍ: Tiền học (đơn vị: triệu đồng/năm hoặc triệu đồng/học kỳ)
- Nếu thấy số 100-200 đứng một mình → nhiều khả năng là CHỈ TIÊU, không phải điểm chuẩn

LỊCH SỬ HỘI THOẠI:
{history_text if history_text else "(Chưa có)"}

THÔNG TIN THAM KHẢO:
{context}

CÂU HỎI: {query}

TRẢ LỜI (hãy trả lời trực tiếp và hữu ích):"""

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
