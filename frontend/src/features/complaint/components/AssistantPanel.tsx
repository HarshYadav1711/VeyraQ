import styles from './AssistantPanel.module.css'

export function AssistantPanel() {
  return (
    <aside className={styles.panel} aria-labelledby="assistant-heading">
      <header className={styles.header}>
        <div>
          <h2 className={styles.title} id="assistant-heading">
            VeyraQ Assistant
          </h2>
          <p className={styles.subtitle}>AI-assisted intake</p>
        </div>
      </header>

      <div className={styles.body}>
        <p className={styles.intro}>
          Paste or upload a pharmaceutical customer complaint to extract the
          record and prepare it for QA review.
        </p>
        <p className={styles.note}>
          Structured fields in the complaint record remain the authoritative
          draft. Direct edits update provenance as user-entered values.
        </p>
      </div>

      <div className={styles.composer}>
        <label className={styles.composerLabel} htmlFor="assistant-composer">
          Complaint input
        </label>
        <textarea
          id="assistant-composer"
          className={styles.composerInput}
          rows={4}
          disabled
          placeholder="Paste complaint text or describe a correction"
          aria-disabled="true"
          title="AI intake will be enabled when the processing workflow is connected."
        />
        <p className={styles.composerHint} id="assistant-composer-hint">
          AI intake will be enabled when the processing workflow is connected.
        </p>
        <div className={styles.composerActions}>
          <button type="button" className={styles.uploadButton} disabled>
            Upload document
          </button>
          <button type="button" className={styles.sendButton} disabled>
            Send
          </button>
        </div>
      </div>
    </aside>
  )
}
