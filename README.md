# Production-style Natural Language to SQL

This repository is a hardened starter version of the original text-to-SQL POC.
It keeps the same idea—English question to SQL result—but adds the boundaries
needed for a real service:

- FastAPI backend separated from the Streamlit UI
- PostgreSQL-ready SQLAlchemy database layer
- Read-only SQL validation with `sqlglot`
- Result row and query-length limits
- API-key protection for application endpoints
- Strict Pydantic request and response models
- Health and readiness endpoints
- Retry handling for model and SQL errors
- Docker Compose with PostgreSQL
- Unit tests for SQL safety

## Architecture

```text
Streamlit UI
    -> POST /api/v1/query
FastAPI API
    -> QueryAgent
       -> Gemini generates a candidate SELECT query
       -> SQL guard validates it
       -> SQLAlchemy executes it using a read-only policy
    -> JSON result
```

## Local setup with SQLite

Use Python 3.11 or newer:

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Set `GOOGLE_API_KEY` in `.env`. For local development, leaving `API_KEY` empty
is allowed; use an API key in every shared environment.

Create the sample database:

```bash
python -m scripts.seed_db
```

Start the backend in one terminal:

```bash
uvicorn app.main:app --reload
```

Start the UI in another terminal:

```bash
streamlit run ui/streamlit_app.py
```

Open `http://localhost:8501`.

## Docker Compose with PostgreSQL

Copy `.env.example` to `.env`, set `GOOGLE_API_KEY` and a strong `API_KEY`, then
run:

```bash
docker compose up --build
```

The UI is available at `http://localhost:8501` and the API at
`http://localhost:8000`.

## API examples

Health check:

```bash
curl http://localhost:8000/health/live
```

Query endpoint when `API_KEY` is configured:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: replace_with_a_long_random_value" \
  -d '{"question":"Show students who scored more than 90"}'
```

## Important production controls

The database credentials used by the API must have read-only permissions. The
application-side SQL guard is defense in depth, not a replacement for database
permissions. In a real deployment, add SSO/OIDC authentication, row-level
authorization, a secret manager, HTTPS, rate limiting, structured logs,
metrics, tracing, backups, migrations, and an evaluation set for NL-to-SQL
accuracy.

## Testing

```bash
pytest -q
ruff check .
```

