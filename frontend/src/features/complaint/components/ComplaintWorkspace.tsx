import { useMemo, useState, useSyncExternalStore } from 'react'

import { useAppSelector } from '../../../app/hooks'
import { isComplaintEmpty } from '../complaintDisplay'
import { AssistantPanel } from './AssistantPanel'
import { ComplaintPanel } from './ComplaintPanel'
import { ComplaintStatusBadge } from './ComplaintStatusBadge'
import styles from './ComplaintWorkspace.module.css'

type MobilePane = 'assistant' | 'complaint'

const NARROW_QUERY = '(max-width: 899px)'

function subscribeNarrow(onChange: () => void) {
  const media = window.matchMedia(NARROW_QUERY)
  media.addEventListener('change', onChange)
  return () => media.removeEventListener('change', onChange)
}

function getNarrowSnapshot() {
  return window.matchMedia(NARROW_QUERY).matches
}

function getNarrowServerSnapshot() {
  return false
}

export function ComplaintWorkspace() {
  const fields = useAppSelector((state) => state.complaint.fields)
  const status = useAppSelector((state) => state.complaint.status)
  const empty = useMemo(() => isComplaintEmpty(fields), [fields])
  const [mobilePane, setMobilePane] = useState<MobilePane>(() =>
    empty ? 'assistant' : 'complaint',
  )
  const isNarrow = useSyncExternalStore(
    subscribeNarrow,
    getNarrowSnapshot,
    getNarrowServerSnapshot,
  )

  function handleSuccessfulDocumentExtraction() {
    setMobilePane('complaint')
  }

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
          aria-hidden={isNarrow ? mobilePane !== 'complaint' : undefined}
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
          aria-hidden={isNarrow ? mobilePane !== 'assistant' : undefined}
          className={
            mobilePane === 'assistant'
              ? `${styles.assistantPane} ${styles.paneActive}`
              : styles.assistantPane
          }
        >
          <AssistantPanel
            onSuccessfulDocumentExtraction={handleSuccessfulDocumentExtraction}
          />
        </div>
      </div>
    </div>
  )
}
