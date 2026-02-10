@echo off
REM ============================================
REM Cài đặt Chatbot Tư vấn Tuyển sinh (Windows)
REM Chạy: click đúp hoặc cmd: install.bat
REM ============================================

echo ============================================
echo   Cài đặt Chatbot Tư vấn Tuyển sinh
echo ============================================
echo.

REM 1. Kiểm tra Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker chưa được cài đặt!
    echo 👉 Tải Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo ✅ Docker đã cài

REM 2. Kiểm tra Docker Compose
docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose chưa được cài đặt!
    pause
    exit /b 1
)
echo ✅ Docker Compose đã cài

REM 3. Tạo file .env nếu chưa có
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo.
        echo ⚠️  File .env đã được tạo từ .env.example
        echo 👉 Hãy mở file .env và sửa thông tin MongoDB của bạn
        echo.
        set /p ready="Bạn đã sửa .env xong chưa? (y/n): "
        if /i not "%ready%"=="y" (
            echo 👉 Sửa file .env rồi chạy lại install.bat
            pause
            exit /b 0
        )
    ) else (
        echo ❌ Không tìm thấy .env hoặc .env.example
        pause
        exit /b 1
    )
) else (
    echo ✅ File .env đã có
)

REM 4. Build và khởi chạy containers
echo.
echo 🔨 Đang build Docker containers...
docker compose build

echo.
echo 🚀 Đang khởi chạy containers...
docker compose up -d

REM 5. Chờ Ollama khởi động
echo.
echo ⏳ Đang chờ Ollama khởi động...
timeout /t 10 /nobreak >nul

:wait_ollama
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 2 /nobreak >nul
    goto wait_ollama
)
echo ✅ Ollama đã sẵn sàng

REM 6. Pull model Ollama
echo.
echo 📥 Đang tải model gemma2:2b (~1.6GB)...
docker exec ollama ollama pull gemma2:2b

echo.
echo ============================================
echo   ✅ Cài đặt hoàn tất!
echo ============================================
echo.
echo   🌐 Truy cập: http://localhost:5000
echo.
echo   Các lệnh:
echo     start.bat  - Khởi chạy
echo     stop.bat   - Dừng
echo.
pause
