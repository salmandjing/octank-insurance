"""Knowledge base search tool — wraps the RAG retriever."""
from __future__ import annotations
from backend.rag.retriever import retriever


def search_knowledge_base(query: str) -> dict:
    """Search the policy knowledge base for relevant information."""
    results = retriever.search(query)

    if not results:
        return {
            "results": [],
            "message": "No relevant policy documents found for this query.",
        }

    return {
        "results": results,
        "total_results": len(results),
    }
