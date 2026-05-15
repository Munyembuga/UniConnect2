# UniConnect Backend - Phase 1

Phase 1 establishes the production-style base for the backend:

- FastAPI application bootstrap
- Async PostgreSQL configuration with SQLAlchemy
- Environment-driven configuration
- Structured logging
- A health endpoint for connectivity checks
- A clean folder structure ready for auth, models, Alembic, uploads, and RAG work

## Folder Structure

```text
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   ├── core/
│   ├── db/
│   ├── middleware/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── utils/
│   └── main.py
├── chroma_db/
├── uploads/
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Installation

Use Python 3.13 for the backend environment.

```powershell
cd "d:\Final Project\UniConnect\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Start PostgreSQL

```powershell
docker compose up -d postgres
```

## Configure Environment

Copy `.env.example` to `.env` and update the values for your machine.

## Run the API

```powershell
uvicorn app.main:app --reload
```

## Required Packages

- fastapi
- uvicorn
- SQLAlchemy
- asyncpg
- alembic
- pydantic
- pydantic-settings
- python-dotenv
- python-multipart
- httpx
- pytest

## Phase 1 Files

- [app/main.py](app/main.py)
- [app/core/config.py](app/core/config.py)
- [app/core/logging.py](app/core/logging.py)
- [app/db/session.py](app/db/session.py)
- [app/db/base.py](app/db/base.py)
- [app/api/router.py](app/api/router.py)
- [app/api/v1/health.py](app/api/v1/health.py)

## API Endpoints

- `GET /` - service welcome message
- `GET /api/v1/health` - API and database health check

## Testing Instructions

1. Start PostgreSQL with Docker.
2. Run the FastAPI server.
3. Open `http://127.0.0.1:8000/docs`.
4. Call `GET /api/v1/health`.

Example:

```powershell
curl http://127.0.0.1:8000/api/v1/health
```

## Expected Output

```json
{
  "status": "ok",
  "database": "ok"
}
```

## Best Practices Applied

- Async request handling from the start
- Environment-based configuration
- PostgreSQL via `asyncpg`
- Clear separation between API, core, and DB layers
- Ready for future auth, migrations, and RAG services

## Next Phases

Phase 2 will add JWT authentication and role management.

Phase 3 will add SQLAlchemy models and Alembic migrations.
