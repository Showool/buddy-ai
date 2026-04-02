"""
配置管理 - 支持多环境配置
"""

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

    # 项目根目录（自动检测）
    PROJECT_ROOT: Optional[Path] = None

    @field_validator("PROJECT_ROOT", mode="before")
    @classmethod
    def set_project_root(cls, v):
        """自动设置项目根目录"""
        if v is None:
            # 从当前文件向上查找项目根目录（包含 README.md 的目录）
            current = Path(__file__).resolve().parent
            for _ in range(5):  # 最多向上查找 5 层
                if (current / "README.md").exists() or (current / "README.MD").exists():
                    return current
                current = current.parent
            return Path(__file__).resolve().parent.parent  # 默认返回 backend 的上级目录
        return Path(v) if isinstance(v, str) else v

    # ========== API Keys ==========
    DASHSCOPE_API_KEY: str = ""
    TAVILY_API_KEY: str = ""
    OPENAI_API_KEY: str = ""  # 可选，用于 OpenAI 模型

    # ========== 数据库配置 ==========
    REDIS_URL: str = "redis://localhost:6379/0"
    POSTGRESQL_URL: str = "postgresql://user:pass@localhost:5432/buddyai"

    # ========== 向量数据库 ==========
    # 统一使用 PostgreSQL+pgvector
    PGVECTOR_COLLECTION_NAME: str = "buddy_ai_docs"

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
    EMBEDDING_MODEL: str = "text-embedding-v4"
    EMBEDDING_DIMENSIONS: int = 1024

    # ========== RAG 检索配置 ==========
    RAG_SEARCH_MODE: str = "hybrid"  # embedding / keywords / hybrid
    RAG_VECTOR_TOP_K: int = 4
    RAG_MIN_SIMILARITY: float = 0.5
    RAG_DIRECT_RETURN_THRESHOLD: float = 0.9
    RAG_RRF_K: int = 60
    RAG_VECTOR_TIMEOUT: float = 5.0
    RAG_FULLTEXT_TIMEOUT: float = 3.0

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


# 创建配置实例
settings = Settings()

# 确保必要的目录存在
settings.get_upload_path().mkdir(parents=True, exist_ok=True)


# 根据环境覆盖配置
if settings.is_production:
    # 生产环境特殊配置
    settings.DEBUG = False
    settings.LOG_LEVEL = "WARNING"
elif settings.ENVIRONMENT == "staging":
    # 预发布环境配置
    settings.DEBUG = False
    settings.LOG_LEVEL = "INFO"
