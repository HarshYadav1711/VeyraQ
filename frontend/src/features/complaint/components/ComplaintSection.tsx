import type { ComplaintSectionConfig } from '../complaintDisplay'
import type { ComplaintFieldKey, ComplaintFieldValue } from '../complaintTypes'
import { ComplaintField } from './ComplaintField'
import styles from './ComplaintSection.module.css'

interface ComplaintSectionProps {
  section: ComplaintSectionConfig
  fields: Record<ComplaintFieldKey, ComplaintFieldValue>
  recentlyUpdatedFields: readonly ComplaintFieldKey[]
  readOnly: boolean
  onFieldChange: (key: ComplaintFieldKey, value: string | null) => void
}

export function ComplaintSection({
  section,
  fields,
  recentlyUpdatedFields,
  readOnly,
  onFieldChange,
}: ComplaintSectionProps) {
  return (
    <section className={styles.section} aria-labelledby={`section-${section.id}`}>
      <h3 className={styles.title} id={`section-${section.id}`}>
        {section.title}
      </h3>
      <div className={styles.fields}>
        {section.fields.map((fieldConfig) => (
          <ComplaintField
            key={fieldConfig.key}
            config={fieldConfig}
            field={fields[fieldConfig.key]}
            recentlyUpdated={recentlyUpdatedFields.includes(fieldConfig.key)}
            readOnly={readOnly}
            onChange={(value) => onFieldChange(fieldConfig.key, value)}
          />
        ))}
      </div>
    </section>
  )
}
