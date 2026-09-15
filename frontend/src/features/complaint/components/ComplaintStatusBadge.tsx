import { COMPLAINT_STATUS_LABELS } from '../complaintDisplay'
import type { ComplaintStatus } from '../complaintTypes'
import styles from './ComplaintStatusBadge.module.css'

interface ComplaintStatusBadgeProps {
  status: ComplaintStatus
}

export function ComplaintStatusBadge({ status }: ComplaintStatusBadgeProps) {
  return (
    <span
      className={`${styles.badge} ${styles[status]}`}
      role="status"
      aria-label={`Complaint status: ${COMPLAINT_STATUS_LABELS[status]}`}
    >
      {COMPLAINT_STATUS_LABELS[status]}
    </span>
  )
}
