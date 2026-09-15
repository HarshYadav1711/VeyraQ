# DOMAIN — Pharmaceutical Complaint Domain Assumptions

This document defines **project-level** terminology and assumptions for VeyraQ.

**Important:** These are working assumptions for an internship assessment product. They are **not** legal, regulatory, or validation claims. VeyraQ does not assert GxP validation, 21 CFR Part 11 compliance, or certified QMS status.

---

## 1. Domain scope

VeyraQ supports **customer complaint intake** for pharmaceutical manufacturing contexts involving:

- **API** — Active Pharmaceutical Ingredient
- **FDF** — Finished Dosage Form (finished drug product)

The module stops at structured intake, advisory assessment, and human commit to a QMS-**style** record store. It does not implement a full quality management system.

---

## 2. Key terms

| Term | Meaning in VeyraQ |
| --- | --- |
| Customer complaint | A report from a customer (or customer-facing channel) regarding a product quality, packaging, labeling, delivery, or related issue |
| Complaint intake | Capturing and structuring complaint information for QA review |
| QMS-style record store | Application database persistence resembling a complaint log entry—not a certified enterprise QMS |
| API (pharma) | Active Pharmaceutical Ingredient (not “application programming interface” in domain text) |
| FDF | Finished Dosage Form |
| Batch / lot number | Manufacturing batch or lot identifier (`batch_lot_number`) |
| Severity (suggested) | Advisory AI classification (`initial_severity`)—not an automatic regulatory disposition |
| Priority | Advisory intake priority signal |
| CAPA | Corrective and Preventive Action — suggestions only; not full CAPA lifecycle |
| Root cause | Hypothesized cause — advisory only |
| Site block | Originating manufacturing site / block / plant area when mentioned or known |
| Non-product materials | Impacted materials that are not the primary product (NPM) |
| Provenance | Origin classification co-located with each field value |

---

## 3. Canonical complaint fields (locked)

Every field is a `ComplaintFieldValue`: `{ value, provenance, confidence, evidence }`.  
Value and provenance are **never** stored in separate parallel maps.

### 3.1 Origin & customer details

| Field key | Description |
| --- | --- |
| `complaint_source` | Channel or origin of the complaint |
| `customer_name` | Customer or reporting organization/person |

### 3.2 Product & batch identification

| Field key | Description |
| --- | --- |
| `product_name` | Product or material complained about |
| `product_strength_grade` | Strength, grade, or similar attribute |
| `batch_lot_number` | Batch or lot identifier |
| `affected_quantity` | Impacted quantity (retain units, e.g. “48 capsules”) |
| `manufacturing_date` | Manufacturing date **as textual intake string** |
| `expiry_date` | Expiry date **as textual intake string** |

### 3.3 Complaint details

| Field key | Description |
| --- | --- |
| `complaint_date` | Complaint date **as textual intake string** |
| `complaint_category` | Defect/issue category (UI may label “Complaint Type / Category”) |
| `complaint_description` | Description of the complaint |

Do **not** create a separate `complaint_type` field unless a later requirement justifies both.

### 3.4 Facility & material impact

| Field key | Description |
| --- | --- |
| `originating_site_block` | Site/block associated with manufacture or handling |
| `impacted_non_product_materials` | Impacted non-product materials (NPM) |

### 3.5 Initial assessment (advisory)

| Field key | Description |
| --- | --- |
| `initial_severity` | Suggested severity |
| `priority` | Suggested priority |
| `suggested_next_action` | Suggested next step for QA |
| `initial_risk_assessment` | Advisory risk narrative / classification |

Assessment fields are never final dispositions.

---

## 4. Provenance definitions (locked)

| Provenance | Meaning |
| --- | --- |
| `source` | Explicitly present in customer text/document and extracted from that source |
| `user` | Directly entered, edited, or corrected by the human |
| `inferred` | AI suggested; not explicitly stated by the source |
| `missing` | No reliable value (`value = null`) |

Rules:
- Empty initial fields use `provenance = missing` and `value = null`.
- User edits use `provenance = user`; do not invent `confidence` / `evidence` for user-entered fields (leave null).
- AI extraction uses `source` when explicit evidence exists; otherwise prefer `missing` over guessing.
- AI suggestions without explicit source support use `inferred`.
- `confidence` is optional (`null` unless produced by extraction logic); range 0.0–1.0 when set.
- `evidence` is optional (`null` unless supported by source text).

**Hallucination rule:** Never invent facts as `source`. Prefer `missing`.

---

## 5. Intake date / precision rule (locked)

At complaint-intake level, these fields are **strings**, not `Date` / `datetime` types:

- `manufacturing_date`
- `expiry_date`
- `complaint_date`

Source text may contain partial dates such as `"March 2026"` or `"February 2028"`.  
Converting those to `2026-03-01` / `2028-02-01` would invent unsupported day precision.

**Preserve the supplied textual precision.** Later normalization may add structured helpers without destroying the source representation.

---

## 6. Complaint status (locked)

Wire / code values (snake_case):

| Status | Meaning |
| --- | --- |
| `pending_triage` | Initial draft; awaiting or beginning processing/review |
| `processing` | AI workflow running |
| `needs_information` | Required intake information incomplete |
| `ready_to_commit` | Completeness/readiness conditions satisfied; awaiting human commit |
| `committed` | Human explicitly committed the record |

Initial draft status: **`pending_triage`**.

### Committed records (locked)

- A **draft** is editable and client-side until commit.
- A **committed** complaint is persisted in PostgreSQL with a server-generated UUID and readable `complaint_number` (assessment format `CMP-{UTC year}-{suffix}`).
- This numbering is **not** a validated pharmaceutical production sequence; a real QMS would replace it with an organization-controlled generator.
- The current assessment API treats committed records as **immutable** (no update/delete endpoints). Regulated amendment/audit would require a separate design.
- Successful commit always yields product status `committed`; draft workflow statuses are not persisted as the authoritative committed state.

---

## 7. Completeness assumptions (project-level)

**Locked Ready-to-Commit minimum fields:**
- `complaint_source`
- `customer_name`
- `product_name`
- `batch_lot_number`
- `complaint_category`
- `complaint_description`
- completed `initial_risk_assessment`

Missing any of these critical fields results in **`needs_information`**.

Other fields may legitimately be unavailable and do **not** block Ready to Commit by themselves:
- `affected_quantity`
- `manufacturing_date`
- `expiry_date`
- `complaint_date`
- `originating_site_block`
- `impacted_non_product_materials`
- `priority` / `initial_severity` / `suggested_next_action` as separate advisory signals (risk assessment itself is required when complete)

Duplicate detection (when implemented) uses **committed** PostgreSQL history plus small fictional seed data. No vector database.

---

## 8. API vs FDF assumptions

| Context | Typical complaint cues (illustrative, not exhaustive) |
| --- | --- |
| API | Material identity, grade, impurity/contamination, packaging of bulk, CoA-related customer claims |
| FDF | Dosage form defects, count/quantity, labeling, tablets/capsules appearance, blister/bottle issues |

If API vs FDF cannot be determined, do not invent a classification as source fact.

---

## 9. Risk assessment assumptions

- Risk output is **advisory** for QA.
- Suggested severity, priority, and next action do not auto-commit or auto-notify.
- Reassessment after patch may occur when patched fields could change risk, without rewriting unrelated complaint facts.

---

## 10. Document assumptions

- PDFs with selectable text are the primary document path.
- Scanned-image-only PDFs without OCR are expected to fail extraction gracefully.
- No claim is made that document handling meets regulated controlled-document standards.

---

## 11. What this domain doc does **not** claim

- Compliance with specific FDA/EMA/WHO guidance as a certified implementation
- Validated computer system status
- Electronic signature / Part 11 controls
- Completeness of pharmacovigilance (adverse event) reporting workflows
- That customer complaints and adverse events are the same process

---

## 12. Example (patch semantics)

Source already extracted product and description. User says:

> The batch is BMX240602 and affected quantity is 48 capsules.

Domain-correct outcome:
- `batch_lot_number` becomes user value `BMX240602`
- `affected_quantity` becomes `48 capsules`
- All other domain fields remain as they were
