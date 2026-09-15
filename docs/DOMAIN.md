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
| Batch / lot number | Manufacturing batch or lot identifier supplied by the customer or source text |
| Severity (suggested) | Advisory AI classification of complaint seriousness—not an automatic regulatory disposition |
| CAPA | Corrective and Preventive Action — VeyraQ may **suggest** ideas only; it does not run CAPA lifecycle |
| Root cause | Hypothesized cause — advisory only |
| Site block | Originating manufacturing site / block / plant area when mentioned or known |
| Non-product materials | Impacted materials that are not the primary product (e.g., packaging components) when relevant |
| Provenance | Origin classification of a field value: source, user, inferred, missing |

---

## 3. Complaint field dictionary

Field names below are **logical**. Implementation may use snake_case equivalents.

### 3.1 Origin & customer details

| Field | Description | Typical source |
| --- | --- | --- |
| complaint_source | Channel or origin of the complaint (e.g., email, phone note, document) | User / source text / inferred only if clearly implied—prefer missing if unclear |
| customer_name | Customer or reporting organization/person name | Source text preferred |

### 3.2 Product & batch identification

| Field | Description |
| --- | --- |
| product_name | Name of the product or material complained about |
| product_strength_grade | Strength, grade, or similar identifying quality attribute |
| batch_number | Batch or lot identifier |
| affected_quantity | Quantity impacted (retain units when present, e.g., “48 capsules”) |
| manufacturing_date | Manufacturing date if provided |
| expiry_date | Expiry date if provided |

### 3.3 Facility & material impact

| Field | Description |
| --- | --- |
| originating_site_block | Site/block associated with manufacture or handling, if provided |
| impacted_non_product_materials | Non-product materials impacted, if provided |

### 3.4 Defect analysis

| Field | Description |
| --- | --- |
| complaint_category | Category label for the defect/issue type |
| complaint_description | Structured or cleaned description of the complaint |

### 3.5 AI initial assessment (advisory)

| Field | Description |
| --- | --- |
| suggested_severity | AI-suggested severity |
| suggested_next_action | AI-suggested next step for QA consideration |
| initial_risk_assessment | Short advisory risk narrative / classification output |

These assessment fields are **never** final dispositions.

---

## 4. Provenance model (domain rules)

| Provenance | Domain meaning | UI implication |
| --- | --- | --- |
| source | Explicitly present in customer text/document | Treated as extracted evidence |
| user | Entered or corrected by QA user | Highest human trust for that field |
| inferred | AI suggested; not explicit in source | Must look different; not silently equated to source |
| missing | Not reliably determinable | Display “Not provided”; store null/empty equivalent |

**Hallucination rule:** If the source does not contain a fact, the system must not invent it as source. Prefer missing. Inferred values, when used, must be labeled inferred.

---

## 5. Status semantics

| Status | Domain meaning |
| --- | --- |
| Pending Triage | Draft exists; awaiting or beginning processing/review |
| Processing | AI workflow running |
| Needs Information | Required intake information incomplete |
| Ready to Commit | Completeness/readiness conditions satisfied; awaiting human commit |
| Committed | Human explicitly committed the record |

Status transitions are product rules for this assessment tool, not claims of regulated workflow validation.

---

## 6. Completeness assumptions (project-level)

For this assessment, a complaint is generally **not** Ready to Commit while critical identification or defect understanding is missing.

**Locked Ready-to-Commit minimum fields:**
- complaint source
- customer name
- product name
- batch / lot number
- complaint category
- complaint description
- completed initial risk assessment

Missing any of these critical fields results in **Needs Information**.

Other fields may legitimately be unavailable and do **not** block Ready to Commit by themselves:
- affected quantity
- manufacturing date
- expiry date
- originating site block
- impacted non-product materials (NPM)

Duplicate detection (when implemented) uses **committed** PostgreSQL complaint history plus small fictional seed data for demonstration. No vector database. Duplicate suggestions do not replace human judgment about whether two complaints are the same event.

---

## 7. API vs FDF assumptions

| Context | Typical complaint cues (illustrative, not exhaustive) |
| --- | --- |
| API | Material identity, grade, impurity/contamination, packaging of bulk, CoA-related customer claims |
| FDF | Dosage form defects, count/quantity, labeling, tablets/capsules appearance, blister/bottle issues |

VeyraQ may use category/description cues to support structuring. It does **not** require the user to select a full manufacturing execution context.

If API vs FDF cannot be determined, do not invent a classification as source fact unless a dedicated optional inferred field is explicitly designed and labeled.

---

## 8. Risk assessment assumptions

- Risk output is **advisory** for QA.
- Suggested severity and next action do not auto-commit or auto-notify.
- Reassessment after patch may occur when patched fields could change risk (per AI workflow), without rewriting unrelated complaint facts.

---

## 9. Document assumptions

- PDFs with selectable text are the primary document path.
- Scanned-image-only PDFs without OCR are expected to fail extraction gracefully.
- No claim is made that document handling meets regulated controlled-document standards.

---

## 10. What this domain doc does **not** claim

- Compliance with specific FDA/EMA/WHO guidance as a certified implementation
- Validated computer system status
- Electronic signature / Part 11 controls
- Completeness of pharmacovigilance (adverse event) reporting workflows
- That customer complaints and adverse events are the same process

If a complaint text appears to describe a patient safety adverse event, the assessment UI may still capture it as a complaint draft; VeyraQ does not implement a separate pharmacovigilance module in this scope.

---

## 11. Example (patch semantics in domain terms)

Source already extracted product and description. User says:

> The batch is BMX240602 and affected quantity is 48 capsules.

Domain-correct outcome:
- `batch_number` becomes user (or user-confirmed) value `BMX240602`
- `affected_quantity` becomes `48 capsules`
- All other domain fields remain as they were
