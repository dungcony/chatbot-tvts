#!/bin/bash
# ============================================
# Cài đặt Chatbot Tư vấn Tuyển sinh (Linux/macOS)
# Chạy: chmod +x install.sh && ./install.sh
# ============================================

set -e

echo "============================================"
echo "  Cài đặt Chatbot Tư vấn Tuyển sinh"
echo "============================================"
echo ""

# 1. Kiểm tra Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker chưa được cài đặt!"
    echo "👉 Cài Docker: https://docs.docker.com/engine/install/"
    exit 1
fi
echo "✅ Docker đã cài"

# 2. Kiểm tra Docker Compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose chưa được cài đặt!"
    exit 1
fi
echo "✅ Docker Compose đã cài"

# 3. Tạo file .env nếu chưa có
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo ""
        echo "⚠️  File .env đã được tạo từ .env.example"
        echo "👉 Hãy mở file .env và sửa thông tin MongoDB của bạn"
        echo ""
        read -p "Bạn đã sửa .env xong chưa? (y/n): " ready
        if [[ ! "$ready" =~ ^[Yy]$ ]]; then
            echo "👉 Sửa file .env rồi chạy lại ./install.sh"
            exit 0
        fi
    else
        echo "❌ Không tìm thấy .env hoặc .env.example"
        exit 1
    fi
else
    echo "✅ File .env đã có"
fi

# 4. Build và khởi chạy containers
echo ""
echo "🔨 Đang build Docker containers..."
docker compose build

echo ""
echo "🚀 Đang khởi chạy containers..."
docker compose up -d

# 5. Chờ Ollama khởi động
echo ""
echo "⏳ Đang chờ Ollama khởi động..."
sleep 10

until docker exec ollama ollama list &> /dev/null; do
    sleep 3
done
echo "✅ Ollama đã sẵn sàng"

# 6. Pull model Ollama
echo ""
echo "📥 Đang tải model gemma2:2b (~1.6GB)..."
docker exec ollama ollama pull gemma2:2b

echo ""
echo "============================================"
echo "  ✅ Cài đặt hoàn tất!"
echo "============================================"
echo ""
echo "  🌐 Truy cập: http://localhost:5000"
echo "  🔧 Admin:    http://localhost:5000/admin"
echo ""
echo "  Các lệnh:"
echo "    ./start.sh  - Khởi chạy"
echo "    ./stop.sh   - Dừng"
echo ""
