import { getEntityProfileFields, getEntityProfilePresentationPreset, getIntakeFormDetail } from '../api/intakeForms'
import type { EntityProfileFieldOption } from '../api/intakeForms'
import type { TranslateFn } from '../i18n'
import {
  defaultPlatformPresentationCode,
  readLatestSubmission,
  readSubmissionAnswerValues,
  resolveSubmissionEntityProfileCode,
  resolveSubmissionPresentationCode,
  type LeadSubmissionV1,
} from './salesQuestionnaireSubmission'
import type { PresentationFieldWithRules } from './presentationRules'

export type SubmissionAnswerRow = {
  qualifiedCode: string
  label: string
  value: string
  sortOrder: number
}

type PresentationLoadResult = {
  fields: PresentationFieldWithRules[]
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

function fieldTypeOf(field: PresentationFieldWithRules): string {
  return text(field.widget_hint || field.field_type).toLowerCase()
}

function humanizeOptionValue(raw: string): string {
  const trimmed = raw.trim()
  if (!trimmed) return ''
  if (!trimmed.includes('_')) {
    return trimmed.charAt(0).toUpperCase() + trimmed.slice(1)
  }
  return trimmed
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function resolveOptionLabel(
  qualifiedCode: string,
  optionValue: string,
  labelKey: string | undefined,
  t: TranslateFn,
): string {
  const value = text(optionValue)
  if (!value) return ''
  const candidates = [
    labelKey ? `${labelKey}.options.${value}` : '',
    `fields.${qualifiedCode.split('.').slice(-1)[0]}.options.${value}`,
    `fields.${qualifiedCode.replace(/\./g, '_')}.options.${value}`,
  ].filter(Boolean)
  for (const key of candidates) {
    const translated = t(key, { defaultValue: '' }).trim()
    if (translated && translated !== key) return translated
  }
  return humanizeOptionValue(value)
}

function formatBoolean(value: unknown, t: TranslateFn): string {
  if (value === true) return t('common.yes', { defaultValue: 'Yes' })
  if (value === false) return t('common.no', { defaultValue: 'No' })
  const normalized = text(value).toLowerCase()
  if (['true', '1', 'yes', 'y'].includes(normalized)) return t('common.yes', { defaultValue: 'Yes' })
  if (['false', '0', 'no', 'n'].includes(normalized)) return t('common.no', { defaultValue: 'No' })
  return text(value)
}

function formatDateValue(value: unknown, locale: string): string {
  const raw = text(value)
  if (!raw) return ''
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return raw
  return date.toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' })
}

function formatPhoneValue(value: unknown): string {
  return text(value)
}

function formatEmailValue(value: unknown): string {
  return text(value)
}

export function formatSubmissionFieldValue(
  value: unknown,
  field: PresentationFieldWithRules,
  options: { t: TranslateFn; locale: string; labelKey?: string },
): string {
  const type = fieldTypeOf(field)
  if (type.includes('multi_select') && Array.isArray(value)) {
    return value
      .map((item) => resolveOptionLabel(field.qualified_code, text(item), options.labelKey, options.t))
      .filter(Boolean)
      .join(', ')
  }
  if (type.includes('single_select') || type.includes('select')) {
    return resolveOptionLabel(field.qualified_code, text(value), options.labelKey, options.t)
  }
  if (type.includes('boolean') || typeof value === 'boolean') {
    return formatBoolean(value, options.t)
  }
  if (type.includes('date')) {
    return formatDateValue(value, options.locale)
  }
  if (type.includes('phone') || type.includes('tel')) {
    return formatPhoneValue(value)
  }
  if (type.includes('email')) {
    return formatEmailValue(value)
  }
  if (Array.isArray(value)) {
    return value.map((item) => text(item)).filter(Boolean).join(', ')
  }
  return text(value)
}

function runtimeFieldFromDetail(row: Record<string, unknown>): PresentationFieldWithRules | null {
  const qualifiedCode = text(row.qualified_code)
  if (!qualifiedCode) return null
  const embedded = record(row.field)
  return {
    qualified_code: qualifiedCode,
    sort_order: Number(row.sort_order ?? 0),
    intake_level: text(row.intake_level) || 'optional',
    label: text(row.label) || text(embedded.label_key) || qualifiedCode.split('.').slice(-1).join(' '),
    field_type: text(row.field_type || embedded.field_type) || null,
    widget_hint: text(row.widget_hint) || null,
    presentation_rules:
      row.presentation_rules && typeof row.presentation_rules === 'object'
        ? (row.presentation_rules as PresentationFieldWithRules['presentation_rules'])
        : undefined,
  }
}

function runtimeFieldFromPreset(row: Record<string, unknown>): PresentationFieldWithRules | null {
  const qualifiedCode = text(row.qualified_code)
  if (!qualifiedCode) return null
  return {
    qualified_code: qualifiedCode,
    sort_order: Number(row.sort_order ?? 0),
    intake_level: text(row.intake_level) || 'optional',
    label: text(row.label_override) || qualifiedCode.split('.').slice(-1).join(' '),
    field_type: text(row.widget_hint) || null,
    widget_hint: text(row.widget_hint) || null,
    presentation_rules:
      row.presentation_rules && typeof row.presentation_rules === 'object'
        ? (row.presentation_rules as PresentationFieldWithRules['presentation_rules'])
        : undefined,
  }
}

function runtimeFieldFromCatalog(row: EntityProfileFieldOption): PresentationFieldWithRules {
  return {
    qualified_code: row.qualified_code,
    sort_order: row.sort_order,
    intake_level: row.intake_level || 'optional',
    label: row.label,
    field_type: row.field_type || null,
    widget_hint: row.field_type || null,
  }
}

export async function loadSubmissionPresentationFields(
  submission: LeadSubmissionV1 | null,
  entityProfileCode: string,
): Promise<PresentationLoadResult> {
  const formId = text(submission?.form_id)
  if (formId) {
    try {
      const detail = await getIntakeFormDetail(formId)
      const fields = (detail.presentation?.fields || [])
        .map((row) => runtimeFieldFromDetail(row as unknown as Record<string, unknown>))
        .filter((row): row is PresentationFieldWithRules => row != null)
      if (fields.length > 0) return { fields }
    } catch {
      // fall through
    }
  }

  const presentationCodes = [
    resolveSubmissionPresentationCode(submission),
    defaultPlatformPresentationCode(),
  ].filter((code): code is string => Boolean(code))

  for (const presentationCode of presentationCodes) {
    try {
      const preset = await getEntityProfilePresentationPreset(entityProfileCode, presentationCode)
      const fields = (preset.fields || [])
        .map((row) => runtimeFieldFromPreset(row as unknown as Record<string, unknown>))
        .filter((row): row is PresentationFieldWithRules => row != null)
      if (fields.length > 0) return { fields }
    } catch {
      // try next code
    }
  }

  const catalog = await getEntityProfileFields(entityProfileCode)
  return {
    fields: (catalog.fields || []).map(runtimeFieldFromCatalog),
  }
}

function labelKeyForField(field: PresentationFieldWithRules, catalogByCode: Map<string, EntityProfileFieldOption>): string | undefined {
  const catalog = catalogByCode.get(field.qualified_code)
  const raw = text(catalog?.label)
  return raw.startsWith('fields.') ? raw : undefined
}

function fallbackFieldLabel(qualifiedCode: string): string {
  const segment = qualifiedCode.split('.').slice(-1)[0] || qualifiedCode
  return humanizeOptionValue(segment) || segment
}

function formatUnknownSubmissionValue(
  value: unknown,
  options: { t: TranslateFn; locale: string },
): string {
  if (value === true || value === false) return formatBoolean(value, options.t)
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (typeof item === 'boolean') return formatBoolean(item, options.t)
        const raw = text(item)
        return raw.includes('_') ? humanizeOptionValue(raw) : raw
      })
      .filter(Boolean)
      .join(', ')
  }
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  const raw = text(value)
  if (!raw) return ''
  if (/^\d{4}-\d{2}-\d{2}/.test(raw)) {
    const formatted = formatDateValue(value, options.locale)
    if (formatted) return formatted
  }
  return raw
}

function maxPresentationSortOrder(fields: PresentationFieldWithRules[]): number {
  return fields.reduce((max, field) => Math.max(max, field.sort_order), 0)
}

function resolveFieldLabel(field: PresentationFieldWithRules, catalogByCode: Map<string, EntityProfileFieldOption>, t: TranslateFn): string {
  if (field.label && !field.label.startsWith('fields.')) return field.label
  const labelKey = labelKeyForField(field, catalogByCode) || field.label
  if (labelKey?.startsWith('fields.')) {
    const translated = t(labelKey, { defaultValue: '' }).trim()
    if (translated && translated !== labelKey) return translated
  }
  return field.label || field.qualified_code.split('.').slice(-1).join(' ').replace(/_/g, ' ')
}

export function buildSubmissionAnswerRows(input: {
  values: Record<string, unknown>
  presentationFields: PresentationFieldWithRules[]
  catalogFields?: EntityProfileFieldOption[]
  t: TranslateFn
  locale: string
}): SubmissionAnswerRow[] {
  const catalogByCode = new Map((input.catalogFields || []).map((row) => [row.qualified_code, row]))
  const fieldsByCode = new Map(input.presentationFields.map((field) => [field.qualified_code, field]))
  const knownSortMax = maxPresentationSortOrder(input.presentationFields)
  let fallbackIndex = 0

  const rows: SubmissionAnswerRow[] = []
  for (const [qualifiedCode, rawValue] of Object.entries(input.values)) {
    const field = fieldsByCode.get(qualifiedCode)
    if (field) {
      const intakeLevel = text(field.intake_level).toLowerCase()
      if (intakeLevel === 'hidden') continue
      const formatted = formatSubmissionFieldValue(rawValue, field, {
        t: input.t,
        locale: input.locale,
        labelKey: labelKeyForField(field, catalogByCode),
      })
      if (!formatted) continue
      rows.push({
        qualifiedCode,
        label: resolveFieldLabel(field, catalogByCode, input.t),
        value: formatted,
        sortOrder: field.sort_order,
      })
      continue
    }

    const formatted = formatUnknownSubmissionValue(rawValue, {
      t: input.t,
      locale: input.locale,
    })
    if (!formatted) continue
    fallbackIndex += 1
    rows.push({
      qualifiedCode,
      label: fallbackFieldLabel(qualifiedCode),
      value: formatted,
      sortOrder: knownSortMax + fallbackIndex * 10,
    })
  }

  return rows.sort((a, b) => a.sortOrder - b.sortOrder || a.label.localeCompare(b.label))
}

export async function loadSubmissionAnswerRowsForLead(
  lead: { normalized?: Record<string, unknown> | null },
  options: { t: TranslateFn; locale: string },
): Promise<SubmissionAnswerRow[]> {
  const submission = readLatestSubmission(lead)
  const entityProfileCode = resolveSubmissionEntityProfileCode(submission, lead)
  const values = readSubmissionAnswerValues(lead, submission, entityProfileCode)
  if (Object.keys(values).length === 0) return []

  const [{ fields }, catalog] = await Promise.all([
    loadSubmissionPresentationFields(submission, entityProfileCode),
    getEntityProfileFields(entityProfileCode).catch(() => ({ fields: [] as EntityProfileFieldOption[] })),
  ])

  return buildSubmissionAnswerRows({
    values,
    presentationFields: fields,
    catalogFields: catalog.fields,
    t: options.t,
    locale: options.locale,
  })
}
