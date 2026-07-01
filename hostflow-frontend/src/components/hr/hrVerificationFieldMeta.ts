import type { HrDocumentFieldReview } from '../../api/workforce'

export type HrFieldInputType = 'text' | 'date' | 'country' | 'dial_code' | 'email' | 'tel'

const DATE_FIELD_CODES = new Set([
  'birth_date',
  'document_issue_date',
  'document_expiry',
  'driver_license_expiry',
  'code95_expiry',
  'tacho_card_expiry',
  'exam_valid_until',
  'passport_issue_date',
  'passport_expiry',
  'passport_valid_to',
  'medical_expiry',
])

const COUNTRY_FIELD_CODES = new Set(['citizenship', 'work_country', 'address_country', 'country_of_residence'])

export function resolveHrFieldInputType(field: HrDocumentFieldReview): HrFieldInputType {
  const explicit = String(field.input_type || '').trim().toLowerCase()
  if (explicit === 'date' || explicit === 'country' || explicit === 'dial_code' || explicit === 'email' || explicit === 'tel') {
    return explicit
  }
  const code = String(field.field_code || '').trim()
  if (COUNTRY_FIELD_CODES.has(code)) return 'country'
  if (
    DATE_FIELD_CODES.has(code) ||
    code.endsWith('_date') ||
    code.endsWith('_expiry') ||
    code.endsWith('_valid_to')
  ) {
    return 'date'
  }
  if (code === 'phone_country_code') return 'dial_code'
  if (code === 'phone') return 'tel'
  return 'text'
}

export function stringifyProfileValue(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number') return String(value)
  if (typeof value === 'object' && !Array.isArray(value)) {
    const o = value as Record<string, unknown>
    const parts = [o.street, o.house, o.apt, o.zip, o.city, o.country]
      .map((part) => String(part || '').trim())
      .filter(Boolean)
    if (parts.length) return parts.join(', ')
  }
  return String(value).trim()
}

export function profileValueForField(
  field: HrDocumentFieldReview,
  reviewed?: Record<string, unknown>,
): string {
  const prev = reviewed?.[field.field_code]
  if (prev && typeof prev === 'object' && prev !== null && 'value' in (prev as object)) {
    const v = stringifyProfileValue((prev as { value?: unknown }).value)
    if (v) return v
  }
  if (field.reviewed_value != null) {
    const reviewedVal = stringifyProfileValue(field.reviewed_value)
    if (reviewedVal) return reviewedVal
  }
  for (const v of Object.values(field.current_profile_values || {})) {
    const text = stringifyProfileValue(v)
    if (text) return text
  }
  return ''
}

export function formatRecruiterValueForField(field: HrDocumentFieldReview): string {
  const parts = Object.values(field.current_profile_values || {})
    .map((v) => stringifyProfileValue(v))
    .filter(Boolean)
  return parts.join(' · ')
}
