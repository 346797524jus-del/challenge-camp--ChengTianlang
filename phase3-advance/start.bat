@echo off
chcp 65001 >nul
echo ========================================
echo   AI 编程小助手 - 智能体模式启动脚本
echo ========================================
echo.

REM 检查 .env 文件是否存在
if not exist ".env" (
    echo [错误] 找不到 .env 文件！
    echo 请复制 .env.example 为 .env 并填入你的 API Key
    echo.
    echo 命令: copy .env.example .env
    pause
    exit /b 1
)

REM 从 .env 文件加载环境变量
echo [1/3] 加载环境变量...
for /f "tokens=* delims=" %%a in ('.env') do (
    set %%a
)

REM 检查 API Key 是否已设置
if "%OPENAI_API_KEY%"=="" (
    echo [错误] OPENAI_API_KEY 未设置！
    echo 请在 .env 文件中填入你的 DeepSeek API Key
    pause
    exit /b 1
)
if "%OPENAI_API_KEY%"=="YOUR_API_KEY_HERE" (
    echo [错误] 请先在 .env 文件中填入你的真实 DeepSeek API Key！
    echo 当前值: %OPENAI_API_KEY%
    pause
    exit /b 1
)

echo   API Base URL: %AI_API_BASE_URL%
echo   Model: %AI_MODEL_NAME%
echo   API Key: %OPENAI_API_KEY:~0,8%...
echo.

REM 启动后端
echo [2/3] 启动后端服务 (端口 8081)...
start "Backend" cmd /c "title Backend && echo 后端服务启动中... && .\mvnw spring-boot:run && pause"

REM 等待后端启动
echo   等待后端启动...
timeout /t 20 /nobreak >nul

REM 启动前端
echo [3/3] 启动前端服务...
cd ai-code-helper-frontend
start "Frontend" cmd /c "title Frontend && npm run dev -- --host && pause"
cd ..

echo.
echo ========================================
echo   启动完成！
echo.
echo   后端: http://localhost:8081/api
echo   前端: http://localhost:3000
echo.
echo   智能体功能:
echo   - 生成 Word 文档（简历、报告等）
echo   - 生成 Excel 表格（学习计划、数据统计等）
echo   - 生成 PPT 演示文稿
echo   - 搜索面试题
echo   - 在线预览和下载生成的文件
echo.
echo   使用说明:
echo   1. 在浏览器中打开前端地址
echo   2. 在输入框中输入需求（如"帮我生成一份Java学习计划"）
echo   3. 智能体会自动调用工具生成文件
echo   4. 生成的文件可以在"文件管理"面板中查看和下载
echo.
echo ========================================
echo.
echo 按任意键关闭此窗口...
pause >nul
