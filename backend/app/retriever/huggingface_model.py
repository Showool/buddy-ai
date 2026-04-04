"""
HuggingFace 嵌入模型工厂

根据模型名称选择合适的嵌入实现：
- Qwen3 系列 -> Qwen3EmbeddingModel
- 其他模型 -> 标准 HuggingFaceEmbeddings
"""

import logging
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)


def get_huggingface_embeddings(
    model_name: Optional[str] = None,
    device: Optional[str] = None,
    truncate_dim: Optional[int] = None,
):
    """
    获取 HuggingFace 嵌入模型

    Args:
        model_name: HuggingFace 模型名称
        device: 设备 "cpu" / "cuda" / "auto"
        truncate_dim: 向量维度截断

    Returns:
        实现 LangChain Embeddings 接口的嵌入模型实例
    """
    model_name = model_name or settings.HF_MODEL_NAME
    device = device or settings.HF_DEVICE
    truncate_dim = truncate_dim or settings.EMBEDDING_DIMENSIONS

    # 检查是否需要使用 Qwen3 专用模型
    special_models = ["Qwen3-Embedding-8B", "Qwen3-Embedding-8B-Fix", "gte-Qwen2-7B-instruct"]
    is_special = any(name in model_name for name in special_models)

    if is_special or "Qwen3" in model_name:
        try:
            from .qwen3_embedding import Qwen3EmbeddingModel

            model = Qwen3EmbeddingModel(
                model_name=model_name,
                device=device,
                truncate_dim=truncate_dim,
            )
            model.load()
            return model
        except Exception as e:
            raise RuntimeError(
                f"HuggingFace 模型加载失败: {model_name}。原始错误: {e}"
            ) from e

    # 使用标准 HuggingFaceEmbeddings
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device},
            encode_kwargs={
                "truncate_dim": truncate_dim,
                "normalize_embeddings": True,
            },
        )
    except Exception as e:
        raise RuntimeError(
            f"HuggingFace 模型加载失败: {model_name}。原始错误: {e}"
        ) from e
