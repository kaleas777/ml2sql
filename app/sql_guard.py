from __future__ import annotations

from typing import Iterable

import sqlglot
from sqlglot import exp


class SQLGuardError(ValueError):
    """Raised when generated SQL is unsafe or outside the allowed scope."""


_FORBIDDEN_NODES = (
    "Insert",
    "Update",
    "Delete",
    "Create",
    "Drop",
    "Alter",
    "Merge",
    "TruncateTable",
    "Grant",
    "Revoke",
    "Command",
    "Pragma",
    "Attach",
    "Detach",
)


def validate_read_only_sql(
    query: str,
    allowed_tables: Iterable[str],
    max_length: int = 4_000,
) -> str:
    """Validate one read-only SQL statement and return a normalized query.

    This is a defense-in-depth layer. The production database must still use
    a database role that has SELECT permission only.
    """

    if not query or not query.strip():
        raise SQLGuardError("SQL query is empty")

    query = query.strip()
    if len(query) > max_length:
        raise SQLGuardError("SQL query is too long")
    if "\x00" in query:
        raise SQLGuardError("SQL query contains an invalid character")

    try:
        statements = sqlglot.parse(query)
    except Exception as exc:  # noqa: BLE001 - parser error is user-facing
        raise SQLGuardError(f"SQL could not be parsed: {exc}") from exc

    if len(statements) != 1:
        raise SQLGuardError("Only one SQL statement is allowed")

    statement = statements[0]

    for node_name in _FORBIDDEN_NODES:
        node_type = getattr(exp, node_name, None)
        if node_type is not None and statement.find(node_type):
            raise SQLGuardError(f"SQL operation is not allowed: {node_name}")

    # SELECT and WITH...SELECT queries contain a Select node. This rejects
    # commands such as SHOW, SET, VACUUM, and transaction statements.
    if statement.find(exp.Select) is None:
        raise SQLGuardError("Only read-only SELECT queries are allowed")

    allowed = {table.upper() for table in allowed_tables}
    cte_names = {
        cte.alias_or_name.upper()
        for cte in statement.find_all(exp.CTE)
        if cte.alias_or_name
    }

    for table in statement.find_all(exp.Table):
        table_name = table.name.upper()
        if allowed and table_name not in allowed and table_name not in cte_names:
            raise SQLGuardError(f"Table is not allowed: {table.name}")

    return statement.sql()

