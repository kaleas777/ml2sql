from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2_000)
    include_sql: bool = True


class GeneratedQuery(BaseModel):
    """Strict shape expected from the language model."""

    sql: str = Field(..., min_length=1, max_length=4_000)
    answer: str = Field(default="", max_length=2_000)


class QueryResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    request_id: str
    answer: str
    sql: str | None
    columns: list[str]
    rows: list[dict[str, Any]]
    truncated: bool
    latency_ms: float


class SchemaResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    database_schema: dict[str, list[dict[str, str]]] = Field(alias="schema")


class HealthResponse(BaseModel):
    status: str
    database: str | None = None
