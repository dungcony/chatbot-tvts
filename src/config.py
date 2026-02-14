"""
Cấu hình trung tâm - Load từ file .env
Chỉ chứa config cấp môi trường (secrets, connection strings).
Application constants (collection names, index names) nằm ở từng service.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI environment variable not set. Check .env file.")
DB_NAME = os.getenv("DB_NAME", "tuvantuyensinh")

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")

# Tự detect cloud model: nếu tên model chứa "cloud" -> gọi Ollama Cloud API
IS_CLOUD_MODEL = "cloud" in OLLAMA_MODEL.lower()
if IS_CLOUD_MODEL:
    OLLAMA_BASE_URL = "https://ollama.com"  # Cloud API endpoint

# Embedding
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)
