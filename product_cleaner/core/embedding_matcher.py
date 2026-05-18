"""
Embedding 语义匹配器（单例 + 缓存）

用于 Phase 5 L3 dedup 辅助判断：
  - 字面 token/子串匹配后的语义验证
  - token_set + 语义相似度兜底子串匹配的误判

模型: BAAI/bge-base-zh-v1.5
首次使用自动下载到 ~/.cache/huggingface/hub/
"""

import numpy as np
from functools import lru_cache

# 缓存: L3 名称 → embedding 向量
_embed_cache = {}
_model = None


def _ensure_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('BAAI/bge-base-zh-v1.5')
    return _model


def l3_similarity(a: str, b: str) -> float:
    """
    返回两个 L3 名称的余弦相似度 (0~1)。
    带 embedding 缓存，重复调用不重复编码。
    """
    model = _ensure_model()
    for t in (a, b):
        if t not in _embed_cache:
            _embed_cache[t] = model.encode(t)

    emb_a = _embed_cache[a]
    emb_b = _embed_cache[b]
    dot = np.dot(emb_a, emb_b)
    norm = np.linalg.norm(emb_a) * np.linalg.norm(emb_b)
    return float(dot / norm) if norm > 0 else 0.0


def is_l3_related(a: str, b: str, threshold: float = 0.55) -> bool:
    """
    语义阈值判断：a 与 b 是否属于同品类。
    高于 threshold 认为应合并，低于则不合并。
    """
    return l3_similarity(a, b) >= threshold


def clear_cache():
    """清空 embedding 缓存（诊断期间通常不调用）"""
    _embed_cache.clear()
