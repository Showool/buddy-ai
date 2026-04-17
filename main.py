import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from apps.agent.graph import init_graph
from apps.agent.memory.mem0 import init_memory
from apps.api.agent_chat import router as agent_chat_router
from apps.api.knowledgebase import router as knowledgebase_router
from apps.config import settings
from apps.database.async_engine import create_tables

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """初始化数据库表 & Agent Graph & Memory"""
    await create_tables()
    init_memory()
    async with AsyncRedisSaver.from_conn_string(settings.REDIS_URL) as checkpointer:
        await checkpointer.asetup()
        init_graph(checkpointer)
        yield
    # async with 退出时自动关闭 Redis 连接


app = FastAPI(lifespan=lifespan)

app.include_router(knowledgebase_router)
app.include_router(agent_chat_router)


@app.get("/")
def read_root() -> dict[str, str]:
    """健康检查端点"""
    return {"Hello": "Buddy-AI Backend"}
