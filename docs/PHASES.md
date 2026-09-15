# PHASES — Incremental Implementation Plan

Every phase must leave the repository in a **working state** (app runs for what exists; tests for that phase pass; docs remain consistent).

Do not start a later phase by breaking earlier demos.

---

## Phase 0 — Documentation

**Goal:** Establish authoritative project documentation.

**Deliverables:**
- README.md
- docs/PROJECT_CONTEXT.md
- docs/PRD.md
- docs/ARCHITECTURE.md
- docs/DOMAIN.md
- docs/DESIGN.md
- docs/RULES.md
- docs/PHASES.md
- docs/AI_WORKFLOW.md
- docs/DEMO.md

**Exit criteria:**
- Docs consistent with PROJECT_CONTEXT
- No application source scaffolding yet (unless a later phase starts)

**Status:** Complete.

---

## Phase 1 — Runnable application foundation

**Goal:** Create frontend and backend project skeletons with mandatory stack, without business features.

**Includes:**
- Monorepo folders `frontend/`, `backend/`
- Vite + React + TypeScript + Redux Toolkit + Inter baseline
- FastAPI app with `/api/v1` prefix, CORS, health + readiness
- Typed pydantic-settings configuration
- Synchronous SQLAlchemy 2.0 + Alembic foundation (no domain models)
- Frontend/backend smoke tests
- `.env.example` files and README run instructions

**Excludes:**
- Complaint functionality, LangGraph, Groq, PyMuPDF
- Dual-pane product UI
- Domain migrations / complaint persistence beyond DB infrastructure

**Exit criteria:**
- Frontend builds and smoke-tests
- Backend `/api/v1/health` returns OK
- Readiness checks PostgreSQL with `SELECT 1` (503 on failure, no secret leakage)
- Alembic initialized against application config

**Status:** Complete.

---

## Phase 2 — Complaint domain contracts and Redux state

**Goal:** Define the canonical complaint data contract (Pydantic + TypeScript) and the Redux complaint draft slice—without UI, API routes, persistence, or AI.

**Includes:**
- `ComplaintFieldValue` co-located provenance model
- Canonical field keys, statuses, patch contract
- Backend domain models + validation tests
- Frontend types + complaint Redux slice + patch semantics tests
- Documentation updates for fields, provenance, dates, patch contract

**Excludes:**
- Complaint form / Copilot UI
- FastAPI complaint endpoints
- SQLAlchemy complaint tables / Alembic domain migrations
- LangGraph, Groq, document parsing, completeness/risk/duplicate logic

**Exit criteria:**
- Empty draft is `pending_triage` with null/missing fields
- Patch updates only listed fields; unrelated fields unchanged
- Frontend build + Vitest and backend Pytest pass without PostgreSQL

**Status:** Complete.
---

## Phase 3 — Complaint review workspace UI

**Goal:** Implement the permanent dual-pane complaint intake/review workspace (form + Assistant shell) with Redux-backed editing, provenance, and responsive segmented layout—without AI or API.

**Includes:**
- Log Customer Complaint form for all canonical field groups
- Direct editing via `setUserField`
- Provenance / missing / recently-updated presentation
- Status badge + disabled Commit until `ready_to_commit`
- Reset with confirmation
- VeyraQ Assistant shell (inactive composer)
- Desktop split + mobile segmented panes
- UI tests

**Excludes:**
- Complaint API, persistence, LangGraph, Groq, document parsing
- Fake AI responses / fake extraction / completeness / risk generation

**Exit criteria:**
- Workspace renders form + assistant
- Editing updates Redux only for touched fields
- Commit disabled until ready; highlight clears via UI timer
- Frontend build + tests and backend pytest pass

**Status:** Complete.

---

## Phase 4 — Committed complaint persistence and API

**Goal:** Persist human-reviewed complaints to PostgreSQL via an explicit commit API—no AI.

**Includes:**
- SQLAlchemy `Complaint` model + Alembic migration
- Values in columns + provenance in `field_metadata` JSON
- `POST /api/v1/complaints/commit`, `GET /complaints`, `GET /complaints/{id}`
- Server-side required-field validation and complaint-number generation
- Frontend commit flow (fetch + Redux commit metadata + locked committed UI)
- Idempotent fictional demo seed script (`CMP-DEMO-*`)

**Excludes:**
- LangGraph, Groq, document parsing, duplicate scoring, AI risk/CAPA
- PUT/PATCH/DELETE for committed records

**Exit criteria:**
- Valid commit returns 201 with id/number/fields/timestamps
- Missing required fields return 422
- Frontend commit success locks fields and shows complaint number
- Pytest (SQLite test DB) + frontend tests pass; Alembic offline SQL renders

**Status:** Complete.

---

## Phase 5 — LangGraph + Groq text complaint intelligence

**Goal:** Implement the first complete AI-assisted text + correction workflow.

**Includes:**
- Groq service boundary + structured JSON-schema outputs
- LangGraph StateGraph factory (`build_complaint_graph`)
- Source extraction with deterministic evidence grounding
- Correction intent/path with partial patches (`provenance = user`)
- Advisory risk assessment (`provenance = inferred`)
- Deterministic completeness → `needs_information` / `ready_to_commit`
- `POST /api/v1/assistant/process`
- Working Assistant composer, conversation messages, Redux `applyFieldPatch`

**Excludes:**
- PDF/OCR/document parsing, duplicates, RCA, CAPA, RAG/embeddings, streaming, voice

**Exit criteria:**
- Pasting a sample complaint populates the form with grounded `source` values
- Unsupported extracted facts are dropped (not stored as source)
- Conversational corrections update only requested fields
- Failed LLM/provider response does not wipe prior draft
- Advisory risk visible as AI suggestion · Verify
- Ready to Commit is reachable; commit remains a human action

**Status:** Complete.

---

## Phase 6 — Conversational patch corrections

**Goal:** Critical patch semantics via AI correction path (Redux patch merge already exists).

Implemented together with Phase 5 text intelligence (correction graph path, `/assistant/process`, field highlight).

**Status:** Complete (delivered with Phase 5). Do not start document upload in this phase.

---

## Phase 7 — Document upload path

**Goal:** PDF (and practical TXT/EML) text extraction into the same workflow.

**Includes:**
- `POST /api/v1/assistant/process-document` (multipart)
- `document_service` with PyMuPDF + stdlib TXT/EML (in-memory only)
- Reuse of `build_complaint_graph` (no second AI pipeline)
- Assistant upload/drop UX + mobile review switch after success
- Focused Pytest / Vitest coverage

**Excludes:**
- OCR / scanned-image pipelines, DOCX/XLSX, document persistence, RAG/embeddings

**Exit criteria:**
- Text PDF complaint populates form via same structuring path
- Bad/empty extraction does not invent content
- Populated draft returns 409; grounding still drops ungrounded facts

**Status:** Complete.

## Phase 8 — Tier 1 remaining bonus + hardening

**Goal:** Duplicate detection against committed history (incl. demo seed) and risk polish.

**Includes:**
- `detect_duplicates` optional node wired into workflow/UI context
- Risk classification refinement within `assess_risk`
- Pytest/Vitest expansion
- Error handling UX polish

**Exit criteria:**
- Tier 1 features demonstrable inside complaint workflow
- No out-of-scope infrastructure added

---

## Phase 9 — Tier 2/3 bonuses (only if Tier 1 solid)

**Goal:** Optional advisory intelligence.

**Priority order:**
1. Root cause hypotheses
2. CAPA suggestions
3. Complaint summary (if not already covered by `summarize`)

**Rules:**
- Advisory only
- No full CAPA lifecycle
- Stay inside Copilot/workflow panels

**Exit criteria:**
- Bonuses improve intake narrative without scope creep

---

## Phase 10 — Playwright critical E2E + demo readiness

**Goal:** One critical E2E path + prepare DEMO.md execution.

**Includes:**
- Playwright path covering intake → populate → patch → readiness/commit (with mocks/stubs as needed)
- Seed/sample complaints for video
- README final runbook
- Verify walkthrough chain for recording

**Exit criteria:**
- E2E critical path green in CI or documented local run
- Product demo and code demo can be recorded from a stable build

---

## Phase dependency graph

```
0 Docs
  → 1 Skeleton
    → 2 Models/contracts
      → 3 UI shell
        → 4 Commit persistence + API
          → 5 Text intake AI
            → 6 Patch corrections
              → 7 Documents
                → 8 Tier 1 polish / duplicates
                  → 9 Tier 2/3 optional
                    → 10 E2E + demo
```

**Patch corrections remain critical** and should not be deferred behind bonuses.

---

## Working-state definition

At the end of each phase:
- README run instructions match reality for that phase
- No committed secrets
- Main happy path for completed features works
- Known limitations listed briefly in README or PHASES notes if necessary
