# Demo fixtures — fictional assessment data

All names, products, batches, and narrative details in this folder are **entirely fictional**. They are provided only for local demos and assessment video recording. Do not treat them as real quality events or confidential customer data.

## Files

| File | Purpose |
| --- | --- |
| `complaint-email.txt` | FDF text / email-style intake (NovaCare / Cefixime) |
| `complaint-report.pdf` | API document intake (Northstar / Metformin Hydrochloride API) — selectable embedded text, no OCR required |
| `DEMO_DATA.md` | This guide |

## Text scenario (`complaint-email.txt`)

**Customer:** NovaCare Pharmacy  
**Product:** Cefixime Capsules 200 mg  
**Batch:** CFX260481  
**Issue:** Brown discoloration  

**Purpose:** Demonstrate grounded text extraction, provenance, partial dates (`April 2026` / `March 2028`), advisory risk, and related-history against seeded committed complaints.

**Intended correction (after first extraction):**

```text
Correction: 30 capsules were affected.
```

This updates only quantity (plus refreshed advisory risk when applicable) while keeping batch `CFX260481` so related-history can still surface.

**Alternate patch demo** (if you want a stronger “only corrected fields change” callout):

```text
Correction: the batch is CFX260418 and 30 capsules were affected.
```

Note: changing the batch away from `CFX260481` may weaken or remove the seed-based related match.

## Document scenario (`complaint-report.pdf`)

**Customer:** Northstar Formulations  
**Product:** Metformin Hydrochloride API  
**Grade:** IP/BP  
**Batch:** MFH260712A  
**Quantity:** 25 kg (1 HDPE drum)  
**Issue:** Dark foreign particulate during incoming inspection  

**Purpose:** Demonstrate PDF upload → in-memory text extraction → same LangGraph complaint workflow as text intake. Use **New Complaint** first so the draft is empty.

## Related-history seed alignment

Run after migrations:

```bash
cd backend
python -m app.scripts.seed_demo_complaints
```

Expected related matches for the Cefixime / `CFX260481` text scenario:

| Seed ID | Why it matches |
| --- | --- |
| `CMP-DEMO-0001` | Same product + same batch + discoloration narrative |
| `CMP-DEMO-0002` | Same product + same batch + related discoloration |

Related results are decision-support only — not automatic duplicate disposition.

## Secrets

Do not put `GROQ_API_KEY`, database passwords, or real customer data into this folder.
