"""BM25 lexical retrieval over chunks already stored in Chroma."""

from typing import Any, Dict, List, Optional
import re

from rank_bm25 import BM25Okapi

from .filtering import build_metadata_filter


# Number of lexical candidates added to the semantic candidate pool.
BM25_TOP_N = 20


def _tokenize(text: str) -> List[str]:
    """Keep identifiers such as DS203, CS101, React.js, and C++ searchable."""
    return re.findall(r"[A-Za-z0-9]+(?:[._+#-][A-Za-z0-9]+)*", text.lower())


def retrieve_bm25_chunks(
    chroma_collection,
    query: str,
    section_key: str,
    top_n: int = BM25_TOP_N,
    extra_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Retrieve exact-term matches from the section-filtered Chroma corpus."""
    if top_n < 1:
        return []

    where_filter = build_metadata_filter(
        section_key,
        extra_filters=extra_filters,
        backend="chroma",
    )
    corpus = chroma_collection.get(
        where=where_filter,
        include=["documents", "metadatas"],
    )

    documents = corpus.get("documents") or []
    metadatas = corpus.get("metadatas") or []
    ids = corpus.get("ids") or []

    if not documents or not _tokenize(query):
        return []

    searchable_documents = [
        f"{metadata.get('entry_title', '')} {document}"
        for document, metadata in zip(documents, metadatas)
    ]
    tokenized_corpus = [_tokenize(document) for document in searchable_documents]
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(_tokenize(query))

    ranked_indexes = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True,
    )[:top_n]

    return [
        {
            "id": ids[index] if index < len(ids) else None,
            "chunk": documents[index],
            "metadata": metadatas[index],
            "bm25_score": float(scores[index]),
        }
        for index in ranked_indexes
    ]