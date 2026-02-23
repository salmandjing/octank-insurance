"""Vector retriever using TF-IDF + cosine similarity.

Lightweight RAG — no model downloads, no GPU, fast startup.
"""
from __future__ import annotations
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from backend.config import RAG_TOP_K
from backend.rag.indexer import Chunk, load_and_chunk_documents

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(self):
        self._chunks: list[Chunk] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._tfidf_matrix = None
        self._ready = False

    def initialize(self) -> None:
        """Load docs, chunk, and build TF-IDF index."""
        logger.info("Indexing policy documents for RAG...")
        self._chunks = load_and_chunk_documents()

        if not self._chunks:
            logger.warning("No document chunks found!")
            return

        self._vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=5000,
        )
        texts = [c.text for c in self._chunks]
        self._tfidf_matrix = self._vectorizer.fit_transform(texts)
        self._ready = True
        logger.info(f"Indexed {len(self._chunks)} chunks from {len(set(c.source_doc for c in self._chunks))} documents")

    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        """Search for relevant chunks given a query."""
        if not self._ready or self._vectorizer is None:
            return []

        k = top_k or RAG_TOP_K
        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < 0.05:  # Skip very low relevance
                continue
            chunk = self._chunks[idx]
            results.append({
                "chunk_text": chunk.text,
                "source_doc": chunk.source_doc,
                "heading": chunk.heading,
                "chunk_index": chunk.chunk_index,
                "relevance_score": round(score, 3),
            })

        return results


# Singleton
retriever = Retriever()
