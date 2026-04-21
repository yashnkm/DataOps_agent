"""check_fee_compliance — opinionated tool comparing transaction fees
to the contract's fee schedule and flagging overcharges.

Reuses the same SQL logic as the Gradio Dashboard's
`compute_discrepancy_analysis` but returned as structured data.
"""

from typing import Optional

from psycopg2.extras import RealDictCursor

from ..server import mcp
from ._db import connect


OVERCHARGE_SQL = """
WITH joined AS (
    SELECT t.transaction_id, t.contract_id, t.transaction_date,
           t.transaction_type, t.transaction_amount, t.fee_charged,
           t.merchant_name,
           (COALESCE(f.fee_amount, 0) + COALESCE(f.fee_percentage, 0) * t.transaction_amount)
               AS expected_fee
    FROM transactions t
    LEFT JOIN fee_schedules f
        ON f.contract_id = t.contract_id
        AND f.fee_category = t.transaction_type
    WHERE t.contract_id = %(contract_id)s
      AND (%(date_from)s::timestamp IS NULL OR t.transaction_date >= %(date_from)s::timestamp)
      AND (%(date_to)s::timestamp IS NULL OR t.transaction_date <= %(date_to)s::timestamp)
)
SELECT * FROM joined
WHERE fee_charged > expected_fee + %(threshold)s
ORDER BY (fee_charged - expected_fee) DESC
"""

SUMMARY_SQL = """
WITH joined AS (
    SELECT t.fee_charged,
           (COALESCE(f.fee_amount, 0) + COALESCE(f.fee_percentage, 0) * t.transaction_amount)
               AS expected_fee
    FROM transactions t
    LEFT JOIN fee_schedules f
        ON f.contract_id = t.contract_id
        AND f.fee_category = t.transaction_type
    WHERE t.contract_id = %(contract_id)s
      AND (%(date_from)s::timestamp IS NULL OR t.transaction_date >= %(date_from)s::timestamp)
      AND (%(date_to)s::timestamp IS NULL OR t.transaction_date <= %(date_to)s::timestamp)
)
SELECT
    COUNT(*) AS total_transactions,
    COUNT(*) FILTER (WHERE fee_charged > expected_fee + %(threshold)s) AS overcharged,
    COALESCE(SUM(fee_charged - expected_fee)
             FILTER (WHERE fee_charged > expected_fee + %(threshold)s), 0)
        AS total_overcharge_usd
FROM joined
"""


@mcp.tool()
def check_fee_compliance(
    contract_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    threshold: float = 0.0001,
    limit: int = 50,
) -> dict:
    """Flag transactions whose fee_charged exceeds the contract's fee schedule.

    Args:
        contract_id: The contract to audit (e.g. 'DBS-MC-2021-001').
        date_from: Optional ISO date/datetime lower bound.
        date_to:   Optional ISO date/datetime upper bound.
        threshold: Minimum USD overcharge to flag (default $0.0001).
        limit:     Max flagged transactions to return (default 50, cap 200).

    Returns:
        dict with `summary` (counts + total overcharge $) and `flagged`
        (list of offending transactions, sorted by variance DESC).
    """
    params = {
        "contract_id": contract_id,
        "date_from": date_from,
        "date_to": date_to,
        "threshold": float(threshold),
    }
    limit = min(max(int(limit), 1), 200)

    try:
        with connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SUMMARY_SQL, params)
                summary = dict(cur.fetchone() or {})
                cur.execute(OVERCHARGE_SQL, params)
                flagged = [dict(r) for r in cur.fetchmany(limit)]
    except Exception as e:
        return {"error": f"Compliance check failed: {e}"}

    if not summary.get("total_transactions"):
        return {
            "summary": {"total_transactions": 0, "overcharged": 0, "total_overcharge_usd": 0},
            "flagged": [],
            "note": f"No transactions found for contract {contract_id}.",
        }

    return {
        "summary": {
            "contract_id": contract_id,
            "total_transactions": int(summary["total_transactions"]),
            "overcharged": int(summary["overcharged"]),
            "total_overcharge_usd": float(summary["total_overcharge_usd"]),
        },
        "flagged": flagged,
    }
