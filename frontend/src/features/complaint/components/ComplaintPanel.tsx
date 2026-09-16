import { useEffect, useId, useRef, useState } from 'react'

import { useAppDispatch, useAppSelector } from '../../../app/hooks'
import { COMPLAINT_SECTIONS } from '../complaintDisplay'
import {
  clearRecentlyUpdatedFields,
  commitComplaint,
  resetComplaintDraft,
  setUserField,
} from '../complaintSlice'
import type { ComplaintFieldKey } from '../complaintTypes'
import { ComplaintSection } from './ComplaintSection'
import { RelatedComplaintsPanel } from './RelatedComplaintsPanel'
import { InvestigationAssistancePanel } from './InvestigationAssistancePanel'
import styles from './ComplaintPanel.module.css'

const HIGHLIGHT_CLEAR_MS = 1250

export function ComplaintPanel() {
  const dispatch = useAppDispatch()
  const fields = useAppSelector((state) => state.complaint.fields)
  const status = useAppSelector((state) => state.complaint.status)
  const recentlyUpdatedFields = useAppSelector(
    (state) => state.complaint.recentlyUpdatedFields,
  )
  const commitStatus = useAppSelector((state) => state.complaint.commitStatus)
  const commitError = useAppSelector((state) => state.complaint.commitError)
  const complaintNumber = useAppSelector((state) => state.complaint.complaintNumber)

  const [confirmOpen, setConfirmOpen] = useState(false)
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  const isCommitted = status === 'committed'
  const isSubmitting = commitStatus === 'submitting'
  const isProcessing = status === 'processing'
  const canCommit = status === 'ready_to_commit' && !isSubmitting

  useEffect(() => {
    if (recentlyUpdatedFields.length === 0) {
      return
    }

    const timer = window.setTimeout(() => {
      dispatch(clearRecentlyUpdatedFields())
    }, HIGHLIGHT_CLEAR_MS)

    return () => {
      window.clearTimeout(timer)
    }
  }, [recentlyUpdatedFields, dispatch])

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) {
      return
    }

    if (confirmOpen && !dialog.open) {
      dialog.showModal()
    } else if (!confirmOpen && dialog.open) {
      dialog.close()
    }
  }, [confirmOpen])

  function handleFieldChange(key: ComplaintFieldKey, value: string | null) {
    dispatch(setUserField({ field: key, value }))
  }

  function handleConfirmReset() {
    dispatch(resetComplaintDraft())
    setConfirmOpen(false)
  }

  function handleCommit() {
    if (!canCommit) {
      return
    }
    void dispatch(commitComplaint())
  }

  return (
    <section className={styles.panel} aria-labelledby={titleId}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.title} id={titleId}>
            Log Customer Complaint
          </h2>
          <p className={styles.subtitle}>API &amp; FDF Quality Assurance</p>
          {isCommitted && complaintNumber ? (
            <p className={styles.committedBanner} role="status">
              Committed as <strong>{complaintNumber}</strong>
            </p>
          ) : null}
        </div>
      </header>

      <div className={styles.body}>
        {COMPLAINT_SECTIONS.map((section) => (
          <ComplaintSection
            key={section.id}
            section={section}
            fields={fields}
            recentlyUpdatedFields={recentlyUpdatedFields}
            readOnly={isCommitted || isProcessing}
            onFieldChange={handleFieldChange}
          />
        ))}
        <RelatedComplaintsPanel />
        <InvestigationAssistancePanel />
      </div>

      <footer className={styles.actions}>
        <button
          type="button"
          className={styles.secondaryButton}
          onClick={() => setConfirmOpen(true)}
        >
          {isCommitted ? 'New Complaint' : 'Reset Complaint'}
        </button>

        <div className={styles.commitGroup}>
          <button
            type="button"
            className={styles.primaryButton}
            disabled={!canCommit || isCommitted}
            aria-busy={isSubmitting}
            title={
              isCommitted
                ? 'Complaint already committed'
                : canCommit
                  ? 'Commit complaint record'
                  : 'Complaint must be ready for review before it can be committed.'
            }
            onClick={handleCommit}
          >
            {isSubmitting ? 'Committing…' : 'Commit Complaint'}
          </button>
          {!canCommit && !isCommitted ? (
            <p className={styles.commitHint}>
              Complaint must be ready for review before it can be committed.
            </p>
          ) : null}
          {commitError ? (
            <p className={styles.commitError} role="alert">
              {commitError}
            </p>
          ) : null}
        </div>
      </footer>

      <dialog
        ref={dialogRef}
        className={styles.dialog}
        aria-labelledby="reset-dialog-title"
        onClose={() => setConfirmOpen(false)}
        onCancel={(event) => {
          event.preventDefault()
          setConfirmOpen(false)
        }}
      >
        <h3 className={styles.dialogTitle} id="reset-dialog-title">
          {isCommitted ? 'Start a new complaint?' : 'Reset complaint draft?'}
        </h3>
        <p className={styles.dialogBody}>
          {isCommitted
            ? 'This clears the committed view and starts a new empty draft.'
            : 'This clears all complaint fields and returns the draft to Pending Triage.'}
        </p>
        <div className={styles.dialogActions}>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={() => setConfirmOpen(false)}
          >
            Cancel
          </button>
          <button
            type="button"
            className={styles.dangerButton}
            onClick={handleConfirmReset}
          >
            {isCommitted ? 'New Complaint' : 'Reset Complaint'}
          </button>
        </div>
      </dialog>
    </section>
  )
}
