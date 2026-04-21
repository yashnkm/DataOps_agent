"""search_contract_documents — RAG over contract PDFs.

Wraps the existing POC RAGProcessor so there is one canonical
retrieval path shared between the Gradio app and the MCP server.
"""

from typing import Any

from ..server import mcp


# Lazy singletons — build on first call, reuse after.
_vector_store: Any = None
_rag_processor: Any = None


def _get_rag():
    global _vector_store, _rag_processor
    if _rag_processor is None:
        from components.vector_store.faiss_store import FAISSVectorStore
        from components.rag_engine.rag_processor import RAGProcessor

        _vector_store = FAISSVectorStore()
        _rag_processor = RAGProcessor(_vector_store)
    return _rag_processor


@mcp.tool()
def search_contract_documents(query: str, k: int = 8) -> dict:
    """Search the uploaded contract PDFs for clauses, terms, or obligations.

    Use this when the question is about contract text (fraud protection,
    termination conditions, SLAs, definitions) rather than structured
    fee/transaction data.

    Args:
        query: Natural-language question or keywords.
        k: Number of context chunks to retrieve (default 8, cap 20).

    Returns:
        dict with `response` (synthesized answer), `chunks_used`,
        and `sources` (list of source filenames cited).
    """
    if not query or not query.strip():
        return {"error": "Empty query."}

    k = min(max(int(k), 1), 20)

    try:
        rag = _get_rag()
        result = rag.process_query(query, use_reranking=False, final_results=k)
    except Exception as e:
        return {"error": f"RAG search failed: {e}"}

    return {
        "response": result.get("response", ""),
        "chunks_used": result.get("final_context_count", 0),
        "sources": result.get("sources", []),
    }
