"""
Main retrieval pipeline for the AI Resume Builder RAG module.

Chains: clean+embed query -> metadata filter + vector search -> cross-encoder
rerank -> structured JSON context for the prompt builder.

This is the single entry point the prompt builder should call.
"""

from typing import Any, Dict, List, Optional

from sentence_transformers import SentenceTransformer,CrossEncoder

from .query import process_query
from .filtering import retrieve_top_k_chunks
from .bm25 import BM25_TOP_N, retrieve_bm25_chunks
from .re_ranker import rerank_chunks
from dotenv import load_dotenv
# ---------------------------------------------------------------------------
# Shared model config — change model names here only, loaded ONCE at import
# time and reused across every pipeline call. Do not re-instantiate inside
# run_retrieval_pipeline() — that reloads weights per request (slow).
# ---------------------------------------------------------------------------
load_dotenv()  # Load environment variables from .env file
#automatically loads the HF_token from the .env file if present, so we don't have to pass it explicitly to the model constructors

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
_embedding_encoder = SentenceTransformer(EMBEDDING_MODEL_NAME)
CROSS_ENCODER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L4-v2"
_cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL_NAME)


def run_retrieval_pipeline(
    query: str,
    section_key: str,
    chroma_collection,
    top_n: int = 20,
    top_m: int = 5,
    extra_filters: Optional[Dict[str, Any]] = None,
    encoder: Optional[SentenceTransformer] = None,
    _cross_encoder: Optional[CrossEncoder] = None,
) -> Dict[str, Any]:
    """
    Full RAG retrieval pipeline.

    Args:
        query: raw resume section text from the user (not a question).
        section_key: one of SectionKey values in filtering.py.
        chroma_collection: chroma collection instance to query against.
        top_n: candidates pulled from vector search before rerank.
        top_m: final chunks returned after rerank.
        extra_filters: optional additional metadata equality filters.
        encoder: override shared embedding model (mainly for tests).

    Returns:
        {
            "retrieved_context": [
                {
                    "entry_title": str,
                    "section_key": str,
                    "chunk": str,
                    "score": float
                },
                ...
            ]
        }
    """
    active_encoder = encoder or _embedding_encoder

    cleaned_query, query_embedding = process_query(query, encoder=active_encoder)

    if not cleaned_query or not query_embedding:
        return {"retrieved_context": []}

    semantic_candidates = retrieve_top_k_chunks(
        chroma_collection=chroma_collection,
        query_embedding=query_embedding,
        section_key=section_key,
        top_k=top_n,
        extra_filters=extra_filters,
    )

    bm25_candidates = retrieve_bm25_chunks(
        chroma_collection=chroma_collection,
        query=cleaned_query,
        section_key=section_key,
        top_n=BM25_TOP_N,
        extra_filters=extra_filters,
    )

    candidates_by_id = {}
    for candidate in [*semantic_candidates, *bm25_candidates]:
        candidate_id = candidate.get("id")
        if candidate_id is None:
            candidate_id = candidate["chunk"]
        existing = candidates_by_id.get(candidate_id)
        if existing is None:
            candidates_by_id[candidate_id] = candidate
        elif "bm25_score" in candidate:
            existing["bm25_score"] = candidate["bm25_score"]

    candidates = list(candidates_by_id.values())

    if not candidates:
        return {"retrieved_context": []}

    reranked = rerank_chunks(
        query_text=cleaned_query,
        candidates=candidates,
        top_m=top_m,
        cross_encoder=_cross_encoder,
    )

    retrieved_context: List[Dict[str, Any]] = [
        {
            "entry_title": r["metadata"].get("entry_title"),
            "section_key": r["metadata"].get("section_key"),
            "chunk": r["chunk"],
            "score": round(r["rerank_score"], 4),
        }
        for r in reranked
    ]

    return {"retrieved_context": retrieved_context}