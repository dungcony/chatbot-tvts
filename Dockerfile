FROM python:3.12-slim

WORKDIR /app

# Cài curl và zstd để tải ollama
RUN apt-get update && apt-get install -y curl zstd && rm -rf /var/lib/apt/lists/*

# Cài ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Cài torch CPU-only trước (nhẹ hơn rất nhiều so với bản có CUDA)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Cài dependencies còn lại
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY .env .env

# Expose port
EXPOSE 5000

# Chạy Flask app
WORKDIR /app/src
CMD ["sh", "-c", "ollama serve & sleep 5 && ollama pull gemma2:2b && python app.py"]
