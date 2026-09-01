import type { EntityProfileFieldOption, PresentationFieldInput } from '../api/intakeForms'
import type { LocaleCode } from '../i18n'
import type { PresentationRules } from './presentationRules'
import { fieldOptionsForCode } from './intakePresentationFieldOptions'

export type PresentationFieldDraft = {
  qualified_code: string
  label_override: string
  intake_level: 'required' | 'optional' | 'hidden'
  sort_order: number
  selected: boolean
  presentation_rules?: PresentationRules
}

export const FORM_LOCALES = ['pl', 'en', 'ru'] as const
export type FormLocale = (typeof FORM_LOCALES)[number]

export function looksLikeI18nKey(value: string): boolean {
  return /^(fields|admin|public|forms)\./.test(value)
}

export function isFormLocale(value: string | null | undefined): value is FormLocale {
  return value === 'pl' || value === 'en' || value === 'ru'
}

export function slugifyFieldCodeFromLabel(label: string): string {
  return label
    .toLowerCase()
    .trim()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 64)
}

function intakeLevel(value: string | undefined | null): PresentationFieldDraft['intake_level'] {
  if (value === 'required' || value === 'hidden') return value
  return 'optional'
}

export function fieldsToPayload(rows: PresentationFieldDraft[]): PresentationFieldInput[] {
  return rows
    .filter((row) => row.selected)
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((row, index) => {
      const rawLabel = row.label_override.trim()
      const payload: PresentationFieldInput = {
        qualified_code: row.qualified_code,
        label_override: !rawLabel || looksLikeI18nKey(rawLabel) ? undefined : rawLabel,
        intake_level: row.intake_level,
        sort_order: (index + 1) * 10,
      }
      if (row.presentation_rules && Object.keys(row.presentation_rules).length > 0) {
        payload.presentation_rules = row.presentation_rules
      }
      return payload
    })
}

export function mergeCatalogWithPreset(
  catalog: EntityProfileFieldOption[],
  presetFields: PresentationFieldInput[],
  prev: PresentationFieldDraft[] = [],
): PresentationFieldDraft[] {
  const presetByCode = new Map(presetFields.map((field) => [field.qualified_code, field]))
  const prevByCode = new Map(prev.map((row) => [row.qualified_code, row]))
  const catalogByCode = new Map(catalog.map((field) => [field.qualified_code, field]))
  const codes: string[] = []
  const seen = new Set<string>()
  for (const field of catalog) {
    if (!seen.has(field.qualified_code)) {
      codes.push(field.qualified_code)
      seen.add(field.qualified_code)
    }
  }
  for (const field of presetFields) {
    if (!seen.has(field.qualified_code)) {
      codes.push(field.qualified_code)
      seen.add(field.qualified_code)
    }
  }

  return codes.map((code, index) => {
    const catalogField = catalogByCode.get(code)
    const presetField = presetByCode.get(code)
    const existing = prevByCode.get(code)
    if (presetField) {
      const rawLabel = String(presetField.label_override || '').trim()
      return {
        qualified_code: code,
        label_override: rawLabel && !looksLikeI18nKey(rawLabel) ? rawLabel : '',
        intake_level: intakeLevel(presetField.intake_level),
        sort_order: presetField.sort_order ?? (index + 1) * 10,
        selected: true,
        presentation_rules: presetField.presentation_rules,
      }
    }
    if (existing) return { ...existing, selected: false }
    return {
      qualified_code: code,
      label_override: '',
      intake_level: intakeLevel(catalogField?.intake_level),
      sort_order: catalogField?.sort_order || (index + 1) * 10,
      selected: false,
    }
  })
}

type TFn = (key: string, options?: { defaultValue?: string }) => string

export function fieldTypeLabel(fieldType: string | null | undefined, t: TFn): string {
  const type = String(fieldType || 'text').trim().toLowerCase()
  const keyMap: Record<string, { key: string; fallback: string }> = {
    text: { key: 'admin.intake_forms.field_types.text', fallback: 'Text' },
    textarea: { key: 'admin.intake_forms.field_types.textarea', fallback: 'Long text' },
    integer: { key: 'admin.intake_forms.field_types.integer', fallback: 'Number' },
    number: { key: 'admin.intake_forms.field_types.integer', fallback: 'Number' },
    single_select: { key: 'admin.intake_forms.field_types.single_select', fallback: 'Single choice' },
    multi_select: { key: 'admin.intake_forms.field_types.multi_select', fallback: 'Multiple choice' },
    phone_e164: { key: 'admin.intake_forms.field_types.phone', fallback: 'Phone' },
    phone: { key: 'admin.intake_forms.field_types.phone', fallback: 'Phone' },
    email: { key: 'admin.intake_forms.field_types.email', fallback: 'Email' },
  }
  const mapped = keyMap[type] || keyMap.text
  return t(mapped.key, { defaultValue: mapped.fallback })
}

export function fieldAnswersHint(
  field: Pick<EntityProfileFieldOption, 'qualified_code' | 'field_type'>,
  t: TFn,
  locale: LocaleCode,
): string {
  const options = fieldOptionsForCode(field.qualified_code, t, locale)
  if (options.length > 0) {
    const labels = options.map((row) => row.label)
    if (labels.length <= 4) return labels.join(', ')
    return `${labels.slice(0, 3).join(', ')} +${labels.length - 3}`
  }
  const type = String(field.field_type || 'text').trim().toLowerCase()
  if (type === 'integer' || type === 'number') {
    return t('admin.intake_forms.answers.number', { defaultValue: 'Number' })
  }
  if (type === 'phone_e164' || type === 'phone') {
    return t('admin.intake_forms.answers.phone', { defaultValue: 'Phone number' })
  }
  if (type === 'email') {
    return t('admin.intake_forms.answers.email', { defaultValue: 'Email address' })
  }
  return t('admin.intake_forms.answers.free_text', { defaultValue: 'Free text' })
}

export function publicIntakeUrlForSlug(
  slug: string,
  opts?: { applicationKind?: 'client' | 'candidate'; lang?: FormLocale },
): string {
  const q = new URLSearchParams({ lead_form_slug: slug })
  if (opts?.applicationKind) q.set('application_kind', opts.applicationKind)
  if (opts?.lang) q.set('lang', opts.lang)
  if (typeof window === 'undefined') return `/public/intake?${q.toString()}`
  return `${window.location.origin}/public/intake?${q.toString()}`
}

export function isCompanyInquiryProfile(profileCode: string | null | undefined): boolean {
  return String(profileCode || '').startsWith('service_sales.')
}
