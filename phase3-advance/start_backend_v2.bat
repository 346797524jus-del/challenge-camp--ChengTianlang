@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   启动 AI 智能助手 v2.0 后端
echo ========================================

REM 设置环境变量
set AI_API_BASE_URL=https://api.deepseek.com
set AI_MODEL_NAME=deepseek-chat
set OPENAI_API_KEY=sk-46f3e548c7774726b1c6a94da442a496

echo API Base URL: %AI_API_BASE_URL%
echo Model: %AI_MODEL_NAME%
echo API Key: %OPENAI_API_KEY:~0,8%...
echo.

echo 正在启动 (端口 8081)...
java -jar target\ai-code-helper-0.0.1-SNAPSHOT.jar
pause