# DESIGN — UI / UX Direction

## 1. Product feel

VeyraQ is an **enterprise pharmaceutical quality** tool.

It should feel:
- trustworthy
- precise
- modern
- clean
- professional
- information-dense without feeling crowded

It must **not** feel like:
- a marketing website
- a cyberpunk dashboard
- a glassmorphism showcase
- an oversized analytics dashboard

---

## 2. Layout hierarchy (desktop)

Primary composition: **two cooperating panes**.

```
┌─────────────────────────────────────────────────────────────┐
│  VeyraQ  ·  status / context bar (minimal)                  │
├──────────────────────────────┬──────────────────────────────┤
│                              │                              │
│  LEFT: Complaint record form │  RIGHT: VeyraQ Copilot       │
│  - structured fields         │  - chat / intake             │
│  - provenance cues           │  - corrections               │
│  - AI assessment panel       │  - document upload           │
│  - status + commit           │  - follow-up Q&A             │
│                              │                              │
└──────────────────────────────┴──────────────────────────────┘
```

### Left pane — Complaint record form
- Origin & customer details
- Product & batch identification
- Facility & material impact
- Defect analysis
- AI initial assessment (advisory)
- Record status
- Explicit Commit control (enabled only when Ready to Commit)

### Right pane — VeyraQ Copilot
Accepts:
- complaint text
- corrections
- document uploads
- follow-up questions

The panes share one draft: Copilot writes into form state; form reflects truth for review.

---

## 3. Visual hierarchy

1. **Brand/product identity** present but restrained (tool header, not a marketing hero).
2. **Status** always scannable (Pending Triage / Processing / Needs Information / Ready to Commit / Committed).
3. **Field groups** use clear section headings; avoid card sprawl.
4. **AI assessment** visually secondary to factual complaint fields, but easy to find.
5. **Commit** is deliberate—not visually impulsive or buried.

Default: prefer sectioned form surfaces over decorative cards. Borders and light surfaces create structure.

---

## 4. Design tokens (locked)

| Token | Value | Usage |
| --- | --- | --- |
| Canvas | `#F8FAFC` | App background |
| Surface | `#FFFFFF` | Form/Copilot panels |
| Primary text | `#111827` | Field values, headings |
| Secondary text | `#667085` | Labels, help, timestamps |
| Border | `#E5E7EB` | Dividers, inputs, pane edges |
| Primary | `#4F46E5` | Primary actions, focus accents |
| Primary hover | `#4338CA` | Hover for primary controls |
| AI tint | `#F5F3FF` | Inferred / AI-related backgrounds |
| Success | `#16A34A` | Success / committed positive cues |
| Success tint | `#DCFCE7` | Success backgrounds |
| Warning | `#D97706` | Needs information / caution |
| Warning tint | `#FEF3C7` | Warning backgrounds |
| Critical | `#DC2626` | Errors / critical severity cues |
| Font | Inter | All UI text (Google Inter) |

Shadows: **subtle only** where hierarchy requires (e.g., slight elevation for active pane or modal confirm). No multi-layer glow stacks.

---

## 5. Provenance presentation

| Provenance | Presentation intent |
| --- | --- |
| Source | Neutral/default field styling; optional quiet “From source” cue |
| User | Clear “User” / corrected cue; appears after edit/patch |
| Inferred | AI tint background and explicit “Inferred” labeling |
| Missing | Secondary text showing **Not provided**; empty/null underlying value |

Inferred must never look identical to source.

---

## 6. Interaction states

### Processing
- Status = Processing
- Copilot shows in-progress state
- Form fields should not flicker through unverified partial hallucinations; prefer atomic update on successful response

### Correction highlight
When a conversational correction updates field(s):
- briefly highlight only those fields
- animation communicates change, not decoration
- highlight then settles to user provenance styling

### Needs Information
- Warning token usage on status and missing required cues
- Copilot may prompt what is missing without inventing answers

### Ready to Commit
- Success-tinged status treatment (restrained)
- Commit action enabled

### Committed
- Record locked or clearly marked read-only for the committed snapshot
- Success confirmation, minimal celebration

### Error / AI failure
- Clear inline Copilot error
- Prior form state preserved
- Critical color for hard failures

---

## 7. Copilot UX rules

- Conversation is operational, not playful.
- Support paste of email-like text.
- Upload control for documents adjacent to composer.
- Show concise system messages for extraction success, patch applied, completeness gaps.
- Do not bury the intake action behind multi-step wizards.

---

## 8. Form UX rules

- Labels above or clearly associated with inputs (accessible).
- Group related fields under the five domain sections.
- Show AI assessment in a dedicated advisory subsection.
- **Locked:** Direct field editing is supported in MVP. Manual field edits set provenance = `user` and must not trigger full regeneration of unrelated fields.
- Prefer “Not provided” over blank ambiguity for missing values.

---

## 9. Responsive behavior

Primary target: **desktop dual-pane** (assessment demo environment).

**Implemented (Phase 3):**
- **≥900px:** split layout — complaint ~62% / assistant ~38%; assistant pane can stick while scrolling.
- **&lt;900px:** Assistant | Complaint segmented tabs (local UI state, not Redux).
  - Empty complaint (all field values `null`): Assistant initially selected.
  - Non-empty complaint: Complaint initially selected.
  - Manual tab switching always available.
- Assistant composer is enabled for text complaints and corrections (Phase 5). Upload remains disabled until the document phase.

Do not build a separate marketing landing layout.

---

## 9a. Phase 3 UI implementation notes

- Design tokens live as CSS custom properties on `:root` in `index.css`.
- Field highlight for `recentlyUpdatedFields` uses success tint; UI clears the Redux list after ~1.25s (timer owned by UI, not Redux).
- Provenance labels: Extracted / User edited / AI suggestion · Verify / Not provided (metadata beside fields; never written into input values).
- Date fields are text inputs to preserve partial precision (e.g. “March 2026”).
- Commit is disabled unless status is `ready_to_commit`; Reset uses a small modal confirmation.
- Phase 5: Assistant composer is enabled for text/corrections. Upload stays disabled. Conversation messages live in the `assistant` Redux slice, not in complaint fields. While an Assistant request is in flight, complaint status is `processing` and is restored on failure.
---

## 10. Accessibility decisions

- Semantic HTML: landmarks for header, main, complementary Copilot region.
- Visible focus rings using primary accent, not removal of outlines.
- Color is not the only provenance signal—include text labels for inferred/missing/user.
- Inputs and buttons keyboard operable.
- Status text readable by assistive tech (not icon-only).
- Sufficient contrast using the locked token palette.
- Motion: brief, purposeful; respect reduced-motion preference where practical.

---

## 11. Motion policy

Allowed:
- short field highlight on patch
- subtle processing indicator
- status change transitions that aid comprehension

Disallowed:
- decorative parallax, particle effects, neon pulses, continuous attention-grabbing animations

---

## 12. Content tone

UI copy should be:
- precise
- calm
- operational

Examples:
- “Not provided”
- “Inferred — verify before commit”
- “Only updated fields you corrected”
- “Ready to commit — review required fields”

Avoid hype language (“unleash”, “magic”, “autonomous QA”).

---

## 13. Explicit non-design goals

- No glassmorphism showcase
- No cyberpunk aesthetic
- No oversized KPI dashboard as home
- No card grid marketing sections
- No emoji-heavy UI
