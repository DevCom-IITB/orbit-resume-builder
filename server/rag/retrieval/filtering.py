"""
Metadata filtering layer for the resume RAG retrieval pipeline.

Responsibility: build a validated metadata filter (currently on section_key,
extensible to domain/company/resume_type/etc.) BEFORE vector similarity search.
This module does NOT perform embedding generation or vector search itself —
it only produces the filter object the search call consumes.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Supported section types
# ---------------------------------------------------------------------------

class SectionKey(str, Enum):
    POSITIONS_OF_RESPONSIBILITY = "positions_of_responsibility"
    PROFESSIONAL_EXPERIENCE = "professional_experience"
    KEY_PROJECTS = "key_projects"
    COURSES = "courses"


class UnsupportedSectionKeyError(ValueError):
    """Raised when caller passes a section_key outside the supported enum."""

    def __init__(self, provided: str, allowed: Set[str]):
        self.provided = provided
        self.allowed = allowed
        super().__init__(
            f"Unsupported section_key '{provided}'. "
            f"Must be one of: {sorted(allowed)}"
        )


class UnsupportedBackendError(ValueError):
    """Raised when caller passes a vector-db backend we don't build filters for."""

    def __init__(self, backend: str):
        super().__init__(
            f"Unsupported backend '{backend}'. Use 'qdrant', 'pgvector', or 'chroma'."
        )


def validate_section_key(section_key: str) -> str:
    """Validate section_key against the supported enum. Returns the value if valid."""
    allowed = {s.value for s in SectionKey}
    if section_key not in allowed:
        raise UnsupportedSectionKeyError(section_key, allowed)
    return section_key


# ---------------------------------------------------------------------------
# Generic filter builder
# ---------------------------------------------------------------------------

def build_metadata_filter(
    section_key: str,
    extra_filters: Optional[Dict[str, Any]] = None,
    backend: str = "qdrant",
):
    """
    Build a metadata filter for vector search.

    Args:
        section_key: required, validated against SectionKey enum.
        extra_filters: optional equality filters, e.g. {"domain": "finance",
            "company": "Accenture"}. Lets you add new filterable metadata
            fields later without changing this function's signature.
        backend: "qdrant" (default) or "pgvector".

    Returns:
        - backend="qdrant"   -> qdrant_client.models.Filter object
        - backend="pgvector" -> dict {"where_sql": str, "params": dict}

    Raises:
        UnsupportedSectionKeyError, UnsupportedBackendError
    """
    section_key = validate_section_key(section_key)

    conditions: Dict[str, Any] = {"section_key": section_key}
    if extra_filters:
        conditions.update(extra_filters)

    
    if backend == "pgvector":
        return _build_pgvector_filter(conditions)
    elif backend == "chroma":
        return _build_chroma_filter(conditions)
    else:
        raise UnsupportedBackendError(backend)





def _build_pgvector_filter(conditions: Dict[str, Any]):
    """
    Assumes metadata stored as a JSONB column named `metadata` on the chunks
    table. Adjust the column name in one place if your schema differs.
    """
    where_clauses = []
    params: Dict[str, Any] = {}

    for key, value in conditions.items():
        where_clauses.append(f"metadata->>'{key}' = %({key})s")
        params[key] = value

    return {
        "where_sql": " AND ".join(where_clauses),
        "params": params,
    }


def _build_chroma_filter(conditions: Dict[str, Any]):
    """
    Chroma's `where` filter is a plain dict. Single condition -> flat dict.
    Multiple conditions -> wrap in $and (works across chroma versions,
    unlike relying on implicit multi-key AND).
    """
    if len(conditions) == 1:
        key, value = next(iter(conditions.items()))
        return {key: value}

    return {"$and": [{key: value} for key, value in conditions.items()]}



# ---------------------------------------------------------------------------
# Example usage inside a retrieval call (pgvector, psycopg2-style)
# ---------------------------------------------------------------------------

def search_candidates_pgvector(
    db_connection,
    table_name: str,
    query_embedding: List[float],
    section_key: str,
    top_n: int = 20,
    extra_filters: Optional[Dict[str, Any]] = None,
):
    """Metadata-filtered vector search on Postgres + pgvector."""
    filt = build_metadata_filter(section_key, extra_filters, backend="pgvector")

    sql = f"""
        SELECT id, chunk_text, metadata,
               1 - (embedding <=> %(query_embedding)s) AS score
        FROM {table_name}
        WHERE {filt["where_sql"]}
        ORDER BY embedding <=> %(query_embedding)s
        LIMIT %(top_n)s
    """
    params = {**filt["params"], "query_embedding": query_embedding, "top_n": top_n}

    with db_connection.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


# ---------------------------------------------------------------------------
# Example usage inside a retrieval call (Chroma)
# ---------------------------------------------------------------------------

def search_candidates_chroma(
    chroma_collection,
    query_embedding: List[float],
    section_key: str,
    top_n: int = 20,
    extra_filters: Optional[Dict[str, Any]] = None,
):
    """
    Metadata-filtered vector search on a Chroma collection.
    `chroma_collection` = result of client.get_collection(name=...).
    """
    where_filter = build_metadata_filter(section_key, extra_filters, backend="chroma")

    return chroma_collection.query(
        query_embeddings=[query_embedding],
        where=where_filter,
        n_results=top_n,
        include=["documents", "metadatas", "distances"],
    )


def retrieve_top_k_chunks(
    chroma_collection,
    query_embedding: List[float],
    section_key: str,
    top_k: int = 20,
    extra_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Full step: metadata-narrow (section_key + extra_filters) -> vector
    similarity search on chunk embeddings -> top_k clean results.

    Returns list of dicts, sorted best-first:
        {"chunk": str, "metadata": dict, "score": float}

    Note: Chroma returns cosine *distance*; converted here to similarity
    score (score = 1 - distance) so higher = more relevant.
    """
    raw = search_candidates_chroma(
        chroma_collection=chroma_collection,
        query_embedding=query_embedding,
        section_key=section_key,
        top_n=top_k,
        extra_filters=extra_filters,
    )

    ids = raw["ids"][0]
    documents = raw["documents"][0]
    metadatas = raw["metadatas"][0]
    distances = raw["distances"][0]

    results = [
        {"id": chunk_id, "chunk": doc, "metadata": meta, "score": 1 - dist}
        for chunk_id, doc, meta, dist in zip(ids, documents, metadatas, distances)
    ]

    # already ordered by Chroma (closest first), but sort explicitly to be safe
    results.sort(key=lambda r: r["score"], reverse=True)
    return results