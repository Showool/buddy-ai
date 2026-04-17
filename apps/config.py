"""
配置管理
"""

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（config.py 上一级）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"

load_dotenv(_ENV_FILE)


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-5.2"

    # ========== API Keys ==========
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ZHIPUAI_API_KEY: str = ""
    ZHIPUAI_URL: str = "https://open.bigmodel.cn/api/paas/v4/"
    OPENAI_API_KEY: str = ""
    TAVILY_API_KEY: str = ""

    # ========== 上传配置 ==========
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB

    # ========== 数据库配置 ==========
    REDIS_URL: str = "redis://localhost:6379/0"
    MYSQL_URL: str = "mysql+aiomysql://root:123456@localhost:3306/buddy_ai?charset=utf8"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600
    DB_ECHO: bool = False

    # ========== Milvus 向量库配置 (mem0) ==========
    MILVUS_URL: str = "http://localhost:19530"
    MILVUS_TOKEN: str = ""
    MILVUS_DB_NAME: str = ""
    MILVUS_MEM0_COLLECTION_NAME: str = "mem0"

    # ========== Embedding 配置 ==========
    EMBEDDING_PROVIDER: str = "openai"  # "huggingface"
    EMBEDDING_MODEL: str = "text-embedding-3-large"  # "Qwen/Qwen3-Embedding-8B"
    EMBEDDING_DIMENSIONS: int = 1024

    # ========== 日志配置 ==========
    LOG_LEVEL: str = "INFO"


# 创建全局配置实例
settings = Settings()
