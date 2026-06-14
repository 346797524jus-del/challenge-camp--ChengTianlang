@echo off
echo ========================================
echo   P3 Agent System - Backend Startup
echo ========================================
echo.

cd /d "%~dp0"

:: Check if virtual environment exists
if not exist "venv\" (
    echo [1/3] Creating Python virtual environment...
    python -m venv venv
    echo Done.
) else (
    echo [1/3] Virtual environment already exists.
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Install dependencies
echo [2/3] Installing dependencies...
pip install -r requirements.txt -q
echo Done.

:: Create necessary directories
if not exist "uploads\" mkdir uploads
if not exist "generated-docs\" mkdir generated-docs
if not exist "logs\" mkdir logs

:: Copy .env if not exists
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [INFO] .env file created from .env.example
        echo [INFO] Please edit .env with your actual API keys!
    )
)

:: Start server
echo.
echo [3/3] Starting P3 Agent System on http://localhost:8081
echo       API Docs: http://localhost:8081/docs
echo       Press Ctrl+C to stop
echo ========================================
echo.

python main.py

pause