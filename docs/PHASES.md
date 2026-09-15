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

## Phase 3 — Dual-pane UI shell

**Goal:** Implement DESIGN.md layout with tokens, form sections, Copilot chrome, status display.

**Includes:**
- Left form sections for all core field groups
- Right Copilot panel layout (input, upload affordance, message list UI)
- Provenance presentation components
- Commit button disabled/enabled wiring to status (even if backend commit comes later)

**Exit criteria:**
- Desktop dual-pane matches design direction
- Missing fields show “Not provided”
- No marketing-page aesthetic

---

## Phase 4 — LangGraph workflow (text intake)

**Goal:** Implement one StateGraph for new complaint text intake through summarize/risk.

**Includes:**
- Nodes: `detect_intent`, `extract_complaint`, `normalize_fields`, `validate_fields`, `check_completeness`, `assess_risk`, `summarize`
- Central prompts
- Groq via env-configured model
- Pydantic validation of structured outputs
- FastAPI intake endpoint
- Frontend wiring: Copilot submit → API → Redux populate

**Exit criteria:**
- Pasting a sample complaint populates the form
- Missing values remain Not provided
- Failed LLM response does not wipe prior draft
- Advisory risk visible

---

## Phase 5 — Conversational patch corrections

**Goal:** Critical patch semantics.

**Includes:**
- Correction path nodes: `extract_patch`, `validate_patch`, `apply_patch`, `reassess_affected_outputs_if_required`
- API correct endpoint
- Redux patch merge
- Field highlight on updated fields

**Exit criteria:**
- AC-3 from PRD passes (only batch + quantity change in the example)
- Unrelated fields untouched
- Tests cover patch merge (Pytest and/or Vitest)

---

## Phase 6 — Document upload path

**Goal:** PDF (and practical TXT/EML) text extraction into the same workflow.

**Includes:**
- Upload endpoint
- `extract_document_text` with PyMuPDF
- Graceful failure for non-extractable files
- Copilot upload UX

**Exit criteria:**
- Text PDF complaint populates form via same structuring path
- Bad/empty extraction does not invent content

---

## Phase 7 — Completeness, readiness, commit, persistence

**Goal:** Status model + PostgreSQL commit path.

**Includes:**
- Completeness checker integrated (Tier 1)
- Status transitions: Needs Information / Ready to Commit / etc.
- Explicit commit endpoint + DB persistence
- UI commit enablement rules

**Exit criteria:**
- Incomplete drafts cannot commit
- Explicit commit stores Committed record
- Retrieve/demonstrate persistence in demo

---

## Phase 8 — Tier 1 remaining bonus + hardening

**Goal:** Duplicate detection (if feasible) and stronger risk classification integration; reliability polish.

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
        → 4 Text intake AI
          → 5 Patch corrections
            → 6 Documents
              → 7 Completeness + commit
                → 8 Tier 1 polish
                  → 9 Tier 2/3 optional
                    → 10 E2E + demo
```

Phases 5 and 6 could swap if needed, but **patch corrections are critical** and should not be deferred behind bonuses.

---

## Working-state definition

At the end of each phase:
- README run instructions match reality for that phase
- No committed secrets
- Main happy path for completed features works
- Known limitations listed briefly in README or PHASES notes if necessary
