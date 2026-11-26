"""
End-to-end test suite for the resume RAG pipeline.

Covers: filtering (section_key validation + backend filters), reranker
(score reordering), query_processing (cleaning + embedding), and the full
run_retrieval_pipeline() chain.

Stubs sentence_transformers so this runs fully offline — no model download,
no HF Hub access needed. Real chroma is used (in-memory, real vector math).

Run:
    pip install pytest chromadb
    pytest test_rag.py -v
"""

import sys
import types

import pytest

# ---------------------------------------------------------------------------
# Stub sentence_transformers BEFORE importing rag_pipeline — pipeline.py and
# query_processing.py import SentenceTransformer at module load time.
# ---------------------------------------------------------------------------

FAKE_EMBEDDINGS = {
    "Built a full-stack website using FastAPI, React, PostgreSQL and Docker.": [0.9, 0.1, 0.0],
    "Built a full-stack web app using FastAPI, React and PostgreSQL": [0.9, 0.1, 0.0],
    "Deployed backend services to production using Docker and Cloud Run": [0.85, 0.15, 0.0],
    "Modelled option pricing using Black-Scholes in Python": [0.1, 0.9, 0.0],
    "hello world": [0.5, 0.5, 0.0],
}


class FakeArray(list):
    def tolist(self):
        return list(self)


class FakeSentenceTransformer:
    def __init__(self, model_name, *args, **kwargs):
        self.model_name = model_name

    def encode(self, text, convert_to_numpy=True):
        return FakeArray(FAKE_EMBEDDINGS.get(text, [0.0, 0.0, 0.0]))


class FakeCrossEncoder:
    """Lexical-overlap stand-in for cross-encoder/ms-marco-MiniLM — no download."""

    def __init__(self, model_name):
        self.model_name = model_name

    def predict(self, pairs):
        scores = []
        for query, chunk in pairs:
            q_words = set(query.lower().split())
            c_words = set(chunk.lower().split())
            scores.append(float(len(q_words & c_words)))
        return scores


fake_module = types.ModuleType("sentence_transformers")
fake_module.SentenceTransformer = FakeSentenceTransformer
fake_module.CrossEncoder = FakeCrossEncoder
# Remember the real entry (if already imported) so it can be put back below:
# pytest imports every test module before running any test, so leaving the
# fake in sys.modules made other tests (rag/tests.py) get 3-dim "embeddings".
_real_sentence_transformers = sys.modules.get("sentence_transformers")
sys.modules["sentence_transformers"] = fake_module

# ---------------------------------------------------------------------------
# Now safe to import the real pipeline modules
# ---------------------------------------------------------------------------
import chromadb  # noqa: E402

from rag.retrieval.filtering import (  # noqa: E402
    validate_section_key,
    build_metadata_filter,
    UnsupportedSectionKeyError,
    UnsupportedBackendError,
    retrieve_top_k_chunks,
)
from rag.retrieval.re_ranker import rerank_chunks  # noqa: E402
from rag.retrieval.query import clean_query, process_query  # noqa: E402
from rag.retrieval.main_pipeline import run_retrieval_pipeline  # noqa: E402


def _restore_sentence_transformers():
    if _real_sentence_transformers is None:
        sys.modules.pop("sentence_transformers", None)
    else:
        sys.modules["sentence_transformers"] = _real_sentence_transformers


_restore_sentence_transformers()


@pytest.fixture(autouse=True, scope="module")
def _fake_sentence_transformers():
    """Re-install the stub only while this module's tests run (the re-ranker
    imports CrossEncoder lazily, at call time)."""
    sys.modules["sentence_transformers"] = fake_module
    yield
    _restore_sentence_transformers()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CHUNKS = [
    ("Built a full-stack web app using FastAPI, React and PostgreSQL",
     {"entry_title": "Project Lead | Dev Community", "section_key": "key_projects"},
     [0.9, 0.1, 0.0]),
    ("Deployed backend services to production using Docker and Cloud Run",
     {"entry_title": "Project Lead | Dev Community", "section_key": "key_projects"},
     [0.85, 0.15, 0.0]),
    ("Modelled option pricing using Black-Scholes in Python",
     {"entry_title": "Option Pricing | Finsearch", "section_key": "key_projects"},
     [0.1, 0.9, 0.0]),
    ("Managed sponsorships worth 3 lakh INR for annual fest",
     {"entry_title": "Convener | Finance Club", "section_key": "positions_of_responsibility"},
     [0.0, 0.2, 0.9]),
]


@pytest.fixture
def chroma_collection():
    client = chromadb.Client()  # fresh in-memory client per test
    collection = client.get_or_create_collection(name="test_resumes")

    ids = [f"chunk_{i}" for i in range(len(SAMPLE_CHUNKS))]
    docs = [c[0] for c in SAMPLE_CHUNKS]
    metas = [c[1] for c in SAMPLE_CHUNKS]
    embeds = [c[2] for c in SAMPLE_CHUNKS]

    collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeds)
    return collection


# ---------------------------------------------------------------------------
# filtering.py
# ---------------------------------------------------------------------------

def test_validate_section_key_valid():
    assert validate_section_key("key_projects") == "key_projects"


def test_validate_section_key_invalid_raises():
    with pytest.raises(UnsupportedSectionKeyError):
        validate_section_key("not_a_real_section")


def test_build_metadata_filter_chroma_single_condition():
    f = build_metadata_filter("key_projects", backend="chroma")
    assert f == {"section_key": "key_projects"}


def test_build_metadata_filter_chroma_multi_condition_uses_and():
    f = build_metadata_filter("key_projects", {"domain": "finance"}, backend="chroma")
    assert f == {"$and": [{"section_key": "key_projects"}, {"domain": "finance"}]}


def test_build_metadata_filter_pgvector():
    f = build_metadata_filter("courses", backend="pgvector")
    assert f["where_sql"] == "metadata->>'section_key' = %(section_key)s"
    assert f["params"] == {"section_key": "courses"}


def test_build_metadata_filter_unsupported_backend_raises():
    with pytest.raises(UnsupportedBackendError):
        build_metadata_filter("courses", backend="not_a_real_backend")


def test_retrieve_top_k_chunks_filters_by_section_key(chroma_collection):
    results = retrieve_top_k_chunks(
        chroma_collection=chroma_collection,
        query_embedding=[0.9, 0.1, 0.0],
        section_key="key_projects",
        top_k=10,
    )
    # only 3 of 4 seeded chunks are key_projects — PoR chunk must be excluded
    assert len(results) == 3
    assert all(r["metadata"]["section_key"] == "key_projects" for r in results)


def test_retrieve_top_k_chunks_ranks_closest_first(chroma_collection):
    results = retrieve_top_k_chunks(
        chroma_collection=chroma_collection,
        query_embedding=[0.9, 0.1, 0.0],
        section_key="key_projects",
        top_k=10,
    )
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# reranker.py
# ---------------------------------------------------------------------------

def test_rerank_chunks_empty_input_returns_empty():
    assert rerank_chunks("some query", [], top_m=5) == []


def test_rerank_chunks_reorders_and_truncates():
    candidates = [
        {"chunk": "Deployed on Docker", "metadata": {}, "score": 0.9},
        {"chunk": "Built FastAPI backend with PostgreSQL", "metadata": {}, "score": 0.5},
        {"chunk": "Wrote unit tests", "metadata": {}, "score": 0.8},
    ]
    out = rerank_chunks(
        query_text="Built a full-stack website using FastAPI, React, PostgreSQL and Docker.",
        candidates=candidates,
        top_m=2,
        cross_encoder=FakeCrossEncoder("fake"),
    )
    assert len(out) == 2
    # FastAPI/PostgreSQL chunk has more word overlap with query -> should rank first
    assert out[0]["chunk"] == "Built FastAPI backend with PostgreSQL"
    assert "rerank_score" in out[0]
    assert out[0]["score"] == 0.5  # original vector score preserved, not overwritten


# ---------------------------------------------------------------------------
# query_processing.py
# ---------------------------------------------------------------------------

def test_clean_query_collapses_whitespace_and_strips_controls():
    dirty = "Hello,\n\n  world!\t\t This  is\r a test."
    cleaned = clean_query(dirty)
    assert cleaned == "Hello, world! This is a test."


def test_clean_query_empty_input():
    assert clean_query("") == ""
    assert clean_query("   ") == ""


def test_process_query_empty_returns_empty_embedding():
    cleaned, embedding = process_query("   ", encoder=FakeSentenceTransformer("fake"))
    assert cleaned == ""
    assert embedding == []


def test_process_query_returns_cleaned_text_and_embedding():
    cleaned, embedding = process_query("hello world", encoder=FakeSentenceTransformer("fake"))
    assert cleaned == "hello world"
    assert embedding == [0.5, 0.5, 0.0]


# ---------------------------------------------------------------------------
# Full pipeline — end to end
# ---------------------------------------------------------------------------

def test_full_pipeline_end_to_end(chroma_collection):
    result = run_retrieval_pipeline(
        query="Built a full-stack website using FastAPI, React, PostgreSQL and Docker.",
        section_key="key_projects",
        chroma_collection=chroma_collection,
        top_n=10,
        top_m=2,
        encoder=FakeSentenceTransformer("fake"),
    )

    assert "retrieved_context" in result
    context = result["retrieved_context"]
    assert len(context) == 2

    for item in context:
        assert set(item.keys()) == {"entry_title", "section_key", "chunk", "score"}
        assert item["section_key"] == "key_projects"

    # FastAPI/PostgreSQL chunk should win rerank due to lexical overlap with query
    assert context[0]["chunk"] == "Built a full-stack web app using FastAPI, React and PostgreSQL"


def test_full_pipeline_empty_query_returns_empty_context(chroma_collection):
    result = run_retrieval_pipeline(
        query="   ",
        section_key="key_projects",
        chroma_collection=chroma_collection,
        encoder=FakeSentenceTransformer("fake"),
    )
    assert result == {"retrieved_context": []}


def test_full_pipeline_invalid_section_key_raises(chroma_collection):
    with pytest.raises(UnsupportedSectionKeyError):
        run_retrieval_pipeline(
            query="Some project text",
            section_key="not_a_real_section",
            chroma_collection=chroma_collection,
            encoder=FakeSentenceTransformer("fake"),
        )