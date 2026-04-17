"""
Qwen3 嵌入模型模块

实现 Qwen3-Embedding-8B 等需要 last-token 池化方式的嵌入模型，
直接继承 LangChain Embeddings 接口。
"""

import logging

import torch
import torch.nn.functional as F  # noqa: N812
from langchain_core.embeddings import Embeddings as LCEmbeddings
from torch import Tensor
from transformers import AutoModel, AutoTokenizer

# from apps.config import settings

logger = logging.getLogger(__name__)


def last_token_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    """最后 token 池化"""
    left_padding = attention_mask[:, -1].sum() == attention_mask.shape[0]
    if left_padding:
        return last_hidden_states[:, -1]
    else:
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        return last_hidden_states[
            torch.arange(batch_size, device=last_hidden_states.device),
            sequence_lengths,
        ]


class Qwen3EmbeddingModel(LCEmbeddings):
    """Qwen3-Embedding-8B 专用嵌入模型，直接实现 LangChain Embeddings 接口"""

    DEFAULT_TASK = "Given a web search query, retrieve relevant passages that answer the query"

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-Embedding-0.6B",
        device: str = "auto",
        max_length: int = 8192,
        truncate_dim: int | None = None,
        use_flash_attention: bool = False,
    ):
        self.model_name = model_name
        self.device = device if device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
        self.max_length = max_length
        self.truncate_dim = truncate_dim
        self.use_flash_attention = use_flash_attention

        self._tokenizer: AutoTokenizer | None = None
        self._model: AutoModel | None = None

    def _get_model_kwargs(self) -> dict:
        """获取模型加载参数"""
        kwargs = {"trust_remote_code": True}
        if self.use_flash_attention and self.device == "cuda":
            kwargs["attn_implementation"] = "flash_attention_2"
            kwargs["torch_dtype"] = torch.float16
        return kwargs

    def load(self):
        """加载模型和分词器（首次自动下载到缓存目录）"""
        if self._tokenizer is None:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                padding_side="left",
                trust_remote_code=True,
            )

        if self._model is None:
            self._model = AutoModel.from_pretrained(self.model_name, **self._get_model_kwargs())
            self._model.to(self.device)
            self._model.eval()

        logger.info("模型加载成功: %s", self.model_name)
        logger.info("设备: %s", self.device)
        return self

    def _prepare_input(self, texts: list[str], task: str = None) -> dict:
        """准备输入数据"""
        if task is None:
            task = self.DEFAULT_TASK
        queries = [f"Instruct: {task}\nQuery: {text}" for text in texts]
        batch_dict = self._tokenizer(
            queries,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        batch_dict.to(self.device)
        return batch_dict

    def embed_query(self, text: str, task: str = None) -> list[float]:
        """嵌入单个查询"""
        return self.embed_queries([text], task)[0]

    def embed_queries(self, texts: list[str], task: str = None) -> list[list[float]]:
        """嵌入多个查询"""
        if not texts:
            return []
        self.load()
        batch_dict = self._prepare_input(texts, task)
        outputs = self._model(**batch_dict)
        embeddings = last_token_pool(outputs.last_hidden_state, batch_dict["attention_mask"])
        embeddings = F.normalize(embeddings, p=2, dim=1)
        if self.truncate_dim:
            embeddings = embeddings[:, : self.truncate_dim]
        return embeddings.cpu().tolist()

    def embed_document(self, text: str) -> list[float]:
        """嵌入单个文档（无需指令前缀）"""
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """嵌入多个文档（无需指令前缀）"""
        if not texts:
            return []
        self.load()
        batch_dict = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        batch_dict.to(self.device)
        outputs = self._model(**batch_dict)
        embeddings = last_token_pool(outputs.last_hidden_state, batch_dict["attention_mask"])
        embeddings = F.normalize(embeddings, p=2, dim=1)
        if self.truncate_dim:
            embeddings = embeddings[:, : self.truncate_dim]
        return embeddings.cpu().tolist()

    def __call__(self, text: str) -> list[float]:
        """支持直接调用"""
        return self.embed_query(text)


def main():
    model = Qwen3EmbeddingModel()
    test_queries = [
        "什么是人工智能？",
        "Python 编程语言的特点",
        "机器学习和深度学习的区别",
    ]
    test_document = "人工智能是计算机科学的一个分支，致力于开发能够执行通常需要人类智能的任务的系统。这包括视觉感知、语音识别、决策制定和语言翻译等。"

    doc_result = model.embed_document(test_document)

    print(f"文档长度: {len(test_document)} 字符")
    print(f"向量维度: {len(doc_result)}")
    result = model.embed_query(test_queries[0])

    print(f"输入: {test_queries[0]}")
    print(f"向量维度: {len(result)}")
    print(f"result: {result}")


if __name__ == "__main__":
    main()
