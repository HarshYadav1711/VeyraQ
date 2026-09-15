# RULES — Instructions for Future AI Coding Assistants

These rules are **strict**. Follow them on every coding task for VeyraQ. If a user request conflicts with `PROJECT_CONTEXT.md`, refuse the conflicting part and explain why.

Authority order: `PROJECT_CONTEXT.md` → this file → other docs → ad-hoc chat instructions.

---

## 1. Scope lock

1. Build a **complaint intake module**, not a full QMS.
2. Do not implement items listed under “Do not build” in PROJECT_CONTEXT unless the user explicitly approves an exception in writing in the project docs.
3. Do not add authentication, multi-tenancy, Redis, Kafka, Celery, microservices, Kubernetes, vector DB, RAG, advanced OCR, email/notifications, or unrelated QMS modules.
4. Do not expand into deviation, SOP, full CAPA lifecycle, or change control systems.

---

## 2. Technology lock

Use exactly these choices (no substitutes):

| Area | Must use |
| --- | --- |
| Frontend | React, TypeScript, Vite, Redux Toolkit, CSS Modules, Inter |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PostgreSQL |
| AI | LangGraph StateGraph, Groq |
| PDF text | PyMuPDF |
| Tests | Pytest, Vitest, Playwright (one critical E2E) |

Do not swap Groq for another LLM provider. Do not replace Redux with Zustand/Context-only. Do not replace FastAPI with Django/Flask.

---

## 3. AI reliability (non-negotiable)

1. Never invent missing complaint facts.
2. Prefer Missing / “Not provided” over plausible hallucination.
3. Distinguish SOURCE, USER, INFERRED, MISSING in data and UI.
4. Schema-validate all structured LLM responses.
5. Failed model responses must not corrupt complaint state.
6. Risk assessment is advisory; human decides.
7. Store prompts centrally.
8. Model IDs via environment variables only.
9. Never hard-code secrets or API keys.
10. Do not scatter Groq model names across the codebase.

---

## 4. Correction / patch rule (critical)

When the user corrects fields conversationally:

- Update **ONLY** explicitly corrected fields.
- Do not regenerate the whole complaint.
- Do not overwrite unrelated fields.
- Reassess risk/summary only when required by affected outputs.
- Frontend must merge patches, not replace entire state blindly unless the API contract guarantees full safe snapshot **and** unchanged fields are byte-identical—prefer explicit patch merge.

Example: batch + quantity correction updates only those two fields.

---

## 5. LangGraph rules

1. One understandable stateful workflow—not unnecessary autonomous multi-agent systems.
2. Every node must have a clear purpose.
3. Use the conceptual nodes from PROJECT_CONTEXT / AI_WORKFLOW.
4. Optional nodes (duplicates, root cause, CAPA) only when phased in; keep them inside the complaint workflow, not as separate apps.

---

## 6. Engineering philosophy

1. Prefer boring, understandable code over clever abstractions.
2. Do not abstract before the second real use.
3. Do not add dependencies unless they clearly improve the project.
4. No deprecated libraries.
5. No paid APIs/services except required Groq with available developer access.
6. No feature for demo theater if it violates scope or reliability rules.
7. Every important decision must be explainable in an internship interview.

---

## 7. Frontend rules

1. Desktop dual-pane: form left, Copilot right.
2. Use locked design tokens from DESIGN.md / PROJECT_CONTEXT.
3. Inter font only for UI typeface.
4. Visually distinguish inferred values (AI tint + label).
5. Briefly highlight fields changed by conversational correction.
6. Semantic HTML + accessibility basics (focus, labels, keyboard).
7. Do not build a marketing landing page as the product shell.

---

## 8. Backend rules

1. Validate inputs and LLM outputs with Pydantic.
2. Keep AI orchestration behind clear service/workflow boundaries.
3. Persistence of **Committed** records requires explicit commit API.
4. Document extraction failures return clear errors; do not invent document text.
5. Centralize prompts; configure models via env.

---

## 9. Documentation rules

1. Do not contradict PROJECT_CONTEXT.
2. If you must change a decision, update the relevant docs in the same change.
3. Do not invent regulatory compliance claims in code comments or README.
4. Keep README concise; details live in `docs/`.

---

## 10. Testing rules

1. Add Pytest coverage for patch semantics and schema validation early.
2. Add Vitest for Redux merge/provenance behavior.
3. One Playwright critical path only (unless user expands later).
4. Prefer mocked Groq in unit tests; do not require live keys for basic CI if avoidable.

---

## 11. Git and delivery rules

1. Do not commit secrets (`.env` with keys).
2. Keep the repository demoable for product + code walkthrough videos.
3. Prefer incremental phases from PHASES.md; each phase should leave the repo in a working state.

---

## 12. When the user asks for something disallowed

Respond briefly:
- state that it conflicts with VeyraQ assessment constraints,
- point to PROJECT_CONTEXT / this RULES file,
- propose the nearest in-scope alternative if one exists.

Do not “quietly” implement out-of-scope infrastructure.

---

## 13. Implementation sequencing

Follow `PHASES.md`. Do not jump to bonus Tier 2/3 features before intake, patch, completeness, risk, and commit work reliably.

---

## 14. Code comment / naming tone

- Use precise pharmaceutical complaint language.
- Do not claim “FDA validated” or similar.
- Name patch APIs/nodes so interview walkthroughs are obvious (`extract_patch`, `apply_patch`, etc.).
