# Assessment checklist — VeyraQ

Maps AIVOA assignment requirements to the implemented system.  
Statuses reflect verification performed during Phase 10 hardening (local automated tests + code review). Live Groq/PostgreSQL rows are marked separately when blocked.

| Requirement | Implementation | Verification | Status |
| --- | --- | --- | --- |
| **Frontend: React** | `frontend/` Vite + React 19 + TypeScript | `npm run build`, Vitest UI/workspace tests | Verified |
| **Frontend: Redux** | Redux Toolkit slices: `complaint`, `assistant` | Patch/merge/commit/assistant Vitest suites | Verified |
| **Frontend: Inter** | Google Inter via `index.css` / font link | Visual + CSS token review | Verified |
| **Backend: Python** | Python 3.12 package `veyraq-backend` | Pytest suite | Verified |
| **Backend: FastAPI** | `app/main.py`, `/api/v1` routers | Health/assistant/complaint API tests | Verified |
| **AI: LangGraph** | `build_complaint_graph` StateGraph in `app/agents/graph.py` | Graph unit tests with fake AI service | Verified |
| **AI: Groq** | `GroqService` + env `GROQ_API_KEY` / `GROQ_MODEL` | Mocked boundary tests; **live smoke blocked without key** | Partial — live blocked |
| **Database: PostgreSQL** | SQLAlchemy model + Alembic; `DATABASE_URL` | SQLite test DB for CI; Alembic `--sql`; **live PG blocked** | Partial — live blocked |
| Text complaint intake | `POST /assistant/process` + Assistant composer | Vitest workflow + pytest graph/API | Verified (mocked AI) |
| Structured field population | `ComplaintPatch` → Redux `applyFieldPatch` | Patch isolation tests | Verified |
| Risk assessment | `assess_risk` / `merge_assessment` (`inferred`) | Graph + UI provenance tests | Verified |
| Conversational correction | Correction path + partial patch (`user`) | Graph + Vitest correction cases | Verified |
| PDF/email document intake | `document_service` + `POST /assistant/process-document` | Document pytest + Vitest | Verified |
| Human review | Dual-pane form + provenance + status | Workspace UI tests | Verified |
| Explicit commit | `POST /complaints/commit`; no auto-commit | Commit API + UI commit tests | Verified |
| Complaint Completeness Checker | Deterministic `check_completeness` → status | Graph/API tests | Verified |
| Root Cause / Hypotheses | Investigation Assistance RCA section | Investigation pytest + Vitest | Verified |
| Duplicate / Related detection | Deterministic `related_complaint_service` | Related service + graph tests | Verified |
| CAPA suggestions | Investigation Assistance CAPA section | Investigation tests | Verified |
| Complaint Summary | Investigation Assistance summary | Investigation tests | Verified |
| AI Risk Classification | Advisory severity/priority/risk narrative | Risk node tests | Verified |
| GitHub repository | Project monorepo layout | `git status` hygiene review | Verified (local) |
| Product demonstration video | Script in `docs/DEMO.md` Video 1 | Recording plan ready; video not produced by Phase 10 | Plan ready |
| Engineering walkthrough video | Script in `docs/DEMO.md` Video 2 | Recording plan ready; video not produced by Phase 10 | Plan ready |

## Source-of-truth contract (Phase 10 audit)

| Rule | Result |
| --- | --- |
| Source values require grounded evidence | Enforced in `grounding.py` / graph verify node |
| User corrections → `provenance=user` | Correction path + `setUserField` |
| AI risk/assessment → `inferred` | `merge_assessment` |
| Missing values remain `null` | Domain model + grounding drops |
| Dates remain source-precision strings | String columns + text inputs |
| Committed records immutable via API | No PUT/PATCH/DELETE; pytest asserts |

## Live integration notes

- **LIVE GROQ VERIFICATION BLOCKED** — `backend/.env` / `GROQ_API_KEY` not configured in this Phase 10 run.
- **LIVE POSTGRESQL VERIFICATION BLOCKED** — no reachable PostgreSQL / Docker daemon unavailable for a temporary instance.

Automated SQLite pytest coverage remains green and does **not** substitute for live PostgreSQL runtime proof.
