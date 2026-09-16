# DEMO — Final recording plan

Two videos are required. Use fictional data from `demo/` and seeded `CMP-DEMO-*` history. Never show `.env` or API keys on screen.

---

## Shared prep checklist

- [ ] PostgreSQL up; `alembic upgrade head`; `python -m app.scripts.seed_demo_complaints`
- [ ] `GROQ_API_KEY` set locally (not visible on camera)
- [ ] Backend `uvicorn` + frontend `npm run dev`
- [ ] `demo/complaint-email.txt` and `demo/complaint-report.pdf` ready
- [ ] Zoom IDE font; pin files listed in Video 2
- [ ] Fresh draft (New Complaint) before each major act

---

## VIDEO 1 — Product demonstration (~6–8 min)

### 0:00–0:20 — Intro
- VeyraQ: AI-assisted pharmaceutical complaint intake (API + FDF)
- Not a full QMS — intake, review, explicit human commit
- Core promise: assist QA without inventing facts

### 0:20–2:00 — Text complaint
- Dual pane: form left, Assistant right
- Paste `demo/complaint-email.txt` (or the short NovaCare / Cefixime paste from README)
- Show Processing → form populate
- Call out provenance: Extracted vs Not provided vs AI suggestion · Verify
- Call out partial dates kept as text (`April 2026`)
- Point at advisory risk — not a disposition

### 2:00–3:00 — Missing data / completeness
- If Needs Information: show which required fields are missing
- Emphasize: unsupported facts stay missing — no fabricated quantity/patient harm

### 3:00–4:00 — Conversational correction (critical)
- Send: `Correction: 30 capsules were affected.`
- Show **only** affected quantity updates (+ brief highlight)
- Say why: patch semantics — unrelated fields keep value/provenance/evidence

### 4:00–5:00 — Related history + commit
- Show Potential Related Complaints (`CMP-DEMO-0001` / `0002` for CFX260481)
- Explain: deterministic recurrence signal, not automatic duplicate close
- When Ready to Commit → click Commit
- Show complaint number; stress nothing auto-committed

### 5:00–6:30 — Document path + Investigation
- New Complaint → upload `demo/complaint-report.pdf` → Analyze Document
- Same structuring path as text
- Generate Investigation Assistance
- Call out: summary / hypotheses / CAPA are advisory; fields/status/severity unchanged

### 6:30–end — Close
- Human authority + provenance trust model
- Point reviewers to README + `docs/` for engineering depth

---

## VIDEO 2 — Engineering walkthrough (~7–9 min)

Follow the data path. Prefer ~8–10 files, not 25.

### 0:00–0:30 — Frame
- “One request from Assistant to committed PostgreSQL row”

### 0:30–2:00 — Frontend → API
1. `AssistantPanel.tsx` — submit / upload
2. `assistantApi.ts` — `POST /assistant/process`
3. `assistantSlice.ts` — processing guard + `applyFieldPatch` + generation discard after reset
4. `complaintSlice.ts` — co-located provenance fields; commit thunk

### 2:00–4:30 — FastAPI → LangGraph → Groq
5. `api/routes/assistant.py` — validation, safe 503s, no body logging
6. `agents/graph.py` — intent → extract/correct → ground → risk → related → completeness
7. `services/groq_service.py` — only Groq SDK boundary
8. `agents/prompts.py` + schemas — central prompts; structured outputs
9. `agents/grounding.py` — evidence must appear in source text

**Talking points**
- Why source facts are grounded
- Why correction is a partial patch
- Why related matching is deterministic

### 4:30–6:30 — Documents, related, investigation, commit
10. `document_service.py` — in-memory PDF/TXT/EML; limits; no OCR
11. `related_complaint_service.py` — scoring gates + reasons
12. `investigation_service.py` — one Groq call; non-mutating; supporting-field validation
13. `complaint_service.py` + `db/models/complaint.py` — server commit validation; JSON metadata; immutable API

### 6:30–8:00 — Tests + close
- Pytest: patch isolation / grounding / investigation non-mutation
- Vitest: Redux merge + stale-response discard
- Playwright: mocked critical path (`npm run test:e2e`)
- Restate: AI assists; humans commit

---

## Interview-worthy lines (use naturally)

- “The model proposes values with evidence; the backend decides whether they become source.”
- “A correction is a patch map, not a regenerated complaint.”
- “Related history has to explain itself — batch equality is exact, never fuzzy.”
- “Investigation Assistance cannot change severity, priority, status, or fields.”
- “Commit is an explicit human action validated again on the server.”

---

## Anti-goals

Do not spend time on auth, Kubernetes, marketing UI, OCR theater, or regulatory certification claims.
