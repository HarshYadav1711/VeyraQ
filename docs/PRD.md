# PRD — Product Requirements Document

## 1. Problem

Pharmaceutical QA teams receive customer complaints as unstructured email, free text, or attached documents. Manual transcription into structured complaint logs is slow, error-prone, and inconsistent—especially across **API** (Active Pharmaceutical Ingredient) and **FDF** (Finished Dosage Form) contexts.

QA needs a focused intake tool that:
- structures complaint information quickly,
- surfaces risk advisory signals,
- preserves human authority,
- never silently invents facts.

---

## 2. Product summary

**VeyraQ** is an AI-assisted pharmaceutical customer complaint intake module.

It turns unstructured complaint input into a structured Log Customer Complaint record, supports conversational corrections with **field-level patching**, checks completeness, and commits only when a human explicitly approves.

VeyraQ is **not** a complete QMS.

---

## 3. Primary user

| Attribute | Description |
| --- | --- |
| Role | Pharmaceutical QA / complaint handling personnel |
| Goal | Accurately log customer complaints with minimal re-keying |
| Constraint | Must trust provenance of each field; cannot accept silent AI invention |
| Authority | Final review and commit decision |

Assumptions for this assessment:
- Single-user local/demo usage (no authentication).
- User understands basic pharmaceutical complaint terminology (see `DOMAIN.md`).

---

## 4. Goals

1. Reduce time from raw complaint to structured draft record.
2. Make AI assistance trustworthy via provenance (source / user / inferred / missing).
3. Enforce correction patch semantics so unrelated fields are never overwritten.
4. Gate commit behind completeness and explicit human action.
5. Keep architecture interview-explainable end-to-end.

### Non-goals

Anything listed in [PROJECT_CONTEXT.md §13](PROJECT_CONTEXT.md) and §11 of this PRD.

---

## 5. Core workflows

### 5.1 Text complaint intake

1. User pastes or types complaint text into the Copilot.
2. System detects intent as new complaint.
3. AI extracts, normalizes, validates fields; checks completeness; assesses risk.
4. Structured result populates the left-pane complaint form (Redux).
5. User reviews provenance-tagged fields and advisory risk output.
6. User may correct via Copilot or direct form edit (MVP). Manual edits set provenance = user.
7. When Ready to Commit conditions are met, user explicitly commits.
8. Record persists as **Committed**.

### 5.2 Document complaint intake

1. User uploads a complaint document (PDF preferred; TXT/EML if supported).
2. System extracts text (PyMuPDF for PDF; no production OCR).
3. Extracted text enters the same structured AI workflow as §5.1.
4. Form population, review, correction, and commit proceed identically.

**Document failure behavior:** If text cannot be extracted, the system must report a clear error and must not invent complaint content.

### 5.3 Conversational correction (critical)

1. User states a correction in natural language (example: batch and quantity).
2. System detects intent as correction/patch.
3. AI extracts a **patch** of only explicitly corrected fields.
4. Patch is validated and applied.
5. Only patched fields update in Redux/form state; other fields remain unchanged.
6. Affected advisory outputs (e.g., risk) may be reassessed **only if required**.
7. Updated fields are briefly highlighted in the UI.

### 5.4 Completeness and readiness

1. System evaluates required fields and completeness rules.
2. Status moves among: Pending Triage, Processing, Needs Information, Ready to Commit, Committed.
3. **Ready to Commit** is available only when required conditions are satisfied.
4. Commit requires an explicit human action (not automatic).

### 5.5 Follow-up questions

The Copilot may accept follow-up questions about the current complaint draft (e.g., what is missing). Answers must not invent missing source facts.

---

## 6. Functional requirements

### FR-1 Complaint intake (text)
The system shall accept unstructured complaint text and produce a structured complaint draft.

### FR-2 Complaint intake (document)
The system shall accept uploaded documents, extract text when possible, and produce a structured complaint draft via the same AI workflow.

### FR-3 Structured field population
The system shall populate the Log Customer Complaint interface with the core fields defined in PROJECT_CONTEXT.

### FR-4 Provenance
Every populated field value shall carry provenance: source, user, inferred, or missing.

### FR-5 Initial risk assessment
The system shall produce an advisory initial risk assessment including suggested severity and suggested next action.

### FR-6 Conversational patch corrections
Corrections shall update only explicitly corrected fields.

### FR-7 Completeness checker
The system shall evaluate complaint completeness and reflect status accordingly (Tier 1 bonus, integrated in workflow).

### FR-8 Human commit
The system shall persist a complaint only after explicit user commit. The backend independently validates required fields and assigns record identity. Committed records are immutable through the current assessment API (no update/delete). Authentication/RBAC would be required for real deployment and is out of scope for this assessment.

### FR-9 Dual-pane desktop UI
Desktop layout shall show complaint form (left) and VeyraQ Copilot (right).

### FR-10 Field highlight on correction
When a conversational correction updates a field, that field shall briefly highlight.

### FR-11 Failed AI safety
Failed or invalid model responses shall not corrupt existing complaint state.

### FR-12 Configurable Groq model
Model identifiers shall be environment-configurable; secrets shall not be hard-coded.

### FR-13 Central prompts
Prompts shall be stored centrally.

---

## 7. Bonus feature requirements (priority)

| ID | Tier | Requirement | Integration rule |
| --- | --- | --- | --- |
| B1 | 1 | Complaint Completeness Checker | Part of intake/correction workflow and status |
| B2 | 1 | Duplicate Complaint Detection | Optional node; surface in Copilot/form context |
| B3 | 1 | AI Risk Classification | Part of `assess_risk` / advisory panel |
| B4 | 2 | Root Cause Hypotheses | Advisory only; not a CAPA module |
| B5 | 2 | CAPA Suggestions | Suggestions only; not full CAPA lifecycle |
| B6 | 3 | Complaint Summary | Compact summary in Copilot/workflow |

Bonus features must not become unrelated pages or expand into full QMS modules.

---

## 8. Non-functional requirements

| ID | Requirement |
| --- | --- |
| NFR-1 | Stack must match mandatory technologies in PROJECT_CONTEXT |
| NFR-2 | Boring, understandable architecture preferred over clever abstractions |
| NFR-3 | Schema validation for all structured LLM outputs |
| NFR-4 | Accessible semantic HTML; keyboard operable primary flows |
| NFR-5 | Automated tests: Pytest (backend), Vitest (frontend), one Playwright E2E critical path |
| NFR-6 | Demo and code walkthrough must be demonstrable from a clean narrative (see DEMO.md) |

---

## 9. Acceptance criteria

### AC-1 Text intake
Given a valid unstructured complaint text, when the user submits it, then the form populates with structured fields and provenance, and an advisory risk assessment is shown.

### AC-2 Document intake
Given a text-extractable PDF complaint, when uploaded, then extracted text flows through the AI workflow and populates the form without inventing unread content.

### AC-3 Patch correction
Given an existing draft and the message *"The batch is BMX240602 and affected quantity is 48 capsules."*, when processed, then **only** `batch_number` and `affected_quantity` change; all other fields remain unchanged.

### AC-4 Missing values
Given source text that omits a field, when extracted, then that field is Missing / "Not provided" and is not hallucinated.

### AC-5 Inferred distinction
Given an inferred value, when displayed, then it is visually distinguishable from source and user values.

### AC-6 Completeness gate
Given incomplete required information, when evaluated, then status is not Ready to Commit (typically Needs Information).

### AC-7 Explicit commit
Given Ready to Commit status, when the user has not clicked commit, then the record is not Committed; when they explicitly commit, then it persists as Committed.

### AC-8 AI failure isolation
Given an invalid/failed Groq/LangGraph response, when handling completes, then prior complaint state remains intact and the user sees a clear error.

### AC-9 Traceability for demo
The implemented path must support the walkthrough chain in DEMO.md (frontend → Redux → API → FastAPI → LangGraph → Groq → structured response → form → risk → persistence).

---

## 10. Status model (product-level)

| Status | Meaning |
| --- | --- |
| Pending Triage | Complaint received / draft created; not yet fully processed |
| Processing | AI workflow in progress |
| Needs Information | Completeness check failed; required info missing |
| Ready to Commit | Required conditions satisfied; awaiting human commit |
| Committed | Human explicitly committed to QMS-style store |

Exact field-level readiness rules are refined in DOMAIN.md and AI_WORKFLOW.md without inventing unsupported regulatory requirements.

---

## 11. Out of scope

Unless explicitly approved later:

- Authentication, registration, user management
- Multi-tenant organizations, billing
- Admin dashboards, large analytics dashboards
- Redis, Kafka, Celery, microservices, Kubernetes
- Vector database, RAG, full regulatory document search
- Advanced OCR pipeline
- Email sending / notifications
- Deviation management, SOP management
- Full CAPA lifecycle management, change control
- Unrelated QMS modules

---

## 12. Success definition for the assessment

A successful VeyraQ submission demonstrates:
- faithful implementation of the AIVOA workflow,
- trustworthy AI provenance and patch corrections,
- clean React/Redux + FastAPI + LangGraph + Groq + PostgreSQL integration,
- restrained product scope,
- clear product and engineering demos.
