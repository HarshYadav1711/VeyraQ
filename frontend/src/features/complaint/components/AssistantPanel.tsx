import {
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type KeyboardEvent,
} from 'react'

import { useAppDispatch, useAppSelector } from '../../../app/hooks'
import {
  clearAssistantError,
  processAssistantDocument,
  processAssistantMessage,
} from '../../assistant/assistantSlice'
import { ASSISTANT_MESSAGE_MAX_LENGTH } from '../../assistant/assistantTypes'
import {
  formatFileSize,
  validateSelectedDocument,
} from '../../assistant/documentLimits'
import styles from './AssistantPanel.module.css'

interface AssistantPanelProps {
  onSuccessfulDocumentExtraction?: () => void
}

export function AssistantPanel({
  onSuccessfulDocumentExtraction,
}: AssistantPanelProps) {
  const dispatch = useAppDispatch()
  const messages = useAppSelector((state) => state.assistant.messages)
  const requestStatus = useAppSelector((state) => state.assistant.requestStatus)
  const error = useAppSelector((state) => state.assistant.error)
  const complaintStatus = useAppSelector((state) => state.complaint.status)
  const [draft, setDraft] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [documentRequestActive, setDocumentRequestActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const processing = requestStatus === 'processing'
  const committed = complaintStatus === 'committed'
  const canSubmit =
    draft.trim().length > 0 &&
    !processing &&
    !committed &&
    draft.length <= ASSISTANT_MESSAGE_MAX_LENGTH
  const canAnalyzeDocument =
    selectedFile !== null && !processing && !committed && !fileError

  const lastUserMessage = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      if (messages[index].role === 'user') {
        return messages[index].content
      }
    }
    return null
  }, [messages])

  const showTextRetry =
    Boolean(error) &&
    Boolean(lastUserMessage) &&
    !lastUserMessage?.startsWith('Uploaded complaint document:')

  function acceptFile(file: File | null) {
    if (!file) {
      return
    }
    const validationError = validateSelectedDocument(file)
    if (validationError) {
      setSelectedFile(null)
      setFileError(validationError)
      return
    }
    setSelectedFile(file)
    setFileError(null)
    dispatch(clearAssistantError())
  }

  function clearSelectedFile() {
    setSelectedFile(null)
    setFileError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  function handleSubmit() {
    if (!canSubmit) {
      return
    }
    const message = draft.trim()
    setDraft('')
    setDocumentRequestActive(false)
    void dispatch(processAssistantMessage({ message }))
  }

  function handleRetry() {
    if (!lastUserMessage || processing || committed) {
      return
    }
    setDocumentRequestActive(false)
    void dispatch(
      processAssistantMessage({ message: lastUserMessage, retry: true }),
    )
  }

  async function handleAnalyzeDocument() {
    if (!selectedFile || !canAnalyzeDocument) {
      return
    }
    const file = selectedFile
    setDocumentRequestActive(true)
    const result = await dispatch(
      processAssistantDocument({
        file,
        displayName: file.name,
      }),
    )
    if (processAssistantDocument.fulfilled.match(result)) {
      clearSelectedFile()
      onSuccessfulDocumentExtraction?.()
    }
    setDocumentRequestActive(false)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault()
      handleSubmit()
    }
  }

  function handleFileInputChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null
    acceptFile(file)
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    event.stopPropagation()
    if (!processing && !committed) {
      setDragActive(true)
    }
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    event.stopPropagation()
    setDragActive(false)
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    event.stopPropagation()
    setDragActive(false)
    if (processing || committed) {
      return
    }
    const file = event.dataTransfer.files?.[0] ?? null
    acceptFile(file)
  }

  const processingLabel = documentRequestActive
    ? 'Analyzing complaint document…'
    : 'Processing complaint…'

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
              Paste or type a pharmaceutical customer complaint, or upload a
              PDF, TXT, or EML document to extract the record for QA review.
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
            {processingLabel}
          </p>
        ) : null}

        {error ? (
          <div className={styles.errorBlock}>
            <p className={styles.error} role="alert">
              {error}
            </p>
            {showTextRetry ? (
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
        <div className={styles.uploadSection}>
          <p className={styles.uploadHeading}>Upload complaint document</p>
          <div
            className={
              dragActive
                ? `${styles.dropZone} ${styles.dropZoneActive}`
                : styles.dropZone
            }
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <p className={styles.dropPrompt}>Drop a PDF, TXT or EML here</p>
            <p className={styles.dropOr}>or</p>
            <button
              type="button"
              className={styles.chooseFileButton}
              disabled={processing || committed}
              onClick={() => fileInputRef.current?.click()}
            >
              Choose file
            </button>
            <label className={styles.visuallyHidden} htmlFor="assistant-document-input">
              Choose complaint document file
            </label>
            <input
              ref={fileInputRef}
              id="assistant-document-input"
              className={styles.fileInput}
              type="file"
              accept=".pdf,.txt,.eml,application/pdf,text/plain,message/rfc822"
              disabled={processing || committed}
              onChange={handleFileInputChange}
            />
            <p className={styles.uploadMeta}>
              Supported: PDF · TXT · EML
              <br />
              Up to 8 MB
            </p>
          </div>

          {selectedFile ? (
            <div className={styles.selectedFile}>
              <div className={styles.selectedFileInfo}>
                <p className={styles.selectedFileName}>{selectedFile.name}</p>
                <p className={styles.selectedFileSize}>
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
              <button
                type="button"
                className={styles.removeFileButton}
                disabled={processing}
                onClick={clearSelectedFile}
              >
                Remove
              </button>
            </div>
          ) : null}

          {fileError ? (
            <p className={styles.fileError} role="alert">
              {fileError}
            </p>
          ) : null}

          <button
            type="button"
            className={styles.analyzeButton}
            disabled={!canAnalyzeDocument}
            onClick={() => {
              void handleAnalyzeDocument()
            }}
          >
            {documentRequestActive && processing
              ? 'Analyzing…'
              : 'Analyze Document'}
          </button>
        </div>

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
          <button
            type="button"
            className={styles.sendButton}
            disabled={!canSubmit}
            onClick={handleSubmit}
          >
            {processing && !documentRequestActive ? 'Processing…' : 'Send'}
          </button>
        </div>
      </div>
    </aside>
  )
}
