from __future__ import annotations

import json
from typing import Any

from .config import Settings
from .models import GeneratedQuery


class LLMConfigurationError(RuntimeError):
    """Raised when the language model cannot be configured."""


class LLMResponseError(RuntimeError):
    """Raised when the model returns an invalid response."""


def _extract_json(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise LLMResponseError("The model did not return a JSON object")

    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMResponseError("The model returned malformed JSON") from exc

    if not isinstance(parsed, dict):
        raise LLMResponseError("The model response must be a JSON object")
    return parsed


class GeminiClient:
    """Small adapter around Gemini so the agent can be tested with a fake LLM."""

    def __init__(self, settings: Settings) -> None:
        if not settings.google_api_key:
            raise LLMConfigurationError("GOOGLE_API_KEY is not configured")

        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise LLMConfigurationError(
                "google-generativeai is not installed"
            ) from exc

        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    def generate_query(
        self,
        question: str,
        schema: dict[str, list[dict[str, str]]],
        previous_error: str | None = None,
    ) -> GeneratedQuery:
        error_context = previous_error or "None"
        prompt = f"""
You are a reliable text-to-SQL service.

Database schema:
{json.dumps(schema, indent=2)}

User question:
{question}

Previous execution error, if any:
{error_context}

Rules:
1. Return ONLY valid JSON.
2. The JSON must contain exactly these useful fields: sql and answer.
3. Generate only one read-only SELECT query.
4. Use only tables and columns present in the schema.
5. Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, PRAGMA, or multiple statements.
6. Limit the query to a reasonable result size when returning rows.

Required format:
{{"sql": "SELECT ...", "answer": "Short answer based on the query result"}}
"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"temperature": 0},
            )
            raw_text = (response.text or "").strip()
            return GeneratedQuery.model_validate(_extract_json(raw_text))
        except LLMResponseError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalized at service boundary
            raise LLMResponseError(f"Gemini request failed: {exc}") from exc

