"""
FastAPI 主应用入口
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api.v1 import chat, files, sessions, memory

# 配置日志
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 Starting Buddy-AI Backend...")

    # 启动时初始化
    try:
        # 初始化向量数据库目录
        from pathlib import Path
        Path(settings.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
        Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

        logger.info(f"✅ Upload directory: {settings.UPLOAD_DIR}")
        logger.info(f"✅ Chroma DB directory: {settings.CHROMA_PERSIST_DIR}")
        logger.info(f"✅ Debug mode: {settings.DEBUG}")

    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        raise

    yield

    # 关闭时清理
    logger.info("👋 Shutting down Buddy-AI Backend...")


# 创建 FastAPI 应用
app = FastAPI(
    title="Buddy-AI API",
    description="智能问答助手 API - 基于LangGraph和RAG",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)


# CORS 中间件
allow_origins = ["*"] if settings.DEBUG else [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证错误处理"""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "message": str(exc) if settings.DEBUG else "服务器内部错误"},
    )


# 路由注册
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(files.router, prefix="/api/v1", tags=["files"])
app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
app.include_router(memory.router, prefix="/api/v1", tags=["memory"])


@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "ok",
        "version": "2.0.0",
        "message": "Buddy-AI Backend is running"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "debug": settings.DEBUG}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """请求日志中间件"""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} - Status: {response.status_code}")
    return response