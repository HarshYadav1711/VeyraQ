# VeyraQ

**AI-Assisted Pharmaceutical Complaint Intelligence**

VeyraQ is an AI-powered customer complaint intake module for pharmaceutical manufacturing (API and FDF). It helps QA personnel turn unstructured complaint text or documents into structured, reviewable complaint records—with human commit as the final control.

> Assessment project for the AI Product Engineer internship at AIVOA.

## Status

Phase 2 complete: canonical complaint domain contracts + Redux complaint draft slice (no complaint UI/API/AI yet).

## Stack

| Layer | Technologies |
| --- | --- |
| Frontend | React, TypeScript, Vite, Redux Toolkit, CSS Modules, Inter |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy 2.0, Alembic |
| Database | PostgreSQL |
| AI (later) | LangGraph StateGraph, Groq |

## Prerequisites

- Node.js 22 LTS (or compatible with current Vite)
- Python 3.12
- PostgreSQL (required for live readiness checks)

## Repository layout

```text
frontend/   React + Vite application
backend/    FastAPI application
docs/       Authoritative project documentation
```

## Frontend setup

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

App: http://localhost:5173

```bash
npm run build
npm test -- --run
```

`VITE_API_BASE_URL` defaults to `http://localhost:8000/api/v1`.

## Backend setup

```bash
cd backend
py -3.12 -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
```

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

- Liveness: `GET http://localhost:8000/api/v1/health`
- Readiness: `GET http://localhost:8000/api/v1/readiness` (requires PostgreSQL)
- OpenAPI docs: http://localhost:8000/docs

### Database

Ensure PostgreSQL is running and create a database matching `DATABASE_URL` in `.env` (default database name: `veyraq`).

Alembic is initialized and reads `DATABASE_URL` from application settings. There are no domain migrations in Phase 1.

```bash
alembic current
```

### Backend tests

```bash
cd backend
pytest
```

Readiness tests mock the database probe and do not require a live PostgreSQL instance.

## Documentation

| Document | Purpose |
| --- | --- |
| [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) | Authoritative non-negotiable project context |
| [docs/PRD.md](docs/PRD.md) | Product requirements and acceptance criteria |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System boundaries and data flow |
| [docs/DOMAIN.md](docs/DOMAIN.md) | Domain terminology and assumptions |
| [docs/DESIGN.md](docs/DESIGN.md) | UI/UX direction and design tokens |
| [docs/RULES.md](docs/RULES.md) | Strict rules for future coding assistants |
| [docs/PHASES.md](docs/PHASES.md) | Incremental implementation plan |
| [docs/AI_WORKFLOW.md](docs/AI_WORKFLOW.md) | LangGraph workflow, provenance, reliability |
| [docs/DEMO.md](docs/DEMO.md) | Product and code walkthrough demo plan |

## Core principle

AI assists QA. AI must never silently invent complaint facts. Source, user, inferred, and missing values remain distinguishable. Final commit authority stays with the human.
