"""
LangGraph agent for cross-source (Postgres + uploaded documents) analysis.

Built with langchain.agents.create_agent() — the modern API per the
langchain-fundamentals skill. Under the hood this is LangGraph with a
ToolNode, MemorySaver checkpointer, and a recursion limit.
"""

import os
from typing import Any, Dict, List, Optional

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver

from components.agent.tools import make_search_documents_tool
from components.mcp.postgres_mcp_client import get_postgres_mcp_client


SYSTEM_PROMPT = """You are a contract compliance analyst.

You have access to these tools:
- Postgres tools: read-only SQL against tables `contracts`, `fee_schedules`, \
`transactions`. Key columns:
  • contracts(contract_id, participant, service_provider, contract_type, effective_date)
  • fee_schedules(contract_id, fee_category, fee_amount, fee_percentage, fee_unit)
  • transactions(contract_id, transaction_date, transaction_type, transaction_amount, fee_charged, merchant_name)
- search_documents: RAG search over uploaded contract PDFs for clauses, terms, obligations.

Rules:
- Be efficient — answer in the fewest tool calls possible (ideally 1–3).
- You already know the schema above; don't waste turns listing tables or columns \
unless the user explicitly asks to.
- Run ONE focused SQL query per DB question; don't explore iteratively.
- For contract-clause questions, call search_documents exactly once.
- After gathering evidence, write the final answer. Do not keep calling tools.
"""


class AnalysisAgent:
    """Cross-source agent combining Postgres MCP tools with the local RAG tool."""

    def __init__(self, rag_processor: Any, session_manager: Any):
        self.rag_processor = rag_processor
        self.session_manager = session_manager
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
        self._agent = None
        self._checkpointer = MemorySaver()
        self._mcp_client = None

    async def build(self) -> None:
        """Load MCP tools + RAG tool and compile the agent. Idempotent."""
        if self._agent is not None:
            return

        self._mcp_client = get_postgres_mcp_client()
        pg_tools = await self._mcp_client.get_tools()
        rag_tool = make_search_documents_tool(self.rag_processor)
        tools = [*pg_tools, rag_tool]

        api_key = os.getenv("GOOGLE_API_KEY_SOL_4")
        model = ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=0,
            google_api_key=api_key,
        )

        self._agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            checkpointer=self._checkpointer,
        )

    async def run(self, query: str, session_id: str) -> Dict[str, Any]:
        """Invoke the agent for a single user turn.

        Returns a dict with:
          - response: final assistant message text
          - tool_calls_log: list of (tool_name, args, result_summary) tuples
          - model: the model ID used
        """
        if self._agent is None:
            await self.build()

        config = {
            "configurable": {"thread_id": session_id or "default"},
            "recursion_limit": 25,
        }

        tool_calls_log: List[Dict[str, Any]] = []
        final_text = ""

        def _to_text(content: Any) -> str:
            """LangChain messages may carry content as str OR list of blocks.
            Flatten to a single string."""
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, str):
                        parts.append(block)
                    elif isinstance(block, dict):
                        parts.append(block.get("text") or block.get("content") or "")
                return "".join(parts)
            return str(content) if content is not None else ""

        async for chunk in self._agent.astream(
            {"messages": [HumanMessage(content=query)]},
            config=config,
            stream_mode="updates",
        ):
            for node_name, node_output in chunk.items():
                messages = node_output.get("messages", []) if isinstance(node_output, dict) else []
                for msg in messages:
                    tool_calls = getattr(msg, "tool_calls", None) or []
                    for tc in tool_calls:
                        tool_calls_log.append(
                            {
                                "tool": tc.get("name", "?"),
                                "args": tc.get("args", {}),
                            }
                        )
                    content = _to_text(getattr(msg, "content", ""))
                    if content and getattr(msg, "type", "") == "ai" and not tool_calls:
                        final_text = content

        if self.session_manager and session_id:
            try:
                self.session_manager.add_message(session_id, "user", query, {"query_mode": "analysis_agent"})
                self.session_manager.add_message(
                    session_id,
                    "assistant",
                    final_text,
                    {"query_mode": "analysis_agent", "tool_calls": len(tool_calls_log)},
                )
            except Exception:
                pass

        return {
            "response": final_text or "(no response generated)",
            "tool_calls_log": tool_calls_log,
            "model": self.model_name,
        }
