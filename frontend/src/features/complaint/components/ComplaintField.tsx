import type { ChangeEvent } from 'react'

import { PROVENANCE_LABELS } from '../complaintDisplay'
import type { ComplaintFieldDisplayConfig } from '../complaintDisplay'
import type { ComplaintFieldValue } from '../complaintTypes'
import styles from './ComplaintField.module.css'

interface ComplaintFieldProps {
  config: ComplaintFieldDisplayConfig
  field: ComplaintFieldValue
  recentlyUpdated: boolean
  readOnly: boolean
  onChange: (value: string | null) => void
}

export function ComplaintField({
  config,
  field,
  recentlyUpdated,
  readOnly,
  onChange,
}: ComplaintFieldProps) {
  const inputId = `complaint-field-${config.key}`
  const metaId = `${inputId}-meta`
  const displayValue = field.value ?? ''
  const isInferred = field.provenance === 'inferred'

  const rootClassName = [
    styles.field,
    recentlyUpdated ? styles.recentlyUpdated : '',
    isInferred ? styles.inferred : '',
  ]
    .filter(Boolean)
    .join(' ')

  function handleChange(event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    const next = event.target.value
    onChange(next === '' ? null : next)
  }

  return (
    <div className={rootClassName} data-field-key={config.key}>
      <div className={styles.labelRow}>
        <label className={styles.label} htmlFor={inputId}>
          {config.label}
        </label>
        <span className={styles.provenance} id={metaId}>
          {PROVENANCE_LABELS[field.provenance]}
        </span>
      </div>

      {config.control === 'textarea' ? (
        <textarea
          id={inputId}
          className={styles.control}
          value={displayValue}
          placeholder={config.placeholder}
          rows={4}
          aria-describedby={metaId}
          readOnly={readOnly}
          disabled={readOnly}
          onChange={handleChange}
        />
      ) : (
        <input
          id={inputId}
          className={styles.control}
          type="text"
          value={displayValue}
          placeholder={config.placeholder}
          aria-describedby={metaId}
          readOnly={readOnly}
          disabled={readOnly}
          onChange={handleChange}
        />
      )}
    </div>
  )
}
