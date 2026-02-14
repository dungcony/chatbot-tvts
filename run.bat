@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Chatbot Tu van Tuyen sinh

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Chatbot Tu van Tuyen sinh              ║
echo  ║   Auto Setup ^& Run                       ║
echo  ╚══════════════════════════════════════════╝
echo.

REM ============================================
REM BUOC 1: Kiem tra Python ^>= 3.10
REM ============================================
echo  [1/5] Kiem tra Python...

python --version >nul 2>&1
if %errorlevel% neq 0 goto :install_python

python -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>nul
if %errorlevel% neq 0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do (
        echo         Python %%v qua cu ^(can 3.10+^). Dang nang cap...
    )
    goto :install_python
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo         OK - Python %%v
goto :step2

:install_python
echo         Dang cai dat Python 3.12...
winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent 2>nul
if !errorlevel! equ 0 (
    echo         Da cai Python 3.12. Khoi dong lai script...
    timeout /t 3 /nobreak >nul
    start "" cmd /c ""%~f0""
    exit
)
echo         Winget khong kha dung. Dang tai Python truc tiep...
powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe' -OutFile \"$env:TEMP\python_setup.exe\" }" 2>nul
if exist "%TEMP%\python_setup.exe" (
    echo         Dang cai dat... ^(mat khoang 1-2 phut^)
    "%TEMP%\python_setup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1
    del "%TEMP%\python_setup.exe" >nul 2>&1
    echo         Da cai Python. Khoi dong lai script...
    timeout /t 3 /nobreak >nul
    start "" cmd /c ""%~f0""
    exit
)
echo.
echo  [LOI] Khong the tu dong cai Python!
echo        Tai thu cong tai: https://www.python.org/downloads/
echo        QUAN TRONG: Tich chon "Add Python to PATH" khi cai dat.
echo        Sau do chay lai file run.bat nay.
start https://www.python.org/downloads/
pause
exit /b 1

REM ============================================
REM BUOC 2: Kiem tra Ollama
REM ============================================
:step2
echo  [2/5] Kiem tra Ollama...

REM Kiem tra neu dung cloud model thi bo qua cai Ollama local
set "CHECK_MODEL="
for /f "tokens=2 delims==" %%m in ('findstr /B "OLLAMA_MODEL=" .env 2^>nul') do set "CHECK_MODEL=%%m"
if not "!CHECK_MODEL!"=="" (
    echo !CHECK_MODEL! | findstr /I "cloud" >nul 2>&1
    if !errorlevel! equ 0 (
        echo         Cloud model - bo qua Ollama local
        goto :step3
    )
)

REM Tim ollama trong PATH
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    echo         OK - Ollama da cai
    goto :step3
)

REM Tim ollama o cac thu muc cai dat thuong gap tren Windows
set "OLLAMA_FOUND="
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    set "OLLAMA_FOUND=%LOCALAPPDATA%\Programs\Ollama"
)
if not defined OLLAMA_FOUND if exist "%ProgramFiles%\Ollama\ollama.exe" (
    set "OLLAMA_FOUND=%ProgramFiles%\Ollama"
)
if not defined OLLAMA_FOUND if exist "%USERPROFILE%\AppData\Local\Ollama\ollama.exe" (
    set "OLLAMA_FOUND=%USERPROFILE%\AppData\Local\Ollama"
)
if defined OLLAMA_FOUND (
    echo         Tim thay Ollama tai: !OLLAMA_FOUND!
    set "PATH=!OLLAMA_FOUND!;!PATH!"
    echo         OK - Da them vao PATH
    goto :step3
)

REM Kiem tra Ollama co dang chay khong (co the cai roi nhung chua trong PATH)
powershell -Command "try { Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" 2>nul
if %errorlevel% equ 0 (
    echo         OK - Ollama da chay
    goto :step3
)

REM Chua co Ollama -> cai dat
echo         Dang cai dat Ollama...
winget install Ollama.Ollama --accept-package-agreements --accept-source-agreements --silent 2>nul

REM Sau khi winget xong, kiem tra lai (ke ca khi winget bao "da cai roi")
where ollama >nul 2>&1
if %errorlevel% equ 0 goto :ollama_installed
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    set "PATH=%LOCALAPPDATA%\Programs\Ollama;!PATH!"
    goto :ollama_installed
)

REM Winget that bai hoac khong co -> tai truc tiep
echo         Dang tai Ollama truc tiep...
powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile \"$env:TEMP\OllamaSetup.exe\" }" 2>nul
if exist "%TEMP%\OllamaSetup.exe" (
    echo         Dang cai dat Ollama...
    "%TEMP%\OllamaSetup.exe" /VERYSILENT /NORESTART
    del "%TEMP%\OllamaSetup.exe" >nul 2>&1
    timeout /t 5 /nobreak >nul
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Ollama;!PATH!"
        goto :ollama_installed
    )
)
echo.
echo  [LOI] Khong the tu dong cai Ollama!
echo        Tai thu cong tai: https://ollama.com/download/windows
echo        Sau do chay lai file run.bat nay.
start https://ollama.com/download/windows
pause
exit /b 1

:ollama_installed
echo         OK - Ollama da san sang

REM ============================================
REM BUOC 3: Tao venv va cai thu vien Python
REM ============================================
:step3
echo  [3/5] Cai dat thu vien Python...

if exist "venv\Scripts\activate.bat" (
    echo         OK - Da cai tu truoc
    goto :step4
)

echo         Dang tao virtual environment...
python -m venv venv
if !errorlevel! neq 0 (
    echo  [LOI] Khong the tao virtual environment!
    pause
    exit /b 1
)

echo         Dang cai thu vien ^(lan dau mat 5-10 phut^)...
call venv\Scripts\activate.bat
pip install --no-cache-dir --quiet torch --index-url https://download.pytorch.org/whl/cpu
if !errorlevel! neq 0 (
    echo  [LOI] Khong the cai PyTorch!
    pause
    exit /b 1
)
pip install --no-cache-dir --quiet -r requirements.txt
if !errorlevel! neq 0 (
    echo  [LOI] Khong the cai thu vien!
    pause
    exit /b 1
)
echo         OK - Da cai xong thu vien

REM ============================================
REM BUOC 4: Cau hinh .env
REM ============================================
:step4
echo  [4/5] Kiem tra cau hinh...

if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
    ) else (
        (
            echo OLLAMA_BASE_URL=http://localhost:11434
            echo OLLAMA_MODEL=gemma2:2b
            echo MONGO_URI=
            echo DB_NAME=tuvantuyensinh
        ) > .env
    )
)

REM Kiem tra MONGO_URI da duoc cau hinh chua
findstr /B /C:"MONGO_URI=mongodb" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo         OK - .env da cau hinh
    goto :step5
)

echo.
echo  ┌──────────────────────────────────────────┐
echo  │  Can nhap MongoDB connection string.      │
echo  │  Lien he nguoi chia se du an de nhan.     │
echo  │                                           │
echo  │  Vi du:                                   │
echo  │  mongodb+srv://user:pass@cluster.net/...  │
echo  └──────────────────────────────────────────┘
echo.
set /p "MONGO_INPUT=  Nhap MONGO_URI: "
if "!MONGO_INPUT!"=="" (
    echo  [LOI] MONGO_URI khong duoc de trong!
    pause
    exit /b 1
)

REM Luu URI vao file tam roi dung Python de ghi vao .env (tranh loi ky tu dac biet)
echo !MONGO_INPUT!> "%TEMP%\_mongo_uri.tmp"
call venv\Scripts\activate.bat
python -c "uri=open(r'%TEMP%\_mongo_uri.tmp',encoding='utf-8').read().strip();lines=open('.env','r',encoding='utf-8').readlines();f=open('.env','w',encoding='utf-8');[f.write(f'MONGO_URI={uri}\n') if l.startswith('MONGO_URI=') else f.write(l) for l in lines];f.close()"
del "%TEMP%\_mongo_uri.tmp" >nul 2>&1
echo         OK - Da luu cau hinh

REM ============================================
REM BUOC 5: Khoi dong Ollama + Pull model + Chay
REM ============================================
:step5
echo  [5/5] Khoi dong chatbot...

REM Doc model tu .env
set "MODEL=gemma2:2b"
for /f "tokens=2 delims==" %%m in ('findstr /B "OLLAMA_MODEL=" .env 2^>nul') do set "MODEL=%%m"

REM Kiem tra cloud model (ten chua "cloud") -> khong can Ollama local
echo !MODEL! | findstr /I "cloud" >nul 2>&1
if %errorlevel% equ 0 (
    echo         Cloud model: !MODEL!
    echo         Khong can Ollama local - goi truc tiep Ollama Cloud API
    goto :model_ready
)

REM === Model local: can Ollama chay ===
REM Kiem tra Ollama co dang chay khong
powershell -Command "try { Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" 2>nul
if %errorlevel% equ 0 goto :ollama_ok

echo         Dang khoi dong Ollama...
start "" ollama serve
echo         Cho Ollama san sang...
set "ollama_retries=0"

:wait_ollama
timeout /t 2 /nobreak >nul
powershell -Command "try { Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" 2>nul
if %errorlevel% equ 0 goto :ollama_ok

set /a ollama_retries+=1
if !ollama_retries! geq 30 (
    echo  [LOI] Ollama khong khoi dong duoc!
    echo        Thu mo Ollama Desktop thu cong roi chay lai.
    pause
    exit /b 1
)
goto :wait_ollama

:ollama_ok
echo         OK - Ollama dang chay

ollama list 2>nul | findstr /C:"!MODEL!" >nul 2>&1
if %errorlevel% neq 0 (
    echo         Dang tai model !MODEL! ^(lan dau mat vai phut^)...
    ollama pull !MODEL!
    if !errorlevel! neq 0 (
        echo  [LOI] Khong the tai model !MODEL!
        pause
        exit /b 1
    )
)

:model_ready
echo         OK - Model !MODEL! da san sang

REM Kich hoat venv va chay Flask
call venv\Scripts\activate.bat

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   CHATBOT DA SAN SANG!                   ║
echo  ║                                           ║
echo  ║   Truy cap:  http://localhost:5000        ║
echo  ║   Admin:     http://localhost:5000/admin  ║
echo  ║                                           ║
echo  ║   Nhan Ctrl+C hoac dong cua so de dung.  ║
echo  ╚══════════════════════════════════════════╝
echo.

REM Tu dong mo trinh duyet
start http://localhost:5000

cd src
python app.py

REM Khi Flask dung, hien thong bao
echo.
echo  Chatbot da dung.
pause
