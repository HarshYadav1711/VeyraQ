import { useAppSelector } from '../../../app/hooks'
import {
  formatMatchStrength,
  formatSimilarityPercent,
} from '../../assistant/assistantTypes'
import styles from './RelatedComplaintsPanel.module.css'

export function RelatedComplaintsPanel() {
  const relatedComplaints = useAppSelector(
    (state) => state.assistant.relatedComplaints,
  )
  const relatedLookupEvaluated = useAppSelector(
    (state) => state.assistant.relatedLookupEvaluated,
  )

  if (!relatedLookupEvaluated) {
    return null
  }

  if (relatedComplaints.length === 0) {
    return (
      <section
        className={styles.panel}
        aria-labelledby="related-complaints-heading"
      >
        <header className={styles.header}>
          <h3 className={styles.title} id="related-complaints-heading">
            Potential Related Complaints
          </h3>
          <p className={styles.subtitle}>
            Historical committed complaints with overlapping product, batch or
            defect signals.
          </p>
        </header>
        <p className={styles.empty}>
          No closely related committed complaints found.
        </p>
      </section>
    )
  }

  return (
    <section
      className={styles.panel}
      aria-labelledby="related-complaints-heading"
    >
      <header className={styles.header}>
        <h3 className={styles.title} id="related-complaints-heading">
          Potential Related Complaints
        </h3>
        <p className={styles.subtitle}>
          Historical committed complaints with overlapping product, batch or
          defect signals. This is a recurrence signal — not a proven duplicate.
        </p>
      </header>

      <ul className={styles.list}>
        {relatedComplaints.map((match) => (
          <li key={match.complaint_id} className={styles.card}>
            <div className={styles.cardTop}>
              <p className={styles.complaintNumber}>{match.complaint_number}</p>
              <p className={styles.strength}>
                {formatMatchStrength(match.match_strength)}
                <span className={styles.score}>
                  {' '}
                  · {formatSimilarityPercent(match.score)} similarity
                </span>
              </p>
            </div>
            <p className={styles.product}>{match.product_name}</p>
            <p className={styles.meta}>Batch {match.batch_lot_number}</p>
            <p className={styles.category}>{match.complaint_category}</p>
            <div className={styles.reasonsBlock}>
              <p className={styles.reasonsLabel}>Why this matched</p>
              <ul className={styles.reasons}>
                {match.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </div>
            {match.complaint_description ? (
              <p className={styles.description}>{match.complaint_description}</p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  )
}
