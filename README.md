# VeyraQ

**AI-Assisted Pharmaceutical Complaint Intelligence**

VeyraQ is an AI-powered customer complaint intake module for pharmaceutical manufacturing (API and FDF). It helps QA personnel turn unstructured complaint text or documents into structured, reviewable complaint records—with human commit as the final control.

> Assessment project for the AI Product Engineer internship at AIVOA.

## Status

Document complaint intake is complete: PDF / TXT / EML extraction feeds the same LangGraph workflow as text intake (grounding, risk, completeness, patch merge). Scanned-image OCR is intentionally not included because the assessment does not require production-grade OCR.

## Stack

| Layer | Technologies |
| --- | --- |
| Frontend | React, TypeScript, Vite, Redux Toolkit, CSS Modules, Inter |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy 2.0, Alembic, PyMuPDF |
| Database | PostgreSQL |
| AI | LangGraph StateGraph, Groq (official Python SDK) |

The original assessment references Groq model IDs that are no longer generally available on the current developer tier. VeyraQ preserves Groq as the required provider while keeping the model configurable. The default model is a currently supported Groq model with strict structured-output support.

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

Set `GROQ_API_KEY` in `backend/.env`. Leave it empty to boot the API and health checks; Assistant processing then returns 503 without changing the draft.

Optional:

```text
GROQ_MODEL=openai/gpt-oss-20b
```

Limits:

- Assistant text messages: 12,000 characters
- Document uploads: PDF, TXT, or EML · up to 8 MB · up to 20 PDF pages · up to 20,000 extracted characters (rejected if over limit — never silently truncated)

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

- Liveness: `GET http://localhost:8000/api/v1/health`
- Readiness: `GET http://localhost:8000/api/v1/readiness` (requires PostgreSQL)
- OpenAPI docs: http://localhost:8000/docs

### Database

Ensure PostgreSQL is running and create a database matching `DATABASE_URL` in `.env` (default database name: `veyraq`).

PostgreSQL is required for **live** readiness checks and real commit persistence. Automated backend tests use an isolated in-memory SQLite database and do not need PostgreSQL.

Apply migrations:

```bash
cd backend
alembic upgrade head
```

Optional fictional history seed (idempotent; for later duplicate demos):

```bash
python -m app.scripts.seed_demo_complaints
```

Complaint API (after migrations):

- `POST /api/v1/complaints/commit`
- `GET /api/v1/complaints`
- `GET /api/v1/complaints/{id}`
- `POST /api/v1/assistant/process`
- `POST /api/v1/assistant/process-document`

Committed records are not updated or deleted through this assessment API. Uploaded documents are processed in memory only and are not stored.

### Text complaint demo

Paste into VeyraQ Assistant:

```text
NovaCare Pharmacy reported brown discoloration on Cefixime
Capsules 200 mg from batch CFX260481. Manufacturing date April
2026 and expiry March 2028. 24 capsules were affected.
```

Then correct:

```text
Correction: the batch is CFX260418 and 30 capsules were affected.
```

Only explicitly corrected fields should change (plus a refreshed advisory risk assessment when the change is risk-relevant). Commit remains a separate human action.

### Document complaint demo

In the Assistant panel, choose a text-based PDF, TXT, or EML pharmaceutical complaint, then click **Analyze Document**. The draft must be empty (use New Complaint first if needed). Scanned image-only PDFs are rejected clearly; OCR is not available in this build.

### Backend tests

```bash
cd backend
pytest
```

Readiness and complaint API tests do not require a live PostgreSQL instance.

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
