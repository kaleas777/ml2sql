from __future__ import annotations

import logging
import secrets
import time
import uuid
from functools import lru_cache

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .agent import AgentError, QueryAgent
from .config import Settings, get_settings
from .db import Database, DatabaseError, get_database
from .llm import GeminiClient, LLMConfigurationError
from .models import HealthResponse, QueryRequest, QueryResponse, SchemaResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def require_api_key(
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Require an API key when one is configured.

    Leaving API_KEY empty is convenient for local development. Set it in every
    shared or production environment.
    """

    if settings.api_key and not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")
    if settings.api_key and not secrets.compare_digest(x_api_key or "", settings.api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@lru_cache
def get_agent() -> QueryAgent:
    settings = get_settings()
    return QueryAgent(get_database(), GeminiClient(settings), settings)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Secure natural-language-to-SQL service",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health/live", response_model=HealthResponse)
    def liveness() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/health/ready", response_model=HealthResponse)
    def readiness(database: Database = Depends(get_database)) -> HealthResponse:
        try:
            database.health_check()
        except DatabaseError as exc:
            raise HTTPException(status_code=503, detail="Database is not ready") from exc
        return HealthResponse(status="ok", database="ok")

    @app.get(
        "/api/v1/schema",
        response_model=SchemaResponse,
        dependencies=[Depends(require_api_key)],
    )
    def schema(database: Database = Depends(get_database)) -> SchemaResponse:
        return SchemaResponse(database_schema=database.get_schema())

    @app.post(
        "/api/v1/query",
        response_model=QueryResponse,
        dependencies=[Depends(require_api_key)],
    )
    def query(
        payload: QueryRequest,
        response: Response,
    ) -> QueryResponse:
        request_id = str(uuid.uuid4())
        response.headers["X-Request-ID"] = request_id
        started = time.perf_counter()

        try:
            agent = get_agent()
            result = agent.answer(payload.question)
        except LLMConfigurationError as exc:
            logger.exception("LLM is not configured; request_id=%s", request_id)
            raise HTTPException(status_code=503, detail="AI service is not configured") from exc
        except AgentError as exc:
            logger.warning("Agent request failed; request_id=%s error=%s", request_id, exc)
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "query_completed request_id=%s rows=%s truncated=%s latency_ms=%s",
            request_id,
            len(result.rows),
            result.truncated,
            latency_ms,
        )
        return QueryResponse(
            request_id=request_id,
            answer=result.answer,
            sql=result.sql if payload.include_sql else None,
            columns=result.columns,
            rows=result.rows,
            truncated=result.truncated,
            latency_ms=latency_ms,
        )

    return app


app = create_app()
