# AI_WORKFLOW — LangGraph Design

## 1. Intent

VeyraQ uses **one** LangGraph `StateGraph` to process complaints and corrections.

Goals:
- understandable nodes for internship walkthroughs
- schema-validated structured outputs
- provenance-aware extraction
- critical patch semantics for corrections
- no unnecessary autonomous multi-agent systems

Groq is the LLM provider. Model identifiers come from environment configuration (`GROQ_MODEL`, default `openai/gpt-oss-20b`). The original assessment references `gemma2-9b-it` and mentions `llama-3.3-70b-versatile`; those IDs are no longer generally available on the current Groq developer tier. VeyraQ keeps Groq as the required provider and keeps the model configurable. The default is a currently supported Groq model with strict structured-output support.

---

## 2. Graph state (implemented)

`ComplaintGraphState` (TypedDict) in `backend/app/agents/state.py`:

| Field | Role |
| --- | --- |
| `user_message` | Current Assistant text |
| `current_fields` | Snapshot of the Redux complaint draft |
| `intent` | `new_complaint` or `correction` |
| `blocked` | True when a populated draft would be overwritten by a new complaint |
| `input_kind` | `text` or `document` (deterministic Assistant messaging; same graph topology) |
| `source_extraction` | Last structured LLM payload used by a node |
| `source_patch` / `correction_patch` / `assessment_patch` | Partial `ComplaintPatch` dicts |
| `merged_fields` | Draft after applying patches |
| `missing_required_fields` | Deterministic completeness result |
| `target_status` | `needs_information` or `ready_to_commit` |
| `assistant_message` | Deterministic UI message (no extra phrasing LLM call) |
| `warnings` | Internal grounding/debug notes (not shown in the UI) |
| `should_assess_risk` / `assessment_ran` | Risk-gate flags |
| `request_id` | Logging correlation (no complaint text logged) |

**Rule:** Failed Groq/schema errors abort the request. The API returns 503 and the client does not apply a patch.

Intents remain `new_complaint` and `correction`. Document intake reuses the new-complaint path after deterministic text extraction outside the graph.

---

## 3. Nodes and purposes

Factory: `build_complaint_graph(ai_service)` in `backend/app/agents/graph.py`.

### 3.1 Shared

| Node | Purpose |
| --- | --- |
| `determine_intent` | Empty draft → `new_complaint` with **no** LLM call. Otherwise Groq classifies `new_complaint` vs `correction`. |

### 3.2 New complaint path

| Node | Purpose |
| --- | --- |
| `extract_source_facts` | Groq source extraction (`value` + `evidence` only; no provenance) |
| `verify_and_build_source_patch` | Deterministic evidence grounding; `complaint_description` = trimmed original text (`source`) |
| `merge_patch` | Apply only keys present in the patch |
| `should_assess_risk` | Requires `product_name` and `complaint_description` |
| `assess_risk` | Advisory inferred category / severity / priority / action / risk narrative |
| `merge_assessment` | Assessment fields enter as `provenance = inferred` |
| `check_completeness` | Deterministic required-field check |
| `prepare_response` | Deterministic Assistant message |

### 3.3 Correction path

| Node | Purpose |
| --- | --- |
| `extract_correction_patch` | Groq returns only explicit field changes |
| `validate_correction` | Known keys only; non-null values must appear in the user message; clears use `missing` |
| `merge_patch` | Same partial merge as intake |
| `should_assess_risk` | Re-run risk only for a centralized risk-relevant field set |
| then `assess_risk` / `merge_assessment` / `check_completeness` / `prepare_response` | Same as intake |

Risk-relevant correction fields: `product_name`, `product_strength_grade`, `batch_lot_number`, `affected_quantity`, `complaint_category`, `complaint_description`, `originating_site_block`, `impacted_non_product_materials`. Changing `customer_name` does not refresh risk.

If a populated draft is classified as a new complaint, routing skips extraction and returns a safe message. The draft is not replaced.

### 3.4 Document path

Document bytes are **not** parsed inside LangGraph. FastAPI uses `app/services/document_service.py` to extract plain text (PyMuPDF / TXT / EML) in memory, then invokes the same compiled graph with:

- `user_message` = extracted source text
- `input_kind` = `document`
- empty-draft check enforced at the API (409 if populated)

Because the draft must be empty, `determine_intent` deterministically selects `new_complaint` with **no** intent LLM call. Source grounding, risk, and completeness are unchanged.

### 3.5 Optional later nodes

| Node | Tier | Purpose |
| --- | --- | --- |
| `detect_duplicates` | 1 | Suggest possible duplicate complaints |
| `suggest_root_causes` | 2 | Advisory root-cause hypotheses |
| `suggest_capa` | 2 | Advisory CAPA suggestions |

These integrate into the same graph/UI context—not separate products.

---

## 4. Transitions (implemented)

### New complaint (text)

```
START
  → determine_intent
  → extract_source_facts
  → verify_and_build_source_patch
  → merge_patch
  → should_assess_risk
       /          \
     yes          no
      ↓            │
  assess_risk      │
      ↓            │
 merge_assessment  │
      └──────┬─────┘
             ↓
   check_completeness
             ↓
    prepare_response
             ↓
            END
```

### Correction

```
START
  → determine_intent
  → extract_correction_patch
  → validate_correction
  → merge_patch
  → should_assess_risk
       /          \
     yes          no
      ↓            │
  assess_risk      │
      ↓            │
 merge_assessment  │
      └──────┬─────┘
             ↓
   check_completeness
             ↓
    prepare_response
             ↓
            END
```

Populated draft + `new_complaint` intent:

```
determine_intent → check_completeness → prepare_response → END
```

(no extraction, empty patch)

### Document

```
POST /assistant/process-document
  → validate + extract_document (in-memory)
  → build_complaint_graph (input_kind=document)
  → determine_intent (empty draft → new_complaint, no LLM)
  → extract_source_facts onward (same as text intake)
```

On extraction failure: HTTP error; no fake extraction; draft unchanged.

### Follow-up

Not implemented in Phase 5. If added later, answers must not invent missing source facts and must not silently patch fields unless the user clearly requests a correction.

---

## 5. Structured output rules

1. Every LLM-facing extraction/assessment node defines a **Pydantic-compatible schema**.
2. Responses are parsed and validated before merging into graph state.
3. Invalid responses → 503; no partial corrupt merge into complaint fields.
4. Extraction schema must support explicit null/missing per field (`value` + `evidence`, both required keys).
5. The extraction model does **not** decide provenance. Backend grounding assigns `source` or drops the field.
6. Patch schema must be a **partial** object: only keys present are candidates for update.
7. Prompts instruct the model not to invent values; backend enforces via grounding, validation, and null policy.
8. Completeness is deterministic from required fields. The LLM is not asked whether the complaint is complete.

---

## 6. Provenance assignment rules

| Situation | Provenance |
| --- | --- |
| Extracted value whose evidence span is contained in the complaint text | `source` |
| Value provided/corrected by user message or form edit | `user` |
| Advisory assessment (category, severity, priority, next action, risk narrative) | `inferred` |
| Value unknown / unreliable / explicitly cleared | `missing` (null + “Not provided” in UI) |

**Grounding:** the extraction model returns `value` + `evidence` only. The backend decides `source`. Evidence must be non-blank and contained in the original text after whitespace normalization (case-insensitive). Ungrounded values are dropped from the patch; they are never stored as `source`.

Prefer missing over inferred when a source fact is unsupported. Inferred values must remain distinguishable downstream.

**Correction note:** Conversational corrections are `user`, not source extraction. Confidence and evidence are null. Explicit clears use `value = null` and `provenance = missing`.

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

- Store prompts in `backend/app/agents/prompts.py`.
- Do not bury prompt strings inside unrelated routers.
- Include explicit instructions for anti-hallucination, complaint-text-as-data, and correction patch limits.

---

## 10. Model configuration

- `GROQ_API_KEY` from environment (never committed). FastAPI still boots when it is empty.
- `GROQ_MODEL` from environment (default `openai/gpt-oss-20b`).
- `GROQ_STRUCTURED_OUTPUT_STRICT` defaults to true for strict JSON-schema mode.
- If the configured model is unavailable, the assistant endpoint fails with a safe 503. There is no multi-model fallback.
- Code must not hard-code obsolete assessment model IDs into inference.

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
