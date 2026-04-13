"""
Postgres MCP client.

Spawns the official @modelcontextprotocol/server-postgres as a subprocess
over stdio and exposes its tools as LangChain-compatible tools via
langchain-mcp-adapters.
"""

import os
from typing import List, Optional

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient


class PostgresMCPClient:
    """Lazy, reusable wrapper around MultiServerMCPClient for the postgres MCP server."""

    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.getenv("POSTGRES_CONNECTION_STRING")
        if not self.connection_string:
            raise ValueError(
                "POSTGRES_CONNECTION_STRING env var must be set "
                "(e.g. postgresql://user:pass@host:5432/dbname)"
            )
        self._client: Optional[MultiServerMCPClient] = None
        self._tools: Optional[List[BaseTool]] = None

    def _build_client(self) -> MultiServerMCPClient:
        return MultiServerMCPClient(
            {
                "postgres": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-postgres",
                        self.connection_string,
                    ],
                    "transport": "stdio",
                }
            }
        )

    async def get_tools(self) -> List[BaseTool]:
        """Return LangChain tools exposed by the postgres MCP server.

        Cached after first call. The underlying MCP client keeps the
        subprocess alive for the lifetime of this PostgresMCPClient.
        """
        if self._tools is None:
            self._client = self._build_client()
            self._tools = await self._client.get_tools()
        return self._tools

    async def aclose(self) -> None:
        """Best-effort shutdown of the MCP subprocess."""
        if self._client is not None:
            close = getattr(self._client, "aclose", None) or getattr(self._client, "close", None)
            if close is not None:
                result = close()
                if hasattr(result, "__await__"):
                    await result
            self._client = None
            self._tools = None


_singleton: Optional[PostgresMCPClient] = None


def get_postgres_mcp_client() -> PostgresMCPClient:
    """Process-wide singleton — one MCP subprocess per Gradio app."""
    global _singleton
    if _singleton is None:
        _singleton = PostgresMCPClient()
    return _singleton
