"""list_contracts — bootstrap helper returning one-liner info for every contract."""

from psycopg2.extras import RealDictCursor

from ..server import mcp
from ._db import connect


@mcp.tool()
def list_contracts() -> dict:
    """List every contract in the database with basic metadata.

    Returns:
        dict with `contracts` — list of {contract_id, participant,
        service_provider, effective_date, source_file}.
    """
    try:
        with connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT contract_id, participant, service_provider,
                              effective_date, source_file
                       FROM contracts
                       ORDER BY participant, service_provider"""
                )
                rows = cur.fetchall()
        return {"contracts": [dict(r) for r in rows], "count": len(rows)}
    except Exception as e:
        return {"error": f"Failed to list contracts: {e}"}
