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
DB_NAME = os.getenv("DB_NAME", "tuvantuyensinh")

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")

# Embedding
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)
