"""
fbe_contracts_mcp — MCP server exposing the FBE contract-analysis capability.

Any MCP-compatible agent (Claude Code, Cursor, Claude Desktop, etc.) can
connect to this server to query the contracts Postgres DB, search contract
PDFs via RAG, and run compliance checks.
"""

__version__ = "0.1.0"
