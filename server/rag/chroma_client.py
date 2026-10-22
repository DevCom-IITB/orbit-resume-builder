"""
Shared Chroma collection accessor for the RAG retrieval pipeline.

Loaded once per process (lru_cache), reused across every request — do NOT
reconnect / re-open the persistent client on each API call, that's
unnecessary I/O on the hot path before every LLM generation.

Requires in .env:
    CHROMA_DB_PATH = "..."        # path to your indexed chroma db
    CHROMA_COLLECTION_NAME = "..."  # your collection name
"""

import functools
import os
import chromadb
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

Chroma_db_path=os.getenv("CHROMA_DB_PATH")
Chroma_collection_name=os.getenv("CHROMA_COLLECTION_NAME")

@functools.lru_cache(maxsize=1)
def get_resume_collection():
    client = chromadb.PersistentClient(path=Chroma_db_path)
    return client.get_collection(name=Chroma_collection_name)