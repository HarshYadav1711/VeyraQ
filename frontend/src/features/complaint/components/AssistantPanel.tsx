import { useMemo, useState, type KeyboardEvent } from 'react'

import { useAppDispatch, useAppSelector } from '../../../app/hooks'
import {
  processAssistantMessage,
} from '../../assistant/assistantSlice'
import { ASSISTANT_MESSAGE_MAX_LENGTH } from '../../assistant/assistantTypes'
import styles from './AssistantPanel.module.css'

export function AssistantPanel() {
  const dispatch = useAppDispatch()
  const messages = useAppSelector((state) => state.assistant.messages)
  const requestStatus = useAppSelector((state) => state.assistant.requestStatus)
  const error = useAppSelector((state) => state.assistant.error)
  const complaintStatus = useAppSelector((state) => state.complaint.status)
  const [draft, setDraft] = useState('')

  const processing = requestStatus === 'processing'
  const committed = complaintStatus === 'committed'
  const canSubmit =
    draft.trim().length > 0 && !processing && !committed && draft.length <= ASSISTANT_MESSAGE_MAX_LENGTH

  const lastUserMessage = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      if (messages[index].role === 'user') {
        return messages[index].content
      }
    }
    return null
  }, [messages])

  function handleSubmit() {
    if (!canSubmit) {
      return
    }
    const message = draft.trim()
    setDraft('')
    void dispatch(processAssistantMessage({ message }))
  }

  function handleRetry() {
    if (!lastUserMessage || processing || committed) {
      return
    }
    void dispatch(processAssistantMessage({ message: lastUserMessage, retry: true }))
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault()
      handleSubmit()
    }
  }

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
        {messages.length === 0 ? (
          <>
            <p className={styles.intro}>
              Paste or type a pharmaceutical customer complaint to extract the
              record and prepare it for QA review.
            </p>
            <p className={styles.note}>
              Structured fields in the complaint record remain the authoritative
              draft. Direct edits update provenance as user-entered values.
            </p>
          </>
        ) : (
          <ol className={styles.transcript} aria-label="Assistant conversation">
            {messages.map((message) => (
              <li
                key={message.id}
                className={
                  message.role === 'user'
                    ? styles.userMessage
                    : styles.assistantMessage
                }
              >
                <p className={styles.messageRole}>
                  {message.role === 'user' ? 'You' : 'Assistant'}
                </p>
                <p className={styles.messageContent}>{message.content}</p>
              </li>
            ))}
          </ol>
        )}

        {processing ? (
          <p className={styles.processing} role="status">
            Processing complaint…
          </p>
        ) : null}

        {error ? (
          <div className={styles.errorBlock}>
            <p className={styles.error} role="alert">
              {error}
            </p>
            {lastUserMessage ? (
              <button
                type="button"
                className={styles.retryButton}
                onClick={handleRetry}
                disabled={processing || committed}
              >
                Retry
              </button>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className={styles.composer}>
        <label className={styles.composerLabel} htmlFor="assistant-composer">
          Complaint input
        </label>
        <textarea
          id="assistant-composer"
          className={styles.composerInput}
          rows={4}
          value={draft}
          disabled={processing || committed}
          placeholder="Paste complaint text or describe a correction"
          maxLength={ASSISTANT_MESSAGE_MAX_LENGTH}
          aria-describedby="assistant-composer-hint"
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <p className={styles.composerHint} id="assistant-composer-hint">
          {committed
            ? 'Start a New Complaint to submit another record.'
            : 'Paste a customer complaint or describe a correction. Ctrl+Enter to send.'}
        </p>
        <div className={styles.composerActions}>
          <button type="button" className={styles.uploadButton} disabled>
            Upload document
          </button>
          <button
            type="button"
            className={styles.sendButton}
            disabled={!canSubmit}
            onClick={handleSubmit}
          >
            {processing ? 'Processing…' : 'Send'}
          </button>
        </div>
      </div>
    </aside>
  )
}
