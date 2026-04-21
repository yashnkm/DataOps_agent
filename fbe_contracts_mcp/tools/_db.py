"""Shared Postgres connection helper for the MCP tools."""

import os

import psycopg2


ALLOWED_TABLES = {"contracts", "fee_schedules", "transactions"}


def connect():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "financial_services_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


def validate_select_only(sql: str) -> str | None:
    """Return an error string if the SQL isn't a safe read-only query, else None."""
    normalized = sql.strip().rstrip(";").lower()
    if not normalized.startswith(("select", "with")):
        return "Only SELECT / WITH queries are allowed."
    forbidden = [" insert ", " update ", " delete ", " drop ", " alter ",
                 " truncate ", " grant ", " revoke ", " create "]
    padded = f" {normalized} "
    for keyword in forbidden:
        if keyword in padded:
            return f"Query contains forbidden keyword: {keyword.strip()}"
    return None
