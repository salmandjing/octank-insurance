"""Knowledge base search tool — wraps the RAG retriever."""
from __future__ import annotations
from backend.rag.retriever import retriever


def search_knowledge_base(query: str) -> dict:
    """Search Prairie Shield's policy documents and knowledge base."""
    results = retriever.search(query)

    if not results:
        return {
            "results": [],
            "message": "No relevant documents found for this query.",
        }

    return {
        "results": results,
        "total_results": len(results),
    }
