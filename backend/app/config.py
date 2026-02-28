"""
配置管理 - 支持多环境配置
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # ========== 应用配置 ==========
    APP_NAME: str = "Buddy-AI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"  # development, staging, production
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ========== API Keys ==========
    DASHSCOPE_API_KEY: str = ""
    TAVILY_API_KEY: str = ""
    OPENAI_API_KEY: str = ""  # 可选，用于 OpenAI 模型

    # ========== 数据库配置 ==========
    REDIS_URL: str = "redis://localhost:6379/0"
    POSTGRESQL_URL: str = "postgresql://user:pass@localhost:5432/buddyai"

    # ========== 向量数据库 ==========
    VECTOR_DB_TYPE: str = "chroma"  # chroma 或 postgresql
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "buddy_ai_knowledge"
    PGVECTOR_COLLECTION_NAME: str = "buddy_ai_knowledge"

    # ========== 文件上传配置 ==========
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB
    ALLOWED_FILE_TYPES: list[str] = ["pdf", "docx", "txt", "md", "csv"]

    @field_validator("ALLOWED_FILE_TYPES", mode="before")
    @classmethod
    def parse_allowed_file_types(cls, v):
        """解析逗号分隔的文件类型列表"""
        if isinstance(v, str):
            return [t.strip() for t in v.split(",")]
        return v

    # ========== LLM 配置 ==========
    LLM_MODEL: str = "qwen-plus"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000
    LLM_STREAM: bool = True

    # ========== Embedding 配置 ==========
    EMBEDDING_MODEL: str = "text-embedding-v2"
    EMBEDDING_DIMENSIONS: int = 1536

    # ========== Agent 配置 ==========
    MAX_TOOL_CALLS: int = 3
    MAX_RETRIES: int = 3

    # ========== WebSocket 配置 ==========
    WS_HEARTBEAT_INTERVAL: int = 30  # 心跳间隔（秒）
    WS_MAX_CONNECTIONS: int = 100  # 最大连接数

    # ========== 安全配置 ==========
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ========== 日志配置 ==========
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    def get_upload_path(self) -> Path:
        """获取上传目录路径"""
        return Path(self.UPLOAD_DIR)

    def get_chroma_path(self) -> Path:
        """获取Chroma数据库路径"""
        return Path(self.CHROMA_PERSIST_DIR)


# 创建配置实例
settings = Settings()

# 确保必要的目录存在
settings.get_upload_path().mkdir(parents=True, exist_ok=True)

# 只有在使用 Chroma 时才创建 Chroma 目录
if settings.VECTOR_DB_TYPE == "chroma":
    settings.get_chroma_path().mkdir(parents=True, exist_ok=True)


# 根据环境覆盖配置
if settings.is_production:
    # 生产环境特殊配置
    settings.DEBUG = False
    settings.LOG_LEVEL = "WARNING"
elif settings.ENVIRONMENT == "staging":
    # 预发布环境配置
    settings.DEBUG = False
    settings.LOG_LEVEL = "INFO"