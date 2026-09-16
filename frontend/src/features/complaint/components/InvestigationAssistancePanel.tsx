import { useAppDispatch, useAppSelector } from '../../../app/hooks'
import { generateInvestigationAssistance } from '../../assistant/assistantSlice'
import {
  CAPA_TYPE_LABELS,
  CAPA_TYPE_ORDER,
  ROOT_CAUSE_CATEGORY_LABELS,
  type CapaSuggestion,
  type CapaSuggestionType,
} from '../../assistant/assistantTypes'
import { complaintFieldLabel } from '../complaintDisplay'
import styles from './InvestigationAssistancePanel.module.css'

function groupCapa(suggestions: CapaSuggestion[]) {
  const groups: { type: CapaSuggestionType; items: CapaSuggestion[] }[] = []
  for (const type of CAPA_TYPE_ORDER) {
    const items = suggestions.filter((item) => item.type === type)
    if (items.length > 0) {
      groups.push({ type, items })
    }
  }
  return groups
}

export function InvestigationAssistancePanel() {
  const dispatch = useAppDispatch()
  const fields = useAppSelector((state) => state.complaint.fields)
  const complaintStatus = useAppSelector((state) => state.complaint.status)
  const investigationStatus = useAppSelector(
    (state) => state.assistant.investigationStatus,
  )
  const investigationError = useAppSelector(
    (state) => state.assistant.investigationError,
  )
  const assistance = useAppSelector(
    (state) => state.assistant.investigationAssistance,
  )

  const hasProduct = Boolean(fields.product_name.value?.trim())
  const hasDescription = Boolean(fields.complaint_description.value?.trim())
  const canGenerate =
    hasProduct &&
    hasDescription &&
    investigationStatus !== 'processing' &&
    complaintStatus !== 'processing'

  function handleGenerate() {
    if (!canGenerate) {
      return
    }
    void dispatch(generateInvestigationAssistance())
  }

  return (
    <section
      className={styles.panel}
      aria-labelledby="investigation-assistance-heading"
    >
      <header className={styles.header}>
        <div>
          <h3 className={styles.title} id="investigation-assistance-heading">
            Investigation Assistance
          </h3>
          <p className={styles.badge}>AI-generated · Verify</p>
        </div>
        <p className={styles.disclaimer}>
          AI-generated investigation support. Root causes and CAPA actions
          require QA review and supporting evidence.
        </p>
      </header>

      {!assistance ? (
        <div className={styles.intro}>
          <p className={styles.introCopy}>
            Generate an AI-assisted complaint summary, root cause hypotheses and
            CAPA suggestions for QA review.
          </p>
          {!hasProduct || !hasDescription ? (
            <p className={styles.hint}>
              Product Name and Complaint Description are required before
              generation.
            </p>
          ) : null}
          <button
            type="button"
            className={styles.generateButton}
            disabled={!canGenerate}
            onClick={handleGenerate}
          >
            {investigationStatus === 'processing'
              ? 'Preparing…'
              : 'Generate Investigation Assistance'}
          </button>
        </div>
      ) : (
        <div className={styles.toolbar}>
          <button
            type="button"
            className={styles.generateButton}
            disabled={!canGenerate}
            onClick={handleGenerate}
          >
            {investigationStatus === 'processing'
              ? 'Preparing…'
              : 'Regenerate'}
          </button>
        </div>
      )}

      {investigationStatus === 'processing' ? (
        <p className={styles.processing} role="status">
          Preparing investigation assistance…
        </p>
      ) : null}

      {investigationError ? (
        <p className={styles.error} role="alert">
          {investigationError}
        </p>
      ) : null}

      {assistance ? (
        <div className={styles.results}>
          <section className={styles.block} aria-labelledby="ai-summary-heading">
            <h4 className={styles.blockTitle} id="ai-summary-heading">
              AI Complaint Summary
            </h4>
            <p className={styles.summary}>{assistance.complaint_summary}</p>
          </section>

          <section
            className={styles.block}
            aria-labelledby="root-cause-heading"
          >
            <h4 className={styles.blockTitle} id="root-cause-heading">
              Root Cause Hypotheses
            </h4>
            {assistance.root_cause_hypotheses.length === 0 ? (
              <p className={styles.emptyNote}>
                No root cause hypotheses were returned for this complaint.
              </p>
            ) : (
              <ul className={styles.hypothesisList}>
                {assistance.root_cause_hypotheses.map((item) => (
                  <li
                    key={`${item.category}-${item.hypothesis}`}
                    className={styles.hypothesisCard}
                  >
                    <p className={styles.category}>
                      {ROOT_CAUSE_CATEGORY_LABELS[item.category]}
                    </p>
                    <p className={styles.hypothesis}>{item.hypothesis}</p>
                    <p className={styles.subLabel}>Why it is being considered</p>
                    <p className={styles.bodyText}>{item.rationale}</p>
                    <p className={styles.subLabel}>
                      Supporting complaint information
                    </p>
                    <ul className={styles.bulletList}>
                      {item.supporting_fields.map((field) => (
                        <li key={field}>{complaintFieldLabel(field)}</li>
                      ))}
                    </ul>
                    {item.evidence_needed.length > 0 ? (
                      <>
                        <p className={styles.subLabel}>
                          Evidence to investigate
                        </p>
                        <ul className={styles.bulletList}>
                          {item.evidence_needed.map((evidence) => (
                            <li key={evidence}>{evidence}</li>
                          ))}
                        </ul>
                      </>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className={styles.block} aria-labelledby="capa-heading">
            <h4 className={styles.blockTitle} id="capa-heading">
              CAPA Suggestions
            </h4>
            {assistance.capa_suggestions.length === 0 ? (
              <p className={styles.emptyNote}>
                No CAPA suggestions were returned for this complaint.
              </p>
            ) : (
              groupCapa(assistance.capa_suggestions).map((group) => (
                <div key={group.type} className={styles.capaGroup}>
                  <p className={styles.capaType}>
                    {CAPA_TYPE_LABELS[group.type]}
                  </p>
                  <ul className={styles.capaList}>
                    {group.items.map((item) => (
                      <li key={`${item.type}-${item.action}`}>
                        <p className={styles.capaAction}>{item.action}</p>
                        <p className={styles.capaRationale}>{item.rationale}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              ))
            )}
          </section>
        </div>
      ) : null}
    </section>
  )
}
