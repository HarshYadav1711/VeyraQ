# ARCHITECTURE — System Design

## 1. Architectural intent

VeyraQ uses a **simple, interview-explainable** layered architecture:

```
React (Vite + TS) + Redux Toolkit
        │  HTTP/JSON
        ▼
FastAPI + Pydantic
        │
        ├── LangGraph StateGraph ──► Groq (LLM)
        │
        └── SQLAlchemy 2.x / Alembic ──► PostgreSQL
```

Principles:
- Prefer boring, understandable engineering.
- No microservices, queues, or clever abstractions before necessity.
- AI assists humans; persistence of committed records is an explicit user action.
- Boundaries stay clear so the code walkthrough can follow one linear path.

---

## 2. System boundaries

### 2.1 Frontend
**Owns:** UI, local interaction state, Redux complaint draft state, Copilot UX, provenance presentation, commit confirmation UX.

**Does not own:** Prompt text as source of truth, LLM calls, database writes, document binary parsing beyond upload.

**Stack:** React, TypeScript, Vite, Redux Toolkit, CSS Modules, Inter, semantic/accessible components.

### 2.2 Backend (API)
**Owns:** HTTP API, request validation (Pydantic), orchestration of AI workflow, document text extraction, completeness/readiness evaluation endpoints (or workflow-embedded), persistence of drafts/commits.

**Does not own:** Frontend styling, Redux store shape as UI concern (API contracts are shared via schemas).

**Stack:** Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic.

### 2.3 AI workflow
**Owns:** Intent detection, extraction, normalization, validation, completeness check, risk assessment, patch extraction/application logic, optional later duplicate/root-cause/CAPA suggestion nodes.

**Does not own:** Silent mutation of stored committed records; inventing missing facts; autonomous multi-agent systems.

**Stack:** LangGraph StateGraph, Groq SDK/API, centrally stored prompts, schema-validated structured outputs.

### 2.4 Database
**Owns:** Persistent storage for complaint records (and supporting entities as needed for drafts/commits/duplicates if implemented).

**Stack:** PostgreSQL.

### 2.5 Document processing
**Owns:** Extracting plain text from uploaded files when practical.

**Rules:** PyMuPDF for normal PDF text; simple TXT/EML if practical; **no** production OCR.

---

## 3. High-level components

| Component | Responsibility |
| --- | --- |
| Complaint Form (left pane) | Displays structured fields, provenance, status, highlights |
| VeyraQ Copilot (right pane) | Text input, corrections, uploads, follow-ups |
| Redux store | Authoritative client-side complaint draft + UI status |
| FastAPI routers | Intake, correct, upload, commit, health |
| LangGraph workflow | Stateful complaint processing graph |
| Prompt registry | Central prompt storage |
| Groq client | Model calls via env-configured model IDs |
| Persistence layer | SQLAlchemy models + Alembic migrations |
| Completeness / risk modules | Workflow nodes producing advisory + readiness signals |

---

## 4. Primary data flows

### 4.1 Text intake

1. User submits complaint text in Copilot.
2. Frontend dispatches Redux action (e.g., processing started) and calls FastAPI.
3. FastAPI validates request and invokes LangGraph with intent = new complaint.
4. Graph: `detect_intent` → `extract_complaint` → `normalize_fields` → `validate_fields` → `check_completeness` → `assess_risk` → `summarize`.
5. Nodes calling Groq return schema-validated structured data.
6. API returns structured complaint + provenance + advisory risk + status signals.
7. Redux updates complaint state; form populates.
8. User reviews; may correct or commit later.

### 4.2 Document intake

1. User uploads document via Copilot.
2. Frontend sends file to FastAPI upload endpoint.
3. Backend runs `extract_document_text` (PyMuPDF / TXT / EML).
4. Extracted text enters the standard complaint workflow (same as §4.1 from intent/extraction onward).
5. Response populates Redux/form.

### 4.3 Correction (patch)

1. User sends correction text referencing the current draft.
2. Frontend sends correction + current field snapshot (or server-side draft id if persisted) to API.
3. Graph: `detect_intent` → `extract_patch` → `validate_patch` → `apply_patch` → `reassess_affected_outputs_if_required`.
4. Response contains **only** patched field updates (plus any required reassessment outputs).
5. Redux merges patch; unrelated fields remain untouched; UI highlights changed fields.

### 4.4 Commit

1. Frontend enables commit only when status is Ready to Commit (per server/client rules aligned with completeness).
2. User explicitly confirms commit.
3. FastAPI persists Committed record in PostgreSQL.
4. Redux reflects Committed status.

### 4.5 Failure isolation

If Groq/LangGraph fails or returns invalid schema:
- API returns a clear error.
- Existing Redux complaint draft is **not** overwritten with partial garbage.
- Status may reflect failure for the processing attempt without destroying prior good state.

---

## 5. API surface (conceptual)

Exact routes will be defined during implementation; conceptual groups:

| Group | Purpose |
| --- | --- |
| `POST /complaints/intake` | Text complaint processing |
| `POST /complaints/upload` | Document upload + processing |
| `POST /complaints/correct` | Conversational patch |
| `POST /complaints/{id}/commit` | Explicit human commit |
| `GET /complaints/{id}` | Retrieve persisted complaint (as needed) |
| `GET /health` | Liveness (`GET /api/v1/health`) |
| `GET /readiness` | Readiness including DB (`GET /api/v1/readiness`) |

All versioned routes mount under the single prefix **`/api/v1`**.

Request/response contracts use Pydantic models shared conceptually with frontend types.

---

## 6. State ownership

| State | Owner |
| --- | --- |
| Active draft being edited in UI | Redux (client) until explicit commit |
| Processing / highlight / Copilot chat UX | Redux or local UI state |
| AI workflow ephemeral state | LangGraph state object (server, per request) |
| **Committed** complaint records | PostgreSQL only |

**Locked:** Complaint drafts remain client-side in Redux until the user explicitly commits. PostgreSQL stores committed complaints. Do not auto-persist drafts.

### Draft field contract (locked)

- Frontend and backend share one conceptual complaint contract (mirrored TypeScript + Pydantic).
- Each canonical field is a `ComplaintFieldValue`: `{ value, provenance, confidence, evidence }` co-located—not a separate provenance map.
- Uncommitted draft lives in Redux under the `complaint` slice (`fields`, `status`, `recentlyUpdatedFields`, plus commit metadata).
- Updates that change only some fields use an explicit **`ComplaintPatch`** (`changes` map). Never “replace the whole regenerated complaint” as the correction contract.

### Persistence boundary (Phase 4)

```text
Redux draft → POST /api/v1/complaints/commit → service validation
  → repository → SQLAlchemy Complaint → PostgreSQL
  → CommittedComplaintResponse → Redux status=committed
```

- **SQL columns** store authoritative field values (dates remain strings).
- **`field_metadata` JSON** stores only `{ provenance, confidence, evidence }` per field — not duplicate values.
- Server generates `id` (UUID) and `complaint_number` (`CMP-{year}-{suffix}`); clients cannot supply them on commit.
- Commit validation is **server-enforced** (required fields); frontend `ready_to_commit` is not trusted.
- No `PUT` / `PATCH` / `DELETE` for committed records in this assessment API.
- Read-only: `GET /api/v1/complaints`, `GET /api/v1/complaints/{id}`.
- Layers: routes → `ComplaintService` → `ComplaintRepository` → model.

---

## 7. AI integration boundary

```
FastAPI handler
  → build initial LangGraph state
  → invoke StateGraph
  → nodes may call Groq with central prompts
  → validate structured outputs with Pydantic schemas
  → return DTO to client
```

Rules:
- One understandable stateful workflow (not a swarm of agents).
- Model name/ID from environment variables.
- Secrets from environment only.
- Prompts centralized.

Details: `AI_WORKFLOW.md`.

---

## 8. Database boundary

PostgreSQL stores QMS-style complaint records suitable for the assessment demo.

Minimum conceptual entities (names may vary in implementation):
- Complaint record (core fields, status, timestamps)
- Field provenance metadata (per-field or structured JSON with clear schema)
- Advisory assessment snapshot (severity, next action, risk text)
- Optional: document reference metadata; duplicate-check support fields

Alembic manages migrations. SQLAlchemy 2.x is the ORM.

---

## 9. Testing architecture

| Layer | Tool | Focus |
| --- | --- | --- |
| Backend | Pytest | API contracts, patch merge semantics, schema validation, workflow unit tests with mocked Groq where appropriate |
| Frontend | Vitest | Redux reducers/selectors, provenance display helpers |
| E2E | Playwright | **One** critical path: intake → form populate → correct patch → ready/commit (as feasible with test doubles or staged env) |

---

## 10. Architectural rationale

| Decision | Why |
| --- | --- |
| Monolith FastAPI + SPA | Assessment clarity; easy walkthrough |
| Redux Toolkit | Mandatory Redux; RTK is current, boring, teachable |
| LangGraph StateGraph | Mandatory; clear nodes for demo |
| Groq | Mandatory LLM provider |
| PostgreSQL | Mandatory durable store for commit |
| CSS Modules | Scoped styling without heavy UI framework lock-in |
| No Redis/Kafka/Celery | Out of scope; unnecessary for intake module |
| No RAG/vector DB | Out of scope; hallucinations controlled by provenance + schema, not retrieval stack |

---

## 11. Locked implementation decisions

| Decision | Choice |
| --- | --- |
| Monorepo folders | `frontend/`, `backend/` |
| API prefix | `/api/v1` |
| Draft persistence | Client-side Redux only until explicit commit; PostgreSQL stores committed complaints |
| Duplicate detection source | Committed PostgreSQL history + small fictional seed data; **no** vector database |
| Database access style | Synchronous SQLAlchemy 2.0 (no async DB stack unless a later requirement justifies it) |
| Runtimes | Node.js 22 LTS (frontend); Python 3.12 (backend) |

## 12. Still open (deferred)

1. Transport for file upload (multipart) details and max size limits.
2. Exact Groq model ID string (env-configured when AI phase begins).
