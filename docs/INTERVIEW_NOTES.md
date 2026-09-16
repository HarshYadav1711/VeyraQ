# Interview notes — VeyraQ

Developer-facing notes for assessment interviews. Answers describe **what exists**, not speculative features.

## Architecture decisions

| Decision | Why |
| --- | --- |
| React + Redux Toolkit | Assessment requires React + Redux; RTK keeps draft/patch/status predictable and testable |
| One LangGraph StateGraph | Clear node walkthrough; avoids multi-agent sprawl for intake |
| Groq only, env-configured model | Mandatory provider; model IDs change — keep configurable |
| Grounding after extraction | LLM proposes `value`+`evidence`; backend decides `source` or drops |
| Client Redux drafts until commit | Matches “AI never auto-commits”; PostgreSQL stores committed records |
| Deterministic related matching | Explainable reasons; no embeddings/vector DB for assessment scale |
| Investigation as separate service | On-demand, non-mutating; keeps intake graph cheaper and focused |
| PyMuPDF in-memory only | Document intake without OCR theater or document persistence |

## Trade-offs

- **Small history scan (≤100)** vs full search index — fine for demo seed size; would need indexing at production volume.
- **No auth** — acceptable for assessment demo; unacceptable for regulated deployment.
- **No OCR** — scanned PDFs fail clearly; avoids false confidence.
- **Investigation not persisted** — advisory workspace aid; CAPA lifecycle is out of scope.
- **Strict structured Groq outputs** — reliability over free-form prose; model must support JSON schema mode.

## Likely questions (concise answers)

**Why Redux?**  
Shared complaint draft is cross-pane state (form + Assistant). Explicit patch merges and provenance belong in a single store with testable reducers — Redux Toolkit fits the mandatory Redux requirement without inventing a second pattern.

**Why LangGraph here?**  
Intake is a stateful pipeline (intent → extract/correct → ground → risk → related → completeness). LangGraph makes those nodes visible for walkthroughs and testing with a fake AI service.

**Why not an LLM for duplicate detection?**  
Duplicates must be explainable and stable. Deterministic scoring (exact batch, normalized product/category, gated description similarity) produces readable reasons and cannot invent a “match.”

**Why no vector database?**  
Out of scope and unnecessary for a small committed history. Provenance + grounding control hallucinations better than retrieval theater for this module.

**How do you prevent hallucinated complaint fields?**  
Extraction returns evidence spans; ungrounded values are dropped. Missing stays null. Risk/investigation cannot backfill core facts. Failed AI calls do not apply patches.

**How does correction preserve existing data?**  
Correction returns a partial `ComplaintPatch`. Redux/`merge_patch` update only keys present in `changes`. Unrelated fields keep value, provenance, and evidence.

**How would you support scanned PDFs?**  
Add an explicit OCR stage before the existing graph, with clear confidence/failure UX — not silent invention. Keep OCR out of provenance=`source` unless text is verified.

**How would you scale duplicate search?**  
Index committed product/batch/category; keep exact batch equality; optionally add approximate search later with human confirmation. Retain explainable reasons.

**How would you introduce authentication/RBAC?**  
Identity at the API boundary; bind commit/read to roles (intake vs QA approver). Do not mix auth into LangGraph nodes.

**How would you handle audit trails / e-signatures?**  
Append-only event log for field changes and commit; separate signature ceremony for regulated release — not present in this assessment build.

**Why isn’t RCA persisted?**  
Investigation Assistance is advisory and context-sensitive. Persisting it as findings would imply disposition. A production CAPA module would be a separate workflow.

**What happens if Groq is unavailable?**  
API returns a safe 503; frontend restores prior status; draft fields unchanged.

**How would you switch models/providers?**  
Keep `AIService` protocol; change `GROQ_MODEL` or swap the Groq adapter. Do not scatter model IDs through nodes. Provider change beyond Groq would be an assessment-constraint discussion.

## Known limitations

- Assessment prototype — not a validated QMS
- No authentication / RBAC / Part 11 e-signatures
- No production OCR
- Related search sized for small demo history
- AI outputs require human QA review
- No formal CAPA lifecycle persistence
- No external SOP retrieval
- Live Groq/PostgreSQL must be configured locally for full demos

## What would change for production

1. AuthN/AuthZ and audit logging  
2. Organization-controlled complaint numbering  
3. Stronger document handling (OCR policy, malware scanning)  
4. Indexed related-history search  
5. Persistence model for investigations/CAPA if required by process  
6. Observability without logging complaint PHI/content  
7. Validated change control around prompts and models  
