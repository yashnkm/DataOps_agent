"""
LangChain tools used by the AnalysisAgent.

The agent also receives postgres tools from the MCP server — those are
returned by PostgresMCPClient.get_tools() and are not defined here.
"""

from typing import Any

from langchain_core.tools import BaseTool, tool


def make_search_documents_tool(rag_processor: Any) -> BaseTool:
    """Return a @tool that wraps RAGProcessor.process_query().

    The returned tool searches uploaded contract/document chunks using
    the existing hybrid FAISS + BM25 pipeline and returns a synthesized
    answer with source context.
    """

    @tool
    def search_documents(query: str) -> str:
        """Search uploaded contract and document PDFs for information.

        Use this tool when the user asks about contract terms, clauses,
        obligations, fee schedules, or anything that would be written in
        the uploaded documents rather than stored in the database.

        Args:
            query: Natural-language question or keywords to search for.
                   Example: "commission rate in the acme contract"
        """
        result = rag_processor.process_query(
            query, use_reranking=False, final_results=8
        )
        response = result.get("response", "")
        chunks_used = result.get("final_context_count", 0)
        if not response:
            return "No relevant content found in uploaded documents."
        return f"{response}\n\n(Sourced from {chunks_used} document chunks.)"

    return search_documents
