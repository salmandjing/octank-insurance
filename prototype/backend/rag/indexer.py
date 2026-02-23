"""Document chunker and indexer for RAG pipeline.

Uses TF-IDF vectorization (scikit-learn) — lightweight, no model downloads.
"""
from __future__ import annotations
import re
from pathlib import Path
from dataclasses import dataclass

from backend.config import DOCS_DIR, RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP


@dataclass
class Chunk:
    text: str
    source_doc: str
    chunk_index: int
    heading: str = ""


def _split_into_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into word-based chunks with overlap."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def _extract_heading(text: str) -> str:
    """Extract the nearest heading from the chunk text."""
    lines = text.strip().split("\n")
    for line in lines:
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return ""


def load_and_chunk_documents() -> list[Chunk]:
    """Load all markdown docs from DOCS_DIR and chunk them."""
    chunks: list[Chunk] = []

    for doc_path in sorted(DOCS_DIR.glob("*.md")):
        text = doc_path.read_text(encoding="utf-8")
        doc_name = doc_path.name

        # Split by sections first for better context
        sections = re.split(r'\n(?=##\s)', text)

        chunk_index = 0
        for section in sections:
            section = section.strip()
            if not section:
                continue

            heading = _extract_heading(section)
            section_chunks = _split_into_chunks(section, RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP)

            for chunk_text in section_chunks:
                if len(chunk_text.split()) < 10:
                    continue  # Skip tiny chunks
                chunks.append(Chunk(
                    text=chunk_text,
                    source_doc=doc_name,
                    chunk_index=chunk_index,
                    heading=heading,
                ))
                chunk_index += 1

    return chunks
