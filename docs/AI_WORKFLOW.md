# AI_WORKFLOW — LangGraph Design

## 1. Intent

VeyraQ uses **one** LangGraph `StateGraph` to process complaints and corrections.

Goals:
- understandable nodes for internship walkthroughs
- schema-validated structured outputs
- provenance-aware extraction
- critical patch semantics for corrections
- no unnecessary autonomous multi-agent systems

Groq is the LLM provider. Model identifiers come from environment configuration.

---

## 2. Graph state (conceptual)

The graph state is a single typed object (exact fields finalized in implementation) carrying at least:

| Area | Contents |
| --- | --- |
| Input | raw_text, optional document metadata, user_message |
| Intent | `new_complaint` \| `correction` \| `follow_up` \| `unknown` (final enum set may refine) |
| Complaint draft | core fields + per-field provenance |
| Patch | set of field updates for correction path |
| Validation | field-level validation issues |
| Completeness | missing required/desired fields, readiness flag/signals |
| Assessment | suggested_severity, suggested_next_action, initial_risk_assessment |
| Summary | short complaint summary (Tier 3 / summarize node) |
| Optional intelligence | duplicates, root_cause_hypotheses, capa_suggestions |
| Control | errors, model/config references, flags for reassessment |

**Rule:** Failed node outputs must set error information without applying corrupt field mutations to the durable draft snapshot used for response.

---

## 3. Nodes and purposes

### 3.1 Shared

| Node | Purpose |
| --- | --- |
| `detect_intent` | Classify user/document request: new complaint vs correction vs follow-up |

### 3.2 New complaint path

| Node | Purpose |
| --- | --- |
| `extract_complaint` | Extract structured fields from raw text with provenance candidates |
| `normalize_fields` | Normalize formats (dates, quantity strings, batch tokens) without inventing values |
| `validate_fields` | Schema/business validation of present values |
| `check_completeness` | Determine missing info and readiness signals |
| `assess_risk` | Advisory severity, next action, risk assessment |
| `summarize` | Concise summary for Copilot/review |

### 3.3 Correction path

| Node | Purpose |
| --- | --- |
| `extract_patch` | Extract **only** explicitly corrected fields from user message |
| `validate_patch` | Validate patch fields only |
| `apply_patch` | Merge patch into existing draft; leave all other fields unchanged |
| `reassess_affected_outputs_if_required` | Optionally refresh risk/summary/completeness when inputs that affect them changed |

### 3.4 Document path

| Node | Purpose |
| --- | --- |
| `extract_document_text` | Extract plain text via PyMuPDF / TXT / EML; fail clearly if empty/unreadable |

Then reuse the standard new-complaint workflow on extracted text.

### 3.5 Optional later nodes

| Node | Tier | Purpose |
| --- | --- | --- |
| `detect_duplicates` | 1 | Suggest possible duplicate complaints |
| `suggest_root_causes` | 2 | Advisory root-cause hypotheses |
| `suggest_capa` | 2 | Advisory CAPA suggestions |

These integrate into the same graph/UI context—not separate products.

---

## 4. Transitions (conceptual)

### New complaint (text)

```
detect_intent
  → (new_complaint) extract_complaint
  → normalize_fields
  → validate_fields
  → check_completeness
  → assess_risk
  → summarize
  → END
```

Optional later: insert `detect_duplicates` after normalize/validate or after completeness; insert root cause/CAPA after risk if enabled.

### Correction

```
detect_intent
  → (correction) extract_patch
  → validate_patch
  → apply_patch
  → reassess_affected_outputs_if_required
  → END
```

`reassess_affected_outputs_if_required` may call completeness and/or risk (and summary) sub-logic when patched fields can change those outputs. It must **not** re-extract unrelated complaint facts.

### Document

**Locked path** (input type already known — do **not** run `detect_intent`):

```
extract_document_text
  → (on success) extract_complaint
  → normalize_fields
  → validate_fields
  → check_completeness
  → assess_risk
  → summarize
  → END
  → (on failure) END with error
```

Document upload uses deterministic text extraction, then enters the complaint extraction graph at `extract_complaint`.

### Follow-up

If intent is follow-up Q&A:
- answer from current draft + known gaps
- do not invent missing source facts
- do not silently patch fields unless user clearly requests a correction (prefer routing to correction intent when appropriate)

---

## 5. Structured output rules

1. Every LLM-facing extraction/assessment node defines a **Pydantic-compatible schema**.
2. Responses are parsed and validated before merging into graph state.
3. Invalid responses → node error path; no partial corrupt merge into complaint fields.
4. Extraction schema must support explicit null/missing per field.
5. Extraction should return provenance per field, or enough evidence tags for the backend to assign SOURCE vs INFERRED vs MISSING.
6. Patch schema must be a **partial** object: only keys present are candidates for update.
7. Prompts instruct the model not to invent values; backend enforces via validation and null policy.

---

## 6. Provenance assignment rules

| Situation | Provenance |
| --- | --- |
| Value explicitly present in source text/document | `source` |
| Value provided/corrected by user message or form edit | `user` |
| Value suggested by model without explicit source span/support | `inferred` |
| Value unknown / unreliable | `missing` (null + “Not provided” in UI) |

Prefer missing over inferred when confidence is weak. Inferred values must remain distinguishable downstream.

**Correction note:** Values introduced by correction messages are `user` (user-provided corrections), not source—unless the product later adds an explicit “confirm source” action (not required now).

---

## 7. Hallucination prevention

1. Prompt rules: never fabricate batch numbers, dates, customer names, quantities.
2. Schema allows nulls.
3. Normalization may reformat, not fabricate.
4. Risk/summary nodes may reason over known fields but must not backfill core facts.
5. Document failure ≠ opportunity to invent; return error.
6. Unit tests should include “missing field stays missing” cases.
7. Patch tests must assert untouched fields remain identical.

---

## 8. Patch semantics (critical)

Corrections and structured extraction results update the draft via an explicit **patch contract**:

```json
{
  "changes": {
    "batch_lot_number": {
      "value": "BMX240602",
      "provenance": "user",
      "confidence": null,
      "evidence": null
    },
    "affected_quantity": {
      "value": "48 capsules",
      "provenance": "user",
      "confidence": null,
      "evidence": null
    }
  }
}
```

Rules:
- Only keys present under `changes` may update.
- Unrelated fields must remain unchanged (same values and provenance).
- Do **not** define correction behavior as “regenerate the complete complaint.”
- Extraction may emit a patch with `provenance: source` (explicit evidence) or `inferred` (AI suggestion without explicit source statement).
- Conversational corrections and manual edits use `provenance: user`.
- Applying a patch does not by itself change complaint status.

Example user message:

> The batch is BMX240602 and affected quantity is 48 capsules.

Expected: only `batch_lot_number` and `affected_quantity` change.

---

## 9. Prompt management

- Store prompts in a **central** module/directory (e.g., `backend/app/ai/prompts/`).
- Do not bury prompt strings inside unrelated routers.
- Versioning can be simple filenames/constants; no premature prompt CMS.
- Include explicit instructions for provenance and anti-hallucination in extraction/patch prompts.

---

## 10. Model configuration

- `GROQ_API_KEY` from environment (never committed).
- Model identifier(s) from environment (e.g., `GROQ_MODEL`).
- If a model is unavailable/deprecated, change config—not scattered literals.
- Code may map logical roles (`extraction_model`, `assessment_model`) to env vars if needed, still centralized.

---

## 11. Failure handling

| Failure | Behavior |
| --- | --- |
| Groq timeout/API error | Return error; preserve prior complaint draft |
| Invalid JSON/schema | Reject; preserve prior draft |
| Unknown intent | Ask user to clarify; no destructive updates |
| Empty document text | Error; no fake extraction |
| Patch with zero fields | No-op fields; inform user nothing applied |

---

## 12. Bonus integration map

| Feature | Node / output | UI placement |
| --- | --- | --- |
| Completeness Checker | `check_completeness` | Status + missing list in form/Copilot |
| Duplicate Detection | `detect_duplicates` | Copilot advisory / contextual banner |
| AI Risk Classification | `assess_risk` | AI initial assessment section |
| Root Cause Hypotheses | `suggest_root_causes` | Advisory panel / Copilot |
| CAPA Suggestions | `suggest_capa` | Advisory panel / Copilot |
| Complaint Summary | `summarize` | Copilot / header summary |

---

## 13. Demo walkthrough alignment

The graph must make this chain easy to show:

API handler → build state → LangGraph invoke → node(s) call Groq → validated structured result → response DTO → Redux form population → risk section → later persistence on commit

Node names in code should stay close to this document for oral walkthrough clarity.
