import { useMemo, useState } from 'react'

import { useAppSelector } from '../../../app/hooks'
import { isComplaintEmpty } from '../complaintDisplay'
import { AssistantPanel } from './AssistantPanel'
import { ComplaintPanel } from './ComplaintPanel'
import { ComplaintStatusBadge } from './ComplaintStatusBadge'
import styles from './ComplaintWorkspace.module.css'

type MobilePane = 'assistant' | 'complaint'

export function ComplaintWorkspace() {
  const fields = useAppSelector((state) => state.complaint.fields)
  const status = useAppSelector((state) => state.complaint.status)
  const empty = useMemo(() => isComplaintEmpty(fields), [fields])
  const [mobilePane, setMobilePane] = useState<MobilePane>(() =>
    empty ? 'assistant' : 'complaint',
  )

  return (
    <div className={styles.workspace}>
      <header className={styles.topBar}>
        <div className={styles.brandBlock}>
          <p className={styles.brand}>VeyraQ</p>
          <p className={styles.productLine}>Customer Complaint Intake</p>
        </div>
        <ComplaintStatusBadge status={status} />
      </header>

      <div
        className={styles.segmented}
        role="tablist"
        aria-label="Workspace panels"
      >
        <button
          type="button"
          role="tab"
          id="tab-assistant"
          aria-selected={mobilePane === 'assistant'}
          aria-controls="panel-assistant"
          className={
            mobilePane === 'assistant'
              ? `${styles.segment} ${styles.segmentActive}`
              : styles.segment
          }
          onClick={() => setMobilePane('assistant')}
        >
          Assistant
        </button>
        <button
          type="button"
          role="tab"
          id="tab-complaint"
          aria-selected={mobilePane === 'complaint'}
          aria-controls="panel-complaint"
          className={
            mobilePane === 'complaint'
              ? `${styles.segment} ${styles.segmentActive}`
              : styles.segment
          }
          onClick={() => setMobilePane('complaint')}
        >
          Complaint
        </button>
      </div>

      <div className={styles.panes}>
        <div
          id="panel-complaint"
          role="tabpanel"
          aria-labelledby="tab-complaint"
          className={
            mobilePane === 'complaint'
              ? `${styles.complaintPane} ${styles.paneActive}`
              : styles.complaintPane
          }
        >
          <ComplaintPanel />
        </div>
        <div
          id="panel-assistant"
          role="tabpanel"
          aria-labelledby="tab-assistant"
          className={
            mobilePane === 'assistant'
              ? `${styles.assistantPane} ${styles.paneActive}`
              : styles.assistantPane
          }
        >
          <AssistantPanel />
        </div>
      </div>
    </div>
  )
}
