# PROJECT_CONTEXT — VeyraQ

This document is the **authoritative, non-negotiable** project context. All other docs, code, and AI-assisted work must conform to it. If another document conflicts with this file, **this file wins**.

---

## 1. Project identity

| Field | Value |
| --- | --- |
| Name | VeyraQ |
| Tagline | AI-Assisted Pharmaceutical Complaint Intelligence |
| Assessment | AI Product Engineer internship — AIVOA |
| Scope | Focused pharmaceutical customer **complaint intake** module |

VeyraQ is **not** a full QMS platform. It covers complaint intake, AI-assisted structuring, human review, and commit to a QMS-style record store. It does not expand into unrelated QMS modules unless explicitly approved later.

---

## 2. Purpose

Build an AI-powered Customer Complaint Management System for pharmaceutical manufacturing covering **API** and **FDF** complaint intake.

The system assists human QA personnel. It does not replace human judgment.

---

## 3. Mandatory AIVOA workflow

The product must follow this workflow:

1. User enters an unstructured customer complaint as text/email **or** uploads a complaint document.
2. AI extracts structured complaint information.
3. Extracted data populates the Log Customer Complaint interface.
4. AI produces an initial complaint risk assessment.
5. User may correct individual complaint details conversationally.
6. Corrections must update **ONLY** the fields explicitly corrected.
7. The system checks complaint completeness.
8. User reviews the record.
9. Complaint becomes **Ready to Commit** only when required conditions are satisfied.
10. Human **explicitly** commits the complaint to the QMS-style record store.

---

## 4. Mandatory technologies (non-substitutable)

### Frontend
- React
- Redux state management
- Google Inter font

### Backend
- Python
- FastAPI

### AI
- LangGraph
- Groq

### Database
- PostgreSQL

**Do not substitute** these technologies.

---

## 5. Final technology decisions

These extend the mandatory set and are locked for implementation:

| Area | Decision |
| --- | --- |
| Frontend | React, TypeScript, Vite, Redux Toolkit, CSS Modules, semantic HTML, accessible components, Inter |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PostgreSQL |
| AI | LangGraph StateGraph, Groq SDK/API, structured Pydantic-compatible responses |
| Documents | PyMuPDF for normal PDF text extraction; simple TXT/EML support if practical; **no** production OCR system |
| Testing | Pytest, Vitest, Playwright for **one** critical end-to-end workflow |

---

## 6. Core product principle — provenance

AI must **NEVER** silently invent complaint facts.

| Provenance | Meaning |
| --- | --- |
| **SOURCE VALUE** | Explicitly found in customer text/document |
| **USER VALUE** | Directly entered or corrected by the user |
| **INFERRED VALUE** | Suggested by AI but not explicitly stated in source material |
| **MISSING VALUE** | Cannot be reliably determined |

Rules:
- AI-inferred information must be visually distinguishable.
- Inferred values must not be silently treated as verified source information.
- When information is missing, prefer **"Not provided"** over hallucinating a plausible value.
- Missing values remain `null` / Not Provided in data.

---

## 7. Core complaint fields

### Origin & customer details
- complaint source
- customer name

### Product & batch identification
- product name
- product strength / grade
- batch / lot number
- affected quantity
- manufacturing date
- expiry date

### Facility & material impact
- originating site block
- impacted non-product materials

### Defect analysis
- complaint category
- complaint description

### AI initial assessment
- suggested severity
- suggested next action
- initial risk assessment

### Record status
- Pending Triage
- Processing
- Needs Information
- Ready to Commit
- Committed

---

## 8. Core interaction requirements

### Text complaint flow
raw complaint → intent detection → structured extraction → normalization → validation → completeness check → risk assessment → populate Redux complaint state → human review

### Document flow
document upload → text extraction → same structured AI workflow → populate complaint state → human review

### Correction flow (critical)
Example user message: *"The batch is BMX240602 and affected quantity is 48 capsules."*

Expected result — **ONLY**:
- `batch_number` = BMX240602
- `affected_quantity` = 48 capsules

No other field may be regenerated or overwritten. **Patch behavior is a critical project requirement.**

---

## 9. LangGraph constraints

- Do **not** create unnecessary autonomous agents.
- Use **one** understandable stateful workflow.
- Every node must have a clear purpose.

Conceptual nodes (authoritative list):

**Shared**
- `detect_intent`

**New complaints**
- `extract_complaint`
- `normalize_fields`
- `validate_fields`
- `check_completeness`
- `assess_risk`
- `summarize`

**Corrections**
- `extract_patch`
- `validate_patch`
- `apply_patch`
- `reassess_affected_outputs_if_required`

**Documents**
- `extract_document_text` then reuse the standard complaint workflow

**Optional later intelligence** (not required for MVP unless phased in):
- `detect_duplicates`
- `suggest_root_causes`
- `suggest_capa`

---

## 10. AI reliability rules

1. Never invent missing complaint facts.
2. All structured LLM responses must be schema validated.
3. AI inference must remain distinguishable from source extraction.
4. Failed model responses must not corrupt complaint state.
5. Correction prompts must update only explicitly requested fields.
6. Missing values remain null / Not Provided.
7. Risk assessment is advisory.
8. Final decision remains with QA/user.
9. Prompts must be stored centrally rather than scattered throughout the codebase.
10. Model identifiers must be configurable via environment variables.
11. Do not hard-code secrets.
12. Handle unavailable/deprecated Groq models through configuration rather than spreading model names across code.

---

## 11. Bonus AI features (priority order)

| Tier | Features |
| --- | --- |
| Tier 1 | Complaint Completeness Checker; Duplicate Complaint Detection; AI Risk Classification |
| Tier 2 | Root Cause Hypotheses; CAPA Suggestions |
| Tier 3 | Complaint Summary |

These must integrate into the complaint workflow rather than becoming unrelated pages.

---

## 12. UI / UX direction (locked)

- Enterprise pharmaceutical quality tool: trustworthy, precise, modern, clean, professional, information-dense without feeling crowded.
- **Not**: marketing site, cyberpunk dashboard, glassmorphism showcase, oversized analytics dashboard.
- Desktop: **LEFT** = Complaint record form; **RIGHT** = VeyraQ Copilot.
- Copilot accepts: complaint text, corrections, document uploads, follow-up questions.
- Form shows: extracted values, user-corrected values, missing values, AI-inferred values, status.
- Conversational corrections briefly highlight the updated field(s).

### Design tokens

| Token | Value |
| --- | --- |
| Canvas | `#F8FAFC` |
| Surface | `#FFFFFF` |
| Primary text | `#111827` |
| Secondary text | `#667085` |
| Border | `#E5E7EB` |
| Primary | `#4F46E5` |
| Primary hover | `#4338CA` |
| AI tint | `#F5F3FF` |
| Success | `#16A34A` |
| Success tint | `#DCFCE7` |
| Warning | `#D97706` |
| Warning tint | `#FEF3C7` |
| Critical | `#DC2626` |
| Font | Inter |

Subtle shadows only where hierarchy requires them. Animations communicate state; they are not decorative.

---

## 13. Explicitly do not build

Unless explicitly approved later, do **not** add:

- authentication / registration
- multi-tenant organizations
- billing
- admin dashboards
- Redis, Kafka, Celery
- microservices, Kubernetes
- vector database, RAG
- full regulatory document search
- advanced OCR pipeline
- email sending infrastructure / notifications
- user management
- large analytics dashboards
- unrelated QMS modules
- deviation management
- SOP management
- full CAPA lifecycle management
- change control

---

## 14. Development philosophy

Assessment values: curiosity, clean code, product thinking, problem solving, understanding the implementation.

Therefore:
- Prefer boring, understandable engineering over clever abstractions.
- Do not create abstractions before they are necessary.
- Do not add dependencies unless they clearly improve the project.
- No deprecated libraries.
- No paid APIs/services except the required Groq integration using available developer access.
- No feature may be added simply because it looks impressive.
- Every important decision must be explainable in an internship interview.

---

## 15. Final deliverables

The final project must support:
- GitHub repository
- product demo video
- engineering/code walkthrough video

The code walkthrough must demonstrate:

frontend input → Redux state → API call → FastAPI endpoint → LangGraph workflow → Groq processing → structured response → form population → risk assessment → persistence

---

## 16. Documentation authority order

1. `docs/PROJECT_CONTEXT.md` (this file)
2. `docs/RULES.md`
3. `docs/PRD.md` / `docs/AI_WORKFLOW.md` / `docs/ARCHITECTURE.md` / `docs/DOMAIN.md` / `docs/DESIGN.md` / `docs/PHASES.md` / `docs/DEMO.md`
4. `README.md` (summary only; must not contradict higher docs)
