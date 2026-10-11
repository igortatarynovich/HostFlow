import type { Document } from '../../../api/types'
import { DocumentFieldInput } from './DocumentFieldInput'
import { getDocumentFieldsConfig } from '../documentFieldsConfig'
import type { MetadataState } from '../types'

type Props = {
  doc: Document
  metadataValues: MetadataState
  disabled?: boolean
  omitKeys?: string[]
  onlyKeys?: string[]
  getFieldValue: (doc: Document, fieldKey: string, metadataValues: MetadataState) => unknown
  onChange: (doc: Document, fieldKey: string, value: unknown) => void
}

export function DocumentMetadataForm({
  doc,
  metadataValues,
  disabled,
  omitKeys,
  onlyKeys,
  getFieldValue,
  onChange,
}: Props) {
  const code = doc.type_code || doc.doc_type || ''
  const omit = new Set(omitKeys || [])
  const only = onlyKeys ? new Set(onlyKeys) : null
  const fields = getDocumentFieldsConfig(code).filter((field) => {
    if (omit.has(field.key)) return false
    if (only && !only.has(field.key)) return false
    return true
  })
  if (!fields.length) return null
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {fields.map((field) => (
        <DocumentFieldInput
          key={field.key}
          fieldConfig={field}
          value={getFieldValue(doc, field.key, metadataValues)}
          onChange={(value) => onChange(doc, field.key, value)}
          disabled={Boolean(disabled)}
        />
      ))}
    </div>
  )
}
