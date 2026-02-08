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

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Embedding
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)
