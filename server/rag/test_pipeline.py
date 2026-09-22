"""Run the real RAG retrieval pipeline with a custom query.

Run from the server directory:

    python -m rag.test_pipeline \
        --section-key positions_of_responsibility \
        --query "Managed sponsorships and organized finance workshops"

This is an integration test. It uses the persisted Chroma collection and the
real embedding and cross-encoder models; no fake models or test data are used.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any

import chromadb
from dotenv import load_dotenv
from sentence_transformers import CrossEncoder, SentenceTransformer

from rag.retrieval.filtering import SectionKey
from rag.retrieval.main_pipeline import run_retrieval_pipeline


DEFAULT_TOP_N = 20
DEFAULT_TOP_M = 5
DEFAULT_COLLECTION_NAME = "resume_chunks"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L4-v2"
DEFAULT_CHROMA_PATH = str(Path(__file__).resolve().parents[1] / "chroma_db")


def parse_args() -> argparse.Namespace:
    """Parse the custom query and retrieval configuration."""
    parser = argparse.ArgumentParser(
        description="Run real Chroma retrieval and print the top reranked chunks."
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Raw resume content to use as the retrieval query.",
    )
    parser.add_argument(
        "--section-key",
        required=True,
        choices=[section.value for section in SectionKey],
        help="Resume section used for metadata filtering.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=DEFAULT_TOP_N,
        help=f"Number of vector-search candidates, default: {DEFAULT_TOP_N}.",
    )
    parser.add_argument(
        "--top-m",
        type=int,
        default=DEFAULT_TOP_M,
        help=f"Number of reranked chunks to print, default: {DEFAULT_TOP_M}.",
    )
    parser.add_argument(
        "--chroma-path",
        default=os.getenv("CHROMA_DB_PATH", DEFAULT_CHROMA_PATH),
        help="Persistent Chroma path; defaults to CHROMA_DB_PATH or server/chroma_db.",
    )
    parser.add_argument(
        "--collection",
        default=os.getenv("CHROMA_COLLECTION_NAME", DEFAULT_COLLECTION_NAME),
        help="Chroma collection name; defaults to CHROMA_COLLECTION_NAME.",
    )
    parser.add_argument(
        "--embedding-model",
        default=DEFAULT_EMBEDDING_MODEL,
        help=f"SentenceTransformer model, default: {DEFAULT_EMBEDDING_MODEL}.",
    )
    parser.add_argument(
        "--reranker-model",
        default=DEFAULT_RERANKER_MODEL,
        help=f"CrossEncoder model, default: {DEFAULT_RERANKER_MODEL}.",
    )
    return parser.parse_args()


def load_real_models(
    embedding_model_name: str,
    reranker_model_name: str,
) -> tuple[SentenceTransformer, CrossEncoder]:
    """Load the real embedding and reranking models from Hugging Face."""
    hf_token = os.getenv("HUGGINGFACE_ACCESS_TOKEN") or os.getenv("HF_TOKEN")
    embedding_encoder = SentenceTransformer(embedding_model_name, token=hf_token)
    reranker = CrossEncoder(reranker_model_name, token=hf_token)
    return embedding_encoder, reranker


def get_collection(chroma_path: str | None, collection_name: str):
    """Open the persisted Chroma collection and fail clearly if misconfigured."""
    if not chroma_path:
        raise RuntimeError(
            "CHROMA_DB_PATH is not configured. Set it in server/.env or pass --chroma-path."
        )

    client = chromadb.PersistentClient(path=chroma_path)
    try:
        collection = client.get_collection(name=collection_name)
    except Exception as exc:
        available = [item.name for item in client.list_collections()]
        raise RuntimeError(
            f"Could not open Chroma collection '{collection_name}'. "
            f"Available collections: {available}"
        ) from exc

    return collection


def run_test(args: argparse.Namespace) -> dict[str, Any]:
    """Run retrieval against the real persisted Chroma data."""
    if args.top_n < 1 or args.top_m < 1 or args.top_m > args.top_n:
        raise ValueError("Require top_n >= top_m >= 1.")

    collection = get_collection(args.chroma_path, args.collection)
    chunk_count = collection.count()
    if chunk_count == 0:
        raise RuntimeError(
            f"Chroma collection '{args.collection}' is empty. Run ingestion first."
        )

    embedding_encoder, reranker = load_real_models(
        args.embedding_model,
        args.reranker_model,
    )

    result = run_retrieval_pipeline(
        query=args.query,
        section_key=args.section_key,
        chroma_collection=collection,
        top_n=args.top_n,
        top_m=args.top_m,
        encoder=embedding_encoder,
        _cross_encoder=reranker,
    )

    return {
        "query": args.query,
        "section_key": args.section_key,
        "collection": args.collection,
        "collection_count": chunk_count,
        "top_n": args.top_n,
        "top_m": args.top_m,
        "retrieved_context": result.get("retrieved_context", []),
    }


def main() -> None:
    """Load configuration, execute retrieval, and print JSON results."""
    load_dotenv()
    args = parse_args()
    result = run_test(args)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
