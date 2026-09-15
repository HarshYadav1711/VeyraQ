import { useEffect, useId, useRef, useState } from 'react'

import { useAppDispatch, useAppSelector } from '../../../app/hooks'
import { COMPLAINT_SECTIONS } from '../complaintDisplay'
import {
  clearRecentlyUpdatedFields,
  resetComplaintDraft,
  setUserField,
} from '../complaintSlice'
import type { ComplaintFieldKey } from '../complaintTypes'
import { ComplaintSection } from './ComplaintSection'
import styles from './ComplaintPanel.module.css'

const HIGHLIGHT_CLEAR_MS = 1250

export function ComplaintPanel() {
  const dispatch = useAppDispatch()
  const fields = useAppSelector((state) => state.complaint.fields)
  const status = useAppSelector((state) => state.complaint.status)
  const recentlyUpdatedFields = useAppSelector(
    (state) => state.complaint.recentlyUpdatedFields,
  )
  const [confirmOpen, setConfirmOpen] = useState(false)
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  const canCommit = status === 'ready_to_commit'

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

  return (
    <section className={styles.panel} aria-labelledby={titleId}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.title} id={titleId}>
            Log Customer Complaint
          </h2>
          <p className={styles.subtitle}>API &amp; FDF Quality Assurance</p>
        </div>
      </header>

      <div className={styles.body}>
        {COMPLAINT_SECTIONS.map((section) => (
          <ComplaintSection
            key={section.id}
            section={section}
            fields={fields}
            recentlyUpdatedFields={recentlyUpdatedFields}
            onFieldChange={handleFieldChange}
          />
        ))}
      </div>

      <footer className={styles.actions}>
        <button
          type="button"
          className={styles.secondaryButton}
          onClick={() => setConfirmOpen(true)}
        >
          Reset Complaint
        </button>

        <div className={styles.commitGroup}>
          <button
            type="button"
            className={styles.primaryButton}
            disabled={!canCommit}
            title={
              canCommit
                ? 'Commit complaint record'
                : 'Complaint must be ready for review before it can be committed.'
            }
          >
            Commit Complaint
          </button>
          {!canCommit ? (
            <p className={styles.commitHint}>
              Complaint must be ready for review before it can be committed.
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
          Reset complaint draft?
        </h3>
        <p className={styles.dialogBody}>
          This clears all complaint fields and returns the draft to Pending
          Triage.
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
            Reset Complaint
          </button>
        </div>
      </dialog>
    </section>
  )
}
