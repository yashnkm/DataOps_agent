"""
MCP server bootstrap using the FastMCP high-level API.

Registers 4 tools and 1 resource. The tools reuse existing POC code
via relative imports into src/components/ — so there's one source of
truth for compliance logic and RAG.
"""

import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Make the existing POC components importable when this package is run
# from the project root or installed in editable mode.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


mcp = FastMCP(
    name="fbe-contracts",
    instructions=(
        "MCP server for Fee Billing Excellence. Exposes tools to query the "
        "contracts/fee_schedules/transactions Postgres tables, search contract "
        "PDFs via RAG, and run opinionated fee-compliance checks. Full contract "
        "text is also available as a resource at contract://{contract_id}."
    ),
)


# Register tools + resources. Importing the modules triggers @mcp.tool /
# @mcp.resource decorators.
from .tools import query_contracts  # noqa: E402,F401
from .tools import search_documents  # noqa: E402,F401
from .tools import check_compliance  # noqa: E402,F401
from .tools import list_contracts  # noqa: E402,F401
from .resources import contract  # noqa: E402,F401


if __name__ == "__main__":
    mcp.run()
