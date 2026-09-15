# DEMO — Product & Engineering Walkthrough Plan

## 1. Purpose

This document plans the final **product demo video** and **engineering/code walkthrough video** for the VeyraQ assessment.

It is a storyboard, not application code.

---

## 2. Demo environment assumptions

When demos are recorded (after implementation phases):

- Local frontend (Vite) + FastAPI backend + PostgreSQL running
- Groq API key configured via environment
- Sample complaint text and a text-extractable PDF prepared
- No authentication screens (out of scope)

---

## 3. Sample scenario (suggested)

**Persona:** QA specialist logging a customer complaint for an FDF product.

**Raw complaint (text):** a short email-like message including:
- customer name
- product name and strength
- a defect description
- **omit** batch number and affected quantity initially (to show Missing → correction)

**Correction message:**

> The batch is BMX240602 and affected quantity is 48 capsules.

**Document variant:** same narrative in a simple PDF for upload path.

Exact sample files will be added during implementation; content must not invent regulatory case studies beyond plausible fictional demo data.

---

## 4. Product demo story (video)

**Target length:** concise (roughly 5–10 minutes unless otherwise required).

### Act A — Context (30–60s)
- What VeyraQ is: AI-assisted pharmaceutical complaint intake (API/FDF)
- What it is not: not a full QMS
- Core principle: AI assists; humans commit; no silent invention of facts

### Act B — Text intake
1. Show dual-pane UI (form left, Copilot right).
2. Paste unstructured complaint into Copilot.
3. Show Processing status.
4. Show form population with provenance (source vs missing).
5. Show advisory risk assessment (suggested severity, next action, initial risk).
6. Point out Missing fields (“Not provided”) rather than fabricated values.

### Act C — Conversational correction (critical)
1. Send the batch + quantity correction.
2. Show **only** those two fields update.
3. Show brief field highlight.
4. Emphasize patch behavior as a product requirement.

### Act D — Completeness & commit
1. Show completeness/readiness move toward Ready to Commit.
2. Explicitly click Commit.
3. Show Committed status / persistence confirmation.

### Act E — Document path (short)
1. Upload PDF.
2. Show extraction → same structuring outcome.
3. Note: no OCR theater; text PDF only.

### Act F — Optional bonuses (if implemented)
- Duplicate suggestion and/or root cause/CAPA as **advisory** panels inside the same workflow.

### Closing
- Restate human authority and provenance trust model.

---

## 5. Engineering / code walkthrough story (video)

**Narrative spine (mandatory):**

```text
frontend input
  → Redux state
  → API call
  → FastAPI endpoint
  → LangGraph workflow
  → Groq processing
  → structured response
  → form population
  → risk assessment
  → persistence
```

### Segment 1 — Frontend input & Redux
- Copilot submit handler
- Dispatch processing action
- Complaint slice shape (fields + provenance + status)

### Segment 2 — API call & FastAPI
- Request payload
- Router/endpoint for intake
- Pydantic validation

### Segment 3 — LangGraph
- StateGraph overview
- `detect_intent` → extract → normalize → validate → completeness → risk → summarize
- Why one workflow (not multi-agent sprawl)

### Segment 4 — Groq + structured output
- Central prompts location
- Env-configured model ID
- Schema validation before state merge
- Failure isolation

### Segment 5 — Response → form + risk
- API DTO → Redux update
- Provenance rendering
- AI assessment section

### Segment 6 — Correction path
- `extract_patch` → `validate_patch` → `apply_patch`
- Show test or live proof that unrelated fields do not change

### Segment 7 — Persistence
- Commit endpoint
- SQLAlchemy model / PostgreSQL row
- Status Committed

### Optional Segment 8 — Document node
- PyMuPDF `extract_document_text` then reuse workflow

---

## 6. What to show in tests during walkthrough

If time permits:
- Pytest: patch apply leaves unrelated fields unchanged
- Pytest: invalid LLM payload does not corrupt state
- Vitest: Redux merge/provenance
- Playwright: one critical E2E path

---

## 7. Recording checklist

- [ ] Fresh running stack
- [ ] `.env` present locally, not shown on screen (no key leakage)
- [ ] Sample text complaint ready
- [ ] Sample PDF ready
- [ ] Correction phrase ready
- [ ] IDE files pinned for walkthrough (router, graph, prompts, slice, model)
- [ ] Zoom readable fonts in IDE and browser
- [ ] Explicit verbal callout of patch-only update
- [ ] Explicit verbal callout of advisory vs human commit

---

## 8. Anti-goals for demos

Do not spend demo time on:
- building auth
- Kubernetes///infra digressions
- unrelated dashboards
- claiming regulatory certification
- live OCR of scans

---

## 9. Success criteria for demos

| Demo | Success |
| --- | --- |
| Product | Viewer understands intake → review → patch → commit and trusts provenance |
| Code | Viewer can retell the mandatory chain without confusion |
| Assessment fit | Curiosity, product thinking, and implementation understanding are visible |

---

## 10. Dependency on phases

Demos are recorded after Phase 7 minimum (commit works). Ideal after Phase 10 (E2E + polish). Bonuses appear only if implemented and stable.
