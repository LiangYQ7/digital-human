"""ChromaDB 向量库封装。

提供统一的 collection 获取接口，默认使用 bge-m3 嵌入模型。
"""
import os
from pathlib import Path

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

# 加载 .env（确保 HF_ENDPOINT 等变量生效）
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

_CLIENT = None
_EMBEDDING_FN = None
_COLLECTION = None

# 默认嵌入模型（中文效果最好的开源模型之一，赛题 RAG 核心）
DEFAULT_EMBED_MODEL = "BAAI/bge-m3"
COLLECTION_NAME = "scenic_kb"


def _get_client() -> chromadb.PersistentClient:
    global _CLIENT
    if _CLIENT is None:
        path = os.getenv("CHROMA_PATH", "brain/data/chroma")
        Path(path).mkdir(parents=True, exist_ok=True)
        _CLIENT = chromadb.PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False),
        )
    return _CLIENT


def _get_embedding_fn() -> embedding_functions.SentenceTransformerEmbeddingFunction:
    global _EMBEDDING_FN
    if _EMBEDDING_FN is None:
        model = os.getenv("EMBED_MODEL", DEFAULT_EMBED_MODEL)
        # 本地优先：如果 ModelScope 缓存存在就直接用，不走网络
        local_path = Path("D:/huggingface_models/models/BAAI--bge-m3/snapshots/master")
        model_name = str(local_path) if local_path.exists() else model
        _EMBEDDING_FN = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name,
        )
    return _EMBEDDING_FN


def get_collection() -> chromadb.Collection:
    """获取（或创建）景区知识库 collection。

    首次调用会自动加载 bge-m3 模型。
    """
    global _COLLECTION
    if _COLLECTION is None:
        _COLLECTION = _get_client().get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=_get_embedding_fn(),
            metadata={"description": "景区导览数字人知识库"},
        )
    return _COLLECTION


def reset_collection():
    """清空并重建 collection（用于重新入库）。"""
    global _COLLECTION
    try:
        _get_client().delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    _COLLECTION = None
    return get_collection()
