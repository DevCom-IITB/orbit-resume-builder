# import re
# import unicodedata
# from typing import Tuple, List

# import numpy as np
# from sentence_transformers import SentenceTransformer

# # Load model once at module level 
# _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


# def clean_query(text: str) -> str:
#     """Cleans raw resume text by normalizing unicode and whitespace."""
#     if not text or not text.strip():
#         return ""
    
#     text = unicodedata.normalize("NFKC", text)
   
#     text = re.sub(r"[\r\n\t]+", " ", text)
#     text = re.sub(r"[^\w\s.,;:!?\"\'\-+()/%$₹#&@]", " ", text)
#     text = re.sub(r"\s+", " ", text)
    
#     return text.strip()


# def get_query_embedding(raw_query: str) -> Tuple[str, List[float]]:
#     """Cleans the query and returns the cleaned text alongside its embedding."""
#     cleaned_text = clean_query(raw_query)
    
#     if not cleaned_text:
#         return "", []
    
#     embedding: np.ndarray = _model.encode(
#         cleaned_text, 
#         convert_to_numpy=True, 
#         normalize_embeddings=True
#     )
    
#     return cleaned_text, embedding.tolist()

import re
from typing import Tuple, List, Optional
from sentence_transformers import SentenceTransformer


def clean_query(query: str) -> str:
    """
    Light cleaning for a search query — NOT the same as clean_resume_text.
    Queries are short and typed by a human right now, so this only strips
    noise, it doesn't try to fix OCR artifacts or reflow paragraphs.
    """
    if not query:
        return ""

    cleaned = query.strip()

    # remove control/non-printable characters
    cleaned = re.sub(r"[^\x20-\x7E\u00A0-\uFFFF]", " ", cleaned)

    # collapse repeated whitespace
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


def process_query(
    query: str,
    encoder: Optional[SentenceTransformer] = None,
    embedding_model: str = "all-MiniLM-L6-v2",
) -> Tuple[str, List[float]]:
    """
    Clean a query and embed it.

    Args:
        query: raw user input.
        encoder: shared SentenceTransformer instance — pass the same one
                 used in embed_and_store.py / semantic_chunker.py. If None,
                 a new one is loaded (avoid this in production paths;
                 reuse the shared instance instead, see encoder_config.py).
        embedding_model: only used if encoder is None.

    Returns:
        (cleaned_query, embedding) — embedding is a plain list of floats,
        ready to pass straight into collection.query(query_embeddings=...).
    """
    cleaned_query = clean_query(query)

    if not cleaned_query:
        return "", []

    if encoder is None:
        encoder = SentenceTransformer(embedding_model)

    embedding = encoder.encode(cleaned_query, convert_to_numpy=True).tolist()

    return cleaned_query, embedding

