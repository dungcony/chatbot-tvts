# Chatbot Tư vấn Tuyển sinh

Chatbot RAG (Retrieval-Augmented Generation) tư vấn tuyển sinh PTIT & Bách Khoa Hà Nội.

**Kiến trúc:** Flask + MongoDB Vector Search + Ollama (LLM local) + HuggingFace Embeddings

## Yêu cầu

- Python 3.10+
- MongoDB Atlas (có Vector Search Index)
- [Ollama](https://ollama.com/) (chạy LLM local)
- RAM ≥ 4GB

## Cài đặt

### 1. Clone & tạo virtual environment

```bash
git clone <repo-url>
cd chat_bot
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows
```

### 2. Cài gói Python

```bash
pip install -r requirements.txt
```

### 3. Cài Ollama & pull model

```bash
# Cài Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model (chọn 1)
ollama pull gemma2:2b     # Nhẹ (~1.6GB), nhanh, chạy tốt trên CPU
# ollama pull gemma2:9b   # Tốt hơn (~5.4GB), cần GPU hoặc RAM ≥ 8GB
```

### 4. Cấu hình biến môi trường

```bash
cp .env.example .env
```

Sửa file `.env` với thông tin MongoDB của bạn:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma2:2b
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/
DB_NAME=tuvantuyensinh
```

### 5. Chuẩn bị dữ liệu (chỉ lần đầu)

```bash
cd src
python scripts/crawl_data.py
python scripts/prepare_data.py
```

### 6. Chạy

```bash
cd src
python app.py
```

Truy cập: http://localhost:5000

## Cấu trúc project

```
src/
├── app.py                  # Flask server chính
├── config.py               # Cấu hình từ .env
├── data/                   # Dữ liệu crawl
├── models/                 # MongoDB models
│   ├── chat_history.py     # Chat history
│   └── document.py         # Documents collection
├── scripts/                # Scripts crawl & prepare data
│   ├── crawl_data.py
│   └── prepare_data.py
├── services/               # Business logic
│   ├── embedding.py        # HuggingFace Embedding model
│   ├── llm.py              # Ollama LLM
│   └── vector_search.py    # MongoDB Vector Search
└── templates/
    └── index.html          # Giao diện chat
```
