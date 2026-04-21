"""contract://{contract_id} resource — returns full PDF text + metadata."""

import os
from pathlib import Path

from psycopg2.extras import RealDictCursor

from ..server import mcp
from ..tools._db import connect


def _docs_dir() -> Path:
    default = Path(__file__).resolve().parent.parent.parent / "data" / "contracts"
    return Path(os.getenv("DOCS_DIR", str(default)))


@mcp.resource("contract://{contract_id}")
def contract(contract_id: str) -> str:
    """Full text of a contract plus header metadata from the database."""
    try:
        with connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT contract_id, participant, service_provider,
                              contract_type, effective_date, term_months,
                              source_file
                       FROM contracts WHERE contract_id = %s""",
                    (contract_id,),
                )
                row = cur.fetchone()
    except Exception as e:
        return f"# Error reading contract {contract_id}\n\n{e}"

    if not row:
        return f"# Contract {contract_id} not found"

    header = (
        f"# {row['participant']} — {row['service_provider']}\n\n"
        f"**Contract ID:** `{row['contract_id']}`\n"
        f"**Type:** {row['contract_type']}\n"
        f"**Effective:** {row['effective_date']}\n"
        f"**Term:** {row['term_months']} months\n\n"
        f"---\n\n"
    )

    source = row.get("source_file")
    if not source:
        return header + "_(no source PDF associated)_"

    path = _docs_dir() / source
    if not path.exists():
        return header + f"_(source file not found at {path})_"

    try:
        return header + path.read_text(encoding="utf-8")
    except Exception as e:
        return header + f"_(failed to read {path}: {e})_"
