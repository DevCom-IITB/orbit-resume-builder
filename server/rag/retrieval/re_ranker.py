"""
Reranking layer for the resume RAG retrieval pipeline.

Input: list of candidate chunks from filtering.retrieve_top_k_chunks()
       -> [{"chunk": str, "metadata": dict, "score": float}, ...]

Responsibility: cross-encoder rerank each candidate against the original
query text, attach a `rerank_score`, and return the top_m best chunks.
Does NOT do vector search, filtering, or LLM calls.
"""

import functools
from typing import Any, Dict, List, Optional

DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L4-v2"


@functools.lru_cache(maxsize=None)
def _load_cross_encoder(model_name: str):
    """
    Cached model load — CrossEncoder loaded once per process per model_name,
    reused across every rerank_chunks() call. Avoids reloading weights
    (slow, GBs of I/O) on every request.
    """
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name)


def rerank_chunks(
    query_text: str,
    candidates: List[Dict[str, Any]],
    top_m: int = 5,
    model_name: str = DEFAULT_RERANKER_MODEL,
    cross_encoder: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Args:
        query_text: the raw resume section text (original query, not embedding).
        candidates: output of retrieve_top_k_chunks(). Each dict keeps its
            existing keys ("chunk", "metadata", "score") — rerank_score
            added on top, nothing overwritten.
        top_m: how many best chunks to return after reranking.
        model_name: cross-encoder checkpoint. Default ms-marco-MiniLM-L-6-v2.
        cross_encoder: optional pre-loaded CrossEncoder instance (mainly for
            tests / dependency injection). If not given, cached loader used.

    Returns:
        Top_m candidates, sorted by rerank_score desc. Each dict now has:
            {"chunk": str, "metadata": dict, "score": float, "rerank_score": float}
    """
    if not candidates:
        return []

    encoder = cross_encoder or _load_cross_encoder(model_name)

    # Batch predict — one forward pass over all pairs, not N separate calls.
    pairs = [(query_text, c["chunk"]) for c in candidates]
    scores = encoder.predict(pairs)

    reranked = [
        {**cand, "rerank_score": float(score)}
        for cand, score in zip(candidates, scores)
    ]

    reranked.sort(key=lambda r: r["rerank_score"], reverse=True)
    return reranked[:top_m]


# ---------------------------------------------------------------------------
# Full pipeline glue example: retrieval_filters -> reranker
# ---------------------------------------------------------------------------

def retrieve_and_rerank(
    chroma_collection,
    query_text: str,
    query_embedding: List[float],
    section_key: str,
    top_n: int = 20,
    top_m: int = 5,
    extra_filters: Optional[Dict[str, Any]] = None,
    model_name: str = DEFAULT_RERANKER_MODEL,
):
    """
    Convenience wrapper chaining the two stages:
    1. retrieve_top_k_chunks() — metadata filter + vector sim search, top_n
    2. rerank_chunks()         — cross-encoder rerank, top_m

    top_n should be > top_m (e.g. 20 -> 5) so reranker has real candidates
    to sort through, not just re-confirm the vector search order.
    """
    from .filtering import retrieve_top_k_chunks

    candidates = retrieve_top_k_chunks(
        chroma_collection=chroma_collection,
        query_embedding=query_embedding,
        section_key=section_key,
        top_k=top_n,
        extra_filters=extra_filters,
    )

    return rerank_chunks(
        query_text=query_text,
        candidates=candidates,
        top_m=top_m,
        model_name=model_name,
    )