FROM python:3.12-slim

WORKDIR /app

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
CMD ["python", "app.py"]
