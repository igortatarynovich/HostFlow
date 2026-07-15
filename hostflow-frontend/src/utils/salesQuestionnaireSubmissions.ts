import type { Lead } from '../api/types'
import type { FieldOption } from './serviceSalesFieldOptions'
import { formatFieldDisplayValue } from './serviceSalesFieldOptions'

export type SubmissionRecord = {
  submission_id?: string
  submitted_at?: string
  form_id?: string
  presentation_code?: string
  normalized_values?: Record<string, unknown>
  source?: Record<string, unknown>
}

export type SubmissionAnswerRow = {
  qualifiedCode: string
  label: string
  value: string
  sortOrder: number
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

export function listSubmissions(lead: Lead): SubmissionRecord[] {
  const normalized = record(lead.normalized)
  const raw = normalized.submissions_v1
  if (!Array.isArray(raw)) return []
  return raw.filter((row): row is SubmissionRecord => Boolean(row) && typeof row === 'object')
}

export function latestSubmission(lead: Lead): SubmissionRecord | null {
  const rows = listSubmissions(lead)
  return rows.length > 0 ? rows[rows.length - 1] : null
}

export function submissionSourceLabel(submission: SubmissionRecord): string {
  const source = record(submission.source)
  const entry = text(source.entry)
  if (entry === 'questionnaire_invite') return 'По вашей ссылке'
  if (entry === 'public_form') return 'Публичная форма'
  return entry || 'Анкета'
}

export function readSalesQuestionnaireValues(lead: Lead): Record<string, unknown> {
  const normalized = record(lead.normalized)
  const block = record(normalized.sales_questionnaire)
  if (Object.keys(block).length > 0) return block
  const latest = latestSubmission(lead)
  if (!latest?.normalized_values) return {}
  const out: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(latest.normalized_values)) {
    const suffix = key.split('.').slice(-1)[0]
    if (suffix) out[suffix] = value
  }
  return out
}

const FIELD_LABELS: Record<string, string> = {
  need_type: 'Кого хотите привлечь',
  recruitment_roles: 'Профессии',
  recruitment_other_role: 'Своя профессия',
  recruitment_headcount: 'Количество сотрудников',
  work_location_country: 'Страна работы',
  work_location_region: 'Регион',
  work_location_city: 'Город',
  work_location_base: 'База',
  job_posting_ready: 'Готовое объявление',
  recruitment_materials: 'Фото / видео',
  advertised_services: 'Услуги / товары',
  advertised_services_other: 'Другая услуга',
  client_geo_country: 'Страна клиентов',
  client_geo_region: 'Регион клиентов',
  client_geo_city: 'Город клиентов',
  conversion_destination: 'Действие клиента',
  has_website: 'Сайт',
  marketing_materials: 'Фото / видео',
  contact_full_name: 'Имя',
  contact_company_name: 'Компания',
  contact_phone: 'Телефон',
  contact_email: 'Email',
  additional_notes: 'Комментарий',
}

export function buildAnswerRowsFromSubmission(
  submission: SubmissionRecord,
  fieldOptionsByCode: Record<string, FieldOption[]>,
): SubmissionAnswerRow[] {
  const values = record(submission.normalized_values)
  const rows: SubmissionAnswerRow[] = []
  let order = 0
  for (const [qualifiedCode, rawValue] of Object.entries(values)) {
    if (rawValue == null || rawValue === '' || (Array.isArray(rawValue) && rawValue.length === 0)) continue
    const suffix = qualifiedCode.split('.').slice(-1)[0] || qualifiedCode
    rows.push({
      qualifiedCode,
      label: FIELD_LABELS[suffix] || suffix.replace(/_/g, ' '),
      value: formatFieldDisplayValue(rawValue, fieldOptionsByCode[qualifiedCode]),
      sortOrder: order++,
    })
  }
  return rows.sort((a, b) => a.sortOrder - b.sortOrder)
}

export function buildAnswerRowsFromLead(
  lead: Lead,
  fieldOptionsByCode: Record<string, FieldOption[]>,
): SubmissionAnswerRow[] {
  const latest = latestSubmission(lead)
  if (latest) return buildAnswerRowsFromSubmission(latest, fieldOptionsByCode)
  const block = readSalesQuestionnaireValues(lead)
  const rows: SubmissionAnswerRow[] = []
  let order = 0
  for (const [key, value] of Object.entries(block)) {
    if (value == null || value === '' || (Array.isArray(value) && value.length === 0)) continue
    const qualifiedCode = `service_sales.targeted_advertising.${key}`
    rows.push({
      qualifiedCode,
      label: FIELD_LABELS[key] || key.replace(/_/g, ' '),
      value: formatFieldDisplayValue(value, fieldOptionsByCode[qualifiedCode]),
      sortOrder: order++,
    })
  }
  return rows
}
