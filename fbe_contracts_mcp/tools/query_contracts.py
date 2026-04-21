"""query_contracts — read-only SQL against the FBE schema."""

from psycopg2.extras import RealDictCursor

from ..server import mcp
from ._db import connect, validate_select_only


@mcp.tool()
def query_contracts(sql: str, limit: int = 100) -> dict:
    """Run a read-only SELECT against the FBE tables.

    Allowed tables: `contracts`, `fee_schedules`, `transactions`.
    Key columns:
      • contracts(contract_id, participant, service_provider, contract_type,
                  effective_date, term_months, source_file)
      • fee_schedules(contract_id, fee_category, fee_amount, fee_percentage,
                      fee_unit, notes)
      • transactions(contract_id, transaction_date, transaction_type,
                     transaction_amount, fee_charged, currency, merchant_name)

    Args:
        sql: A SELECT / WITH SQL statement. DML is rejected.
        limit: Max rows to return (hard cap 500).

    Returns:
        dict with `columns`, `rows` (list of dicts), `row_count`.
    """
    err = validate_select_only(sql)
    if err:
        return {"error": err}

    limit = min(max(int(limit), 1), 500)

    try:
        with connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchmany(limit)
                columns = [desc[0] for desc in cur.description] if cur.description else []
        return {
            "columns": columns,
            "rows": [dict(r) for r in rows],
            "row_count": len(rows),
        }
    except Exception as e:
        return {"error": f"SQL execution failed: {e}"}
