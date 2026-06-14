"""
Xiaoshitou Agent System - Main Application Entry Point
FastAPI server with four-layer pipeline, MCP integration, RAG, file management.
"""
import sys, os, traceback
from pathlib import Path
try:
    sys.path.insert(0, str(Path(__file__).parent))
except NameError:
    sys.path.insert(0, os.getcwd())
    from pathlib import Path
    parent = Path(os.getcwd()).parent
    parent_str = str(parent)
    if parent_str not in sys.path:
        sys.path.insert(0, parent_str)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.config import get_settings
from app.database import init_db, get_db_info
from app.api.routes import router as api_router


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="小石头智能助手",
        description=(
            "四层架构智能体系统 - 输入理解 → 数据获取 → 数据处理(LLM清洗) → 输出呈现\n"
            "集成MCP协议、RAG知识库、WPS三件套生成"
        ),
        version="4.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    # ━━━ Static file serving for generated/uploaded files ━━━
    from fastapi.staticfiles import StaticFiles
    workspace_dir = Path(__file__).parent / "workspace" / "files"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/files", StaticFiles(directory=str(workspace_dir)), name="workspace_files")
    logger.info(f"📁 Static files served from: {workspace_dir}")

    logger.add(
        "logs/xiaoshitou_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
    )

    # ━━━ Global Exception Handlers ━━━

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catch all unhandled exceptions to prevent silent failures."""
        logger.error(f"❌ Unhandled error on {request.method} {request.url}: {exc}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": str(exc)[:500],
                "path": str(request.url),
            },
        )

    from fastapi.exceptions import HTTPException

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(
            f"HTTP {exc.status_code} on {request.method} {request.url}: {exc.detail}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": str(exc.status_code), "message": str(exc.detail)},
        )

    @app.on_event("startup")
    async def startup_event():
        logger.info("🪨 小石头智能助手启动中...")
        # ━━━ Validate API Key ━━━
        api_key = settings.ai_api_key
        if not api_key or api_key.startswith("sk-placeholder") or len(api_key) < 10:
            logger.warning("⚠️ AI_API_KEY 未有效配置！聊天功能将无法正常工作。")
            logger.warning("   请在 backend/.env 中设置有效的 AI_API_KEY")
        else:
            masked = api_key[:8] + "..." + api_key[-4:]
            logger.info(f"🔑 AI_API_KEY 已配置: {masked}")
            logger.info(
                f"🌐 LLM 后端: {settings.ai_api_base_url} | "
                f"模型: {settings.ai_model_name}"
            )

        try:
            db_info = init_db()
            logger.info(
                f"✅ 数据库就绪 | 类型: {db_info['type']} | 连接: {db_info['connection']}"
            )
            if db_info['type'] == "SQLite (memory)":
                logger.warning("⚠️ 使用内存存储！数据重启后丢失。请检查MySQL连接。")
            elif db_info['type'] == "SQLite":
                logger.info("📋 使用SQLite本地存储（MySQL不可用）")

            logger.info("🔍 联网搜索: 常驻开启（用户不可关闭）")
            logger.info(
                f"🧠 深度思考默认: {'启用' if settings.deep_thinking_default else '关闭'}"
            )
            logger.info("📁 文件存储: workspace/files/ (上传/生成/备份)")

            # Initialize MCP manager
            try:
                from app.mcp import get_mcp_manager
                mcp = get_mcp_manager()
                tools = mcp.get_tools()
                logger.info(f"📡 MCP协议: 已加载 {len(tools)} 个MCP工具")
            except Exception as e:
                logger.warning(f"⚠️ MCP初始化跳过: {e}")

            # Initialize RAG (Milvus)
            try:
                from app.rag import VectorDBManager
                rag = VectorDBManager(
                    host=settings.milvus_host,
                    port=settings.milvus_port,
                    collection_name=settings.milvus_collection,
                )
                stats = rag.get_stats()
                logger.info(
                    f"📚 RAG知识库: {'已连接' if stats.get('connected') else '未连接'} | "
                    f"集合: {settings.milvus_collection}"
                )
            except Exception as e:
                logger.warning(f"⚠️ RAG初始化跳过: {e}")

        except Exception as e:
            logger.warning(f"⚠️ 数据库初始化警告: {e}")

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("👋 小石头智能助手正在关闭...")
        try:
            from app.mcp import get_mcp_manager
            mcp = get_mcp_manager()
            await mcp.cleanup()
            logger.info("🧹 MCP连接已清理")
        except Exception:
            pass

    @app.get("/")
    def root():
        db_info = get_db_info()
        rag_stats = {}
        try:
            from app.rag import VectorDBManager
            s = get_settings()
            rag = VectorDBManager(
                host=s.milvus_host,
                port=s.milvus_port,
                collection_name=s.milvus_collection,
            )
            rag_stats = rag.get_stats()
        except Exception:
            pass

        mcp_tools_count = 0
        try:
            from app.mcp import get_mcp_manager
            mcp = get_mcp_manager()
            mcp_tools_count = len(mcp.get_tools())
        except Exception:
            pass

        return {
            "name": "小石头智能助手",
            "version": "4.0.0",
            "description": "四层架构智能体系统 - 完整重构版",
            "database": db_info,
            "rag": rag_stats,
            "mcp_tools": mcp_tools_count,
            "features": [
                "多会话隔离记忆",
                "文件全生命周期管理",
                "WPS三件套生成与美化",
                "联网搜索（常驻）",
                "RAG知识库 (Milvus + DashScope)",
                "MCP协议集成 (天气/文件/地图)",
                "深度思考模式",
                "个性化设置",
            ],
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=False,
        log_level="info",
        timeout_keep_alive=65,
    )