from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .db import Database, DatabaseError
from .llm import GeminiClient, LLMResponseError
from .sql_guard import SQLGuardError, validate_read_only_sql


class AgentError(RuntimeError):
    """Raised when the text-to-SQL workflow cannot produce a safe result."""


@dataclass
class AgentResult:
    answer: str
    sql: str
    columns: list[str]
    rows: list[dict]
    truncated: bool


class QueryAgent:
    """Controlled orchestration loop for schema -> SQL -> validation -> execution."""

    def __init__(self, database: Database, llm: GeminiClient, settings: Settings) -> None:
        self.database = database
        self.llm = llm
        self.settings = settings

    def answer(self, question: str) -> AgentResult:
        try:
            schema = self.database.get_schema()
        except DatabaseError as exc:
            raise AgentError("The database schema could not be loaded") from exc
        if not schema:
            raise AgentError("The database has no visible tables")

        last_error: str | None = None
        allowed_tables = schema.keys()

        for _ in range(self.settings.max_agent_retries + 1):
            try:
                generated = self.llm.generate_query(question, schema, last_error)
                safe_sql = validate_read_only_sql(
                    generated.sql,
                    allowed_tables=allowed_tables,
                    max_length=self.settings.max_sql_length,
                )
                columns, rows, truncated = self.database.execute_readonly(
                    safe_sql,
                    max_rows=self.settings.max_result_rows,
                )
                answer = generated.answer or f"{len(rows)} row(s) returned."
                return AgentResult(answer, safe_sql, columns, rows, truncated)
            except (SQLGuardError, DatabaseError, LLMResponseError) as exc:
                last_error = str(exc)[:800]

        raise AgentError(f"Unable to produce a safe, executable query: {last_error}")
