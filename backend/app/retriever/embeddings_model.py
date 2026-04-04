"""
嵌入模型工厂 - 支持多种嵌入模型提供商

通过注册表模式 + 单例管理器实现可扩展的嵌入模型加载。
"""

import logging
import threading
from typing import Callable, Optional

from langchain_core.embeddings import Embeddings

from ..config import settings

logger = logging.getLogger(__name__)


class _ProviderRegistry:
    """提供商注册表，维护 provider 名称到工厂函数的映射。"""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], Embeddings]] = {}

    def register(self, name: str, factory: Callable[[], Embeddings]) -> None:
        """注册提供商工厂函数。

        Args:
            name: 提供商名称（自动转为小写）。
            factory: 无参工厂函数，调用后返回 Embeddings 实例。
        """
        self._factories[name.lower()] = factory

    def create(self, name: str) -> Embeddings:
        """根据提供商名称创建模型实例。

        Args:
            name: 提供商名称（大小写不敏感）。

        Returns:
            由对应工厂函数创建的 Embeddings 实例。

        Raises:
            ValueError: 提供商未注册时抛出，错误消息中列出所有已注册提供商。
        """
        name = name.lower()
        if name not in self._factories:
            available = ", ".join(sorted(self._factories.keys()))
            raise ValueError(
                f"不支持的嵌入模型提供商: {name}。支持的选项: {available}"
            )
        return self._factories[name]()

    @property
    def providers(self) -> list[str]:
        """返回所有已注册的提供商名称（排序后）。"""
        return sorted(self._factories.keys())


class _EmbeddingModelManager:
    """线程安全的嵌入模型单例管理器。

    使用双重检查锁定模式确保同一配置下只创建一个模型实例。
    """

    def __init__(self, registry: _ProviderRegistry) -> None:
        self._registry = registry
        self._instance: Optional[Embeddings] = None
        self._instance_key: Optional[str] = None
        self._lock = threading.Lock()

    def get(self) -> Embeddings:
        """获取或创建嵌入模型实例。

        使用双重检查锁定：先在锁外检查缓存键是否匹配，
        再在锁内二次检查，避免不必要的锁竞争。

        Returns:
            缓存的或新创建的 Embeddings 实例。
        """
        key = self._build_key()
        if self._instance is not None and self._instance_key == key:
            return self._instance
        with self._lock:
            if self._instance is not None and self._instance_key == key:
                return self._instance
            self._instance = self._registry.create(settings.EMBEDDING_PROVIDER)
            self._instance_key = key
            logger.info("嵌入模型实例已创建: provider=%s", settings.EMBEDDING_PROVIDER)
            return self._instance

    def reset(self) -> None:
        """清除缓存的模型实例。"""
        with self._lock:
            self._instance = None
            self._instance_key = None
            logger.info("嵌入模型缓存已清除")

    def _build_key(self) -> str:
        """根据当前配置构建缓存键。

        Returns:
            标识当前配置组合的字符串键。
        """
        provider = settings.EMBEDDING_PROVIDER.lower()
        if provider == "huggingface":
            return f"huggingface:{settings.HF_MODEL_NAME}:{settings.HF_DEVICE}:{settings.EMBEDDING_DIMENSIONS}"
        elif provider == "dashscope":
            return f"dashscope:{settings.EMBEDDING_MODEL}"
        return f"{provider}:default"


def _create_dashscope() -> Embeddings:
    """DashScope 云端嵌入模型工厂函数。"""
    if not settings.DASHSCOPE_API_KEY:
        raise ValueError("DashScope 嵌入模型需要配置 DASHSCOPE_API_KEY")
    from langchain_community.embeddings import DashScopeEmbeddings
    return DashScopeEmbeddings(model=settings.EMBEDDING_MODEL)


def _create_huggingface() -> Embeddings:
    """HuggingFace 本地嵌入模型工厂函数。"""
    from .huggingface_model import get_huggingface_embeddings
    return get_huggingface_embeddings()


# 模块级注册表和管理器实例
_registry = _ProviderRegistry()
_registry.register("dashscope", _create_dashscope)
_registry.register("huggingface", _create_huggingface)

_manager = _EmbeddingModelManager(_registry)


def get_embeddings_model() -> Embeddings:
    """获取嵌入模型实例（主要公共 API，向后兼容）。"""
    return _manager.get()


def register_provider(name: str, factory: Callable[[], Embeddings]) -> None:
    """注册自定义嵌入模型提供商。"""
    _registry.register(name, factory)


def reset_embeddings_model() -> None:
    """重置嵌入模型缓存（用于测试）。"""
    _manager.reset()


def health_check() -> bool:
    """验证当前嵌入模型是否正常工作。"""
    try:
        model = get_embeddings_model()
        result = model.embed_query("health check test")
        if len(result) == settings.EMBEDDING_DIMENSIONS:
            return True
        logger.warning(
            "健康检查失败: 向量维度不匹配 (期望=%d, 实际=%d)",
            settings.EMBEDDING_DIMENSIONS,
            len(result),
        )
        return False
    except Exception as e:
        logger.warning("健康检查失败: %s", e)
        return False
