"""
FastAPI 主应用入口
"""

import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api.v1 import chat, files

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
        logger.info(f"✅ Debug mode: {settings.DEBUG}")

        # 测试 PostgreSQL 连接
        try:
            import psycopg2
            conn = psycopg2.connect(settings.POSTGRESQL_URL)
            conn.close()
            logger.info(f"✅ PostgreSQL 连接成功")
        except Exception as e:
            logger.warning(f"⚠️  PostgreSQL 连接失败: {e}")
            logger.info("💡 提示: 确保 PostgreSQL 已安装 pgvector 扩展: CREATE EXTENSION IF NOT EXISTS vector;")

        # 生成 LangGraph 工作流程图
        try:
            from app.agent.workflow_diagram import generate_workflow_diagram
            diagram_path = generate_workflow_diagram()
            if diagram_path:
                logger.info(f"✅ LangGraph 流程图已生成: {diagram_path}")
        except Exception as e:
            logger.warning(f"⚠️  生成流程图失败（可忽略）: {e}")

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
    "http://localhost:3001",
    "http://127.0.0.1:3001",
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
    # 只返回可序列化的错误详情，避免包含 FormData 等对象
    error_details = [
        {
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": error_details},
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