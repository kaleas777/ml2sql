from __future__ import annotations

from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from .config import Settings, get_settings


class DatabaseError(RuntimeError):
    """Raised when a database operation cannot be completed."""


class Database:
    """Small database service with a production-ready engine boundary.

    SQLite is convenient for local development. Set DATABASE_URL to a
    PostgreSQL URL in staging/production; SQLAlchemy handles both.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        connect_args: dict[str, Any] = {}
        if self.settings.database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        self.engine: Engine = create_engine(
            self.settings.database_url,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args,
        )

    def get_schema(self) -> dict[str, list[dict[str, str]]]:
        inspector = inspect(self.engine)
        schema: dict[str, list[dict[str, str]]] = {}

        for table_name in inspector.get_table_names():
            columns: list[dict[str, str]] = []
            for column in inspector.get_columns(table_name):
                columns.append(
                    {
                        "name": str(column["name"]),
                        "type": str(column["type"]),
                        "nullable": str(bool(column.get("nullable", True))),
                    }
                )
            schema[table_name] = columns

        return schema

    def execute_readonly(self, query: str, max_rows: int) -> tuple[list[str], list[dict[str, Any]], bool]:
        """Execute a previously validated read-only query.

        The SQL guard is deliberately called before this method. In a real
        deployment, the database credentials must also be read-only.
        """

        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(query))
                columns = list(result.keys())
                raw_rows = result.fetchmany(max_rows + 1)
                truncated = len(raw_rows) > max_rows
                rows = [dict(row._mapping) for row in raw_rows[:max_rows]]
                return columns, rows, truncated
        except Exception as exc:  # noqa: BLE001 - converted at service boundary
            raise DatabaseError(str(exc)) from exc

    def health_check(self) -> None:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001 - converted at service boundary
            raise DatabaseError(str(exc)) from exc


@lru_cache
def get_database() -> Database:
    return Database(get_settings())

