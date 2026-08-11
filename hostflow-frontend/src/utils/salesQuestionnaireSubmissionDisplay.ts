import {
  getEntityProfileFields,
  getEntityProfilePresentationPreset,
  getIntakeFormDetail,
  resolveEntityProfilePresentation,
} from '../api/intakeForms'
import type { EntityProfileFieldOption } from '../api/intakeForms'
import { lookupScopedTranslation, type LocaleCode, type TranslateFn } from '../i18n'
import { fieldOptionsForCode } from './intakePresentationFieldOptions'
import { intakePresentationFieldLabel } from './intakePresentationI18n'
import {
  evaluatePresentationFields,
  type PresentationFieldWithRules,
} from './presentationRules'
import {
  defaultPlatformPresentationCode,
  readLatestSubmission,
  readLeadSubmissions,
  readSubmissionAnswerValues,
  resolveSubmissionEntityProfileCode,
  resolveSubmissionPresentationCode,
  type LeadSubmissionV1,
} from './salesQuestionnaireSubmission'

function asLocaleCode(value: string | null | undefined): LocaleCode {
  const code = String(value || '').trim().slice(0, 2).toLowerCase()
  if (code === 'en' || code === 'ru' || code === 'pl') return code
  return 'pl'
}

export type AnswerValueKind = 'text' | 'chips' | 'phone' | 'email' | 'long_text'

export type SubmissionAnswerRow = {
  qualifiedCode: string
  label: string
  /** Plain display string (also used for chips join / a11y). */
  value: string
  sortOrder: number
  kind: AnswerValueKind
  chips?: string[]
  href?: string | null
  changed?: boolean
  sectionKey: string
}

export type SubmissionAnswerSection = {
  key: string
  title: string
  rows: SubmissionAnswerRow[]
}

export type GroupedSubmissionAnswers = {
  sections: SubmissionAnswerSection[]
  submittedAt: string | null
  formLocale: string | null
  isResubmission: boolean
  history: LeadSubmissionV1[]
  selectedSubmission: LeadSubmissionV1 | null
}

/** Business sections for sales questionnaire answers (leaf field → section). */
const SECTION_BY_SUFFIX: Record<string, string> = {
  contact_company_name: 'company',
  industry: 'company',
  contact_website: 'company',

  need_type: 'promote',
  promotion_subject: 'promote',
  recruitment_roles: 'promote',
  recruitment_other_role: 'promote',
  recruitment_headcount: 'promote',
  work_location_country: 'promote',
  work_location_city: 'promote',
  client_geo_scope: 'promote',
  client_geo_detail: 'promote',
  target_audience_description: 'promote',

  primary_outcome: 'goal',
  conversion_destination: 'goal',
  application_channel: 'goal',
  start_timeline: 'goal',
  offer_ready: 'goal',
  job_posting_ready: 'goal',
  monthly_ad_budget: 'goal',
  prior_ads_experience: 'goal',
  decision_maker: 'goal',
  qualified_lead_definition: 'goal',

  marketing_materials: 'materials',
  recruitment_materials: 'materials',

  contact_full_name: 'contact',
  contact_phone: 'contact',
  contact_email: 'contact',

  additional_notes: 'notes',
}

/** English fallbacks when scoped submission-locale keys are missing. */
const SECTION_TITLE_DEFAULTS_EN: Record<string, string> = {
  company: 'Company',
  promote: 'What to promote',
  goal: 'Goal and campaign setup',
  materials: 'Materials',
  contact: 'Contact',
  notes: 'Additional information',
  other: 'Other',
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

function leafSuffix(qualifiedCode: string): string {
  const parts = qualifiedCode.split('.')
  return parts[parts.length - 1] || qualifiedCode
}

export function sectionKeyForField(qualifiedCode: string): string {
  return SECTION_BY_SUFFIX[leafSuffix(qualifiedCode)] || 'other'
}

export function sectionTitleForKey(key: string, locale: string, _t?: TranslateFn): string {
  const code = asLocaleCode(locale)
  const fallback = SECTION_TITLE_DEFAULTS_EN[key] || SECTION_TITLE_DEFAULTS_EN.other
  // Use submission locale dictionary, not CRM UI language.
  return lookupScopedTranslation(code, 'app.sales_questionnaire.section', key) || fallback
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

function formatBoolean(value: unknown, t: TranslateFn, locale: LocaleCode): string {
  const yes =
    lookupScopedTranslation(locale, 'common', 'yes') || t('common.yes', { defaultValue: 'Yes' })
  const no =
    lookupScopedTranslation(locale, 'common', 'no') || t('common.no', { defaultValue: 'No' })
  if (value === true) return yes
  if (value === false) return no
  const normalized = text(value).toLowerCase()
  if (['true', '1', 'yes', 'y'].includes(normalized)) return yes
  if (['false', '0', 'no', 'n', 'none'].includes(normalized)) return no
  return text(value)
}

function catalogOptionsForField(
  qualifiedCode: string,
  t: TranslateFn,
  locale: LocaleCode,
): ReturnType<typeof fieldOptionsForCode> {
  return fieldOptionsForCode(qualifiedCode, t, locale)
}

function resolveCatalogOptionLabel(
  qualifiedCode: string,
  optionValue: string,
  t: TranslateFn,
  locale: LocaleCode,
): string {
  const value = text(optionValue)
  if (!value) return ''
  const options = catalogOptionsForField(qualifiedCode, t, locale)
  const match = options.find((option) => option.value === value)
  if (match?.label) return match.label
  return humanizeOptionValue(value)
}

function hasCatalogOption(qualifiedCode: string, optionValue: string, t: TranslateFn, locale: LocaleCode): boolean {
  const value = text(optionValue)
  if (!value) return false
  return catalogOptionsForField(qualifiedCode, t, locale).some((option) => option.value === value)
}

function detectKind(field: PresentationFieldWithRules | null, value: unknown): AnswerValueKind {
  const type = field ? fieldTypeOf(field) : ''
  const suffix = field ? leafSuffix(field.qualified_code) : ''
  if (type.includes('multi_select') || Array.isArray(value)) return 'chips'
  if (type.includes('phone') || type.includes('tel') || suffix.includes('phone')) return 'phone'
  if (type.includes('email') || suffix.includes('email')) return 'email'
  if (type.includes('textarea') || suffix.includes('notes') || suffix.includes('description')) return 'long_text'
  return 'text'
}

export function formatSubmissionFieldValue(
  value: unknown,
  field: PresentationFieldWithRules,
  options: { t: TranslateFn; locale: LocaleCode },
): string {
  const type = fieldTypeOf(field)
  if (type.includes('multi_select') && Array.isArray(value)) {
    return value
      .map((item) => resolveCatalogOptionLabel(field.qualified_code, text(item), options.t, options.locale))
      .filter(Boolean)
      .join(', ')
  }
  if (type.includes('single_select') || type.includes('select') || type.includes('yes_no')) {
    const raw = text(value)
    if (!raw) return ''
    if (type.includes('yes_no') || typeof value === 'boolean') {
      return formatBoolean(value, options.t, options.locale)
    }
    return resolveCatalogOptionLabel(field.qualified_code, raw, options.t, options.locale)
  }
  if (type.includes('boolean') || typeof value === 'boolean') {
    return formatBoolean(value, options.t, options.locale)
  }
  if (Array.isArray(value)) {
    return value
      .map((item) => resolveCatalogOptionLabel(field.qualified_code, text(item), options.t, options.locale))
      .filter(Boolean)
      .join(', ')
  }
  const raw = text(value)
  // Thin presentation metadata: still map known option codes to human labels.
  if (raw && hasCatalogOption(field.qualified_code, raw, options.t, options.locale)) {
    return resolveCatalogOptionLabel(field.qualified_code, raw, options.t, options.locale)
  }
  return raw
}

function formatChips(
  value: unknown,
  field: PresentationFieldWithRules,
  options: { t: TranslateFn; locale: LocaleCode },
): string[] {
  const items = Array.isArray(value) ? value : [value]
  return items
    .map((item) => resolveCatalogOptionLabel(field.qualified_code, text(item), options.t, options.locale))
    .filter(Boolean)
}

function phoneHref(value: string): string | null {
  const digits = value.replace(/[^\d+]/g, '')
  return digits ? `tel:${digits}` : null
}

function emailHref(value: string): string | null {
  return value.includes('@') ? `mailto:${value}` : null
}

function runtimeFieldFromPresentationRow(row: Record<string, unknown>): PresentationFieldWithRules | null {
  const qualifiedCode = text(row.qualified_code)
  if (!qualifiedCode) return null
  const embedded = record(row.field)
  const overrides = record(row.presentation_overrides)
  const label =
    text(row.label) ||
    text(row.label_override) ||
    text(overrides.label_override) ||
    text(embedded.label_key) ||
    text(embedded.name) ||
    ''
  const fieldType =
    text(row.field_type) ||
    text(embedded.field_type) ||
    text(row.widget_hint) ||
    text(overrides.widget_hint) ||
    null
  const widgetHint = text(row.widget_hint) || text(overrides.widget_hint) || fieldType
  const rules =
    (row.presentation_rules && typeof row.presentation_rules === 'object'
      ? row.presentation_rules
      : null) ||
    (overrides.presentation_rules && typeof overrides.presentation_rules === 'object'
      ? overrides.presentation_rules
      : null)
  return {
    qualified_code: qualifiedCode,
    sort_order: Number(row.sort_order ?? 0),
    intake_level: text(row.intake_level) || text(overrides.intake_level) || 'optional',
    label,
    field_type: fieldType,
    widget_hint: widgetHint,
    presentation_rules: rules
      ? (rules as PresentationFieldWithRules['presentation_rules'])
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

function presentationCodesForLoad(
  submission: LeadSubmissionV1 | null,
  formLocale: LocaleCode,
): string[] {
  const codes = [
    resolveSubmissionPresentationCode(submission),
    formLocale === 'en'
      ? 'service_sales.targeted_advertising.public_en'
      : formLocale === 'ru'
        ? 'service_sales.targeted_advertising.public_ru'
        : defaultPlatformPresentationCode(),
    defaultPlatformPresentationCode(),
  ]
  return [...new Set(codes.filter((code): code is string => Boolean(code)))]
}

export async function loadSubmissionPresentationFields(
  submission: LeadSubmissionV1 | null,
  entityProfileCode: string,
  formLocale: LocaleCode = 'pl',
): Promise<PresentationLoadResult> {
  // 1) Published presentation used by the public questionnaire (CRM-readable).
  for (const presentationCode of presentationCodesForLoad(submission, formLocale)) {
    try {
      const runtime = await resolveEntityProfilePresentation(entityProfileCode, presentationCode)
      const fields = (runtime.fields || [])
        .map((row) => runtimeFieldFromPresentationRow(row as unknown as Record<string, unknown>))
        .filter((row): row is PresentationFieldWithRules => row != null)
      if (fields.length > 0) return { fields }
    } catch {
      // try next source
    }
  }

  // 2) Admin form detail / preset (may 403 for non-admin roles).
  const formId = text(submission?.form_id)
  if (formId) {
    try {
      const detail = await getIntakeFormDetail(formId)
      const fields = (detail.presentation?.fields || [])
        .map((row) => runtimeFieldFromPresentationRow(row as unknown as Record<string, unknown>))
        .filter((row): row is PresentationFieldWithRules => row != null)
      if (fields.length > 0) return { fields }
    } catch {
      // fall through
    }
  }

  for (const presentationCode of presentationCodesForLoad(submission, formLocale)) {
    try {
      const preset = await getEntityProfilePresentationPreset(entityProfileCode, presentationCode)
      const fields = (preset.fields || [])
        .map((row) => runtimeFieldFromPresentationRow(row as unknown as Record<string, unknown>))
        .filter((row): row is PresentationFieldWithRules => row != null)
      if (fields.length > 0) return { fields }
    } catch {
      // try next code
    }
  }

  try {
    const catalog = await getEntityProfileFields(entityProfileCode)
    return {
      fields: (catalog.fields || []).map(runtimeFieldFromCatalog),
    }
  } catch {
    return { fields: [] }
  }
}

function resolveFieldLabel(
  field: PresentationFieldWithRules,
  catalogByCode: Map<string, EntityProfileFieldOption>,
  t: TranslateFn,
  locale: LocaleCode,
): string {
  // Prefer published presentation label for the submission language.
  const fromPresentation = intakePresentationFieldLabel(t, field, locale)
  if (fromPresentation && fromPresentation !== field.qualified_code && !fromPresentation.startsWith('fields.')) {
    // intakePresentationFieldLabel falls back to field.label (snapshot) when i18n is empty.
    if (field.label || fromPresentation !== leafSuffix(field.qualified_code)) {
      return fromPresentation
    }
  }
  if (field.label && !field.label.startsWith('fields.')) return field.label
  const catalog = catalogByCode.get(field.qualified_code)
  const labelKey = catalog?.label || field.label
  if (labelKey?.startsWith('fields.')) {
    const translated = t(labelKey, { defaultValue: '' }).trim()
    if (translated && translated !== labelKey) return translated
  }
  if (catalog?.label && !catalog.label.startsWith('fields.')) return catalog.label
  return humanizeOptionValue(leafSuffix(field.qualified_code))
}

function valuesEqual(a: unknown, b: unknown): boolean {
  if (Array.isArray(a) || Array.isArray(b)) {
    const left = Array.isArray(a) ? a.map(text).filter(Boolean).sort() : [text(a)].filter(Boolean)
    const right = Array.isArray(b) ? b.map(text).filter(Boolean).sort() : [text(b)].filter(Boolean)
    return left.length === right.length && left.every((item, index) => item === right[index])
  }
  return text(a) === text(b)
}

function buildAnswerRow(input: {
  qualifiedCode: string
  rawValue: unknown
  field: PresentationFieldWithRules | null
  sortOrder: number
  catalogByCode: Map<string, EntityProfileFieldOption>
  previousValue?: unknown
  markChanges: boolean
  t: TranslateFn
  locale: LocaleCode
}): SubmissionAnswerRow | null {
  const { field, rawValue } = input
  if (field) {
    const intakeLevel = text(field.intake_level).toLowerCase()
    if (intakeLevel === 'hidden') return null
  }

  const kind = detectKind(field, rawValue)
  let chips: string[] | undefined
  let value = ''
  let href: string | null = null

  if (field) {
    if (kind === 'chips') {
      chips = formatChips(rawValue, field, { t: input.t, locale: input.locale })
      value = chips.join(', ')
    } else {
      value = formatSubmissionFieldValue(rawValue, field, { t: input.t, locale: input.locale })
    }
  } else if (Array.isArray(rawValue)) {
    chips = rawValue
      .map((item) => {
        const itemText = text(item)
        if (hasCatalogOption(input.qualifiedCode, itemText, input.t, input.locale)) {
          return resolveCatalogOptionLabel(input.qualifiedCode, itemText, input.t, input.locale)
        }
        return humanizeOptionValue(itemText)
      })
      .filter(Boolean)
    value = chips.join(', ')
  } else if (typeof rawValue === 'boolean') {
    value = formatBoolean(rawValue, input.t, input.locale)
  } else {
    const raw = text(rawValue)
    value = hasCatalogOption(input.qualifiedCode, raw, input.t, input.locale)
      ? resolveCatalogOptionLabel(input.qualifiedCode, raw, input.t, input.locale)
      : humanizeOptionValue(raw) || raw
  }

  if (!value) return null

  if (kind === 'phone') href = phoneHref(value)
  if (kind === 'email') href = emailHref(value)

  const changed =
    input.markChanges && input.previousValue !== undefined
      ? !valuesEqual(rawValue, input.previousValue)
      : false

  return {
    qualifiedCode: input.qualifiedCode,
    label: field
      ? resolveFieldLabel(field, input.catalogByCode, input.t, input.locale)
      : humanizeOptionValue(leafSuffix(input.qualifiedCode)),
    value,
    sortOrder: input.sortOrder,
    kind: chips && chips.length > 0 ? 'chips' : kind,
    chips,
    href,
    changed,
    sectionKey: sectionKeyForField(input.qualifiedCode),
  }
}

/**
 * Group filled answers by business section.
 * Section and question order follow published presentation sort_order (first appearance).
 */
export function buildGroupedSubmissionAnswerSections(input: {
  values: Record<string, unknown>
  previousValues?: Record<string, unknown> | null
  presentationFields: PresentationFieldWithRules[]
  catalogFields?: EntityProfileFieldOption[]
  t: TranslateFn
  locale: LocaleCode
  markChanges?: boolean
}): SubmissionAnswerSection[] {
  const catalogByCode = new Map((input.catalogFields || []).map((row) => [row.qualified_code, row]))
  const evaluated = evaluatePresentationFields(input.presentationFields, input.values)
  const orderedFields = [...evaluated].sort((a, b) => a.sort_order - b.sort_order || a.qualified_code.localeCompare(b.qualified_code))
  const fieldsByCode = new Map(orderedFields.map((field) => [field.qualified_code, field]))
  const seenCodes = new Set<string>()
  const sectionOrder: string[] = []
  const sectionRows = new Map<string, SubmissionAnswerRow[]>()

  const pushRow = (row: SubmissionAnswerRow) => {
    if (!sectionRows.has(row.sectionKey)) {
      sectionOrder.push(row.sectionKey)
      sectionRows.set(row.sectionKey, [])
    }
    sectionRows.get(row.sectionKey)!.push(row)
  }

  for (const field of orderedFields) {
    if (!field.evaluated?.visible) continue
    const rawValue = input.values[field.qualified_code]
    if (rawValue == null || rawValue === '' || (Array.isArray(rawValue) && rawValue.length === 0)) continue
    const row = buildAnswerRow({
      qualifiedCode: field.qualified_code,
      rawValue,
      field,
      sortOrder: field.sort_order,
      catalogByCode,
      previousValue: input.previousValues?.[field.qualified_code],
      markChanges: Boolean(input.markChanges),
      t: input.t,
      locale: input.locale,
    })
    if (!row) continue
    seenCodes.add(field.qualified_code)
    pushRow(row)
  }

  // Fallback: values present without matching presentation field (legacy snapshots).
  let fallbackSort = orderedFields.reduce((max, field) => Math.max(max, field.sort_order), 0)
  for (const [qualifiedCode, rawValue] of Object.entries(input.values)) {
    if (seenCodes.has(qualifiedCode)) continue
    if (rawValue == null || rawValue === '' || (Array.isArray(rawValue) && rawValue.length === 0)) continue
    fallbackSort += 10
    const row = buildAnswerRow({
      qualifiedCode,
      rawValue,
      field: fieldsByCode.get(qualifiedCode) || null,
      sortOrder: fallbackSort,
      catalogByCode,
      previousValue: input.previousValues?.[qualifiedCode],
      markChanges: Boolean(input.markChanges),
      t: input.t,
      locale: input.locale,
    })
    if (!row) continue
    pushRow(row)
  }

  return sectionOrder.map((key) => ({
    key,
    title: sectionTitleForKey(key, input.locale, input.t),
    rows: sectionRows.get(key) || [],
  }))
}

/** @deprecated Prefer buildGroupedSubmissionAnswerSections — flat list kept for callers. */
export function buildSubmissionAnswerRows(input: {
  values: Record<string, unknown>
  presentationFields: PresentationFieldWithRules[]
  catalogFields?: EntityProfileFieldOption[]
  t: TranslateFn
  locale: string
}): SubmissionAnswerRow[] {
  return buildGroupedSubmissionAnswerSections({
    ...input,
    locale: input.locale as LocaleCode,
  }).flatMap((section) => section.rows)
}

export function resolveFormLocale(
  lead: { normalized?: Record<string, unknown> | null },
  submission: LeadSubmissionV1 | null,
): string | null {
  const source = record(submission?.source)
  const fromSubmission = text(source.form_locale || source.locale || (submission as { locale?: unknown } | null)?.locale)
  if (fromSubmission) return fromSubmission.slice(0, 2).toLowerCase()

  const fromLead = text(record(lead.normalized).sales_questionnaire_locale)
  if (fromLead) return fromLead.slice(0, 2).toLowerCase()

  const presentation = resolveSubmissionPresentationCode(submission) || ''
  if (presentation.includes('.public_pl') || presentation.endsWith('_pl') || presentation.includes('.pl')) return 'pl'
  if (presentation.includes('.public_en') || presentation.endsWith('_en') || presentation.includes('.en')) return 'en'
  if (presentation.includes('.public_ru') || presentation.endsWith('_ru') || presentation.includes('.ru')) return 'ru'

  // Tenant form presentations (`.form.*`) are Polish by default in HostFlow sales flows.
  if (presentation.includes('.form.') || presentation.includes('targeted_advertising')) return 'pl'
  return null
}

export function formLocaleLabel(locale: string | null, t: TranslateFn): string {
  const code = String(locale || '').toLowerCase()
  if (code === 'pl') return t('app.sales_questionnaire.locale_pl', { defaultValue: 'Questionnaire in Polish' })
  if (code === 'en') return t('app.sales_questionnaire.locale_en', { defaultValue: 'Questionnaire in English' })
  if (code === 'ru') return t('app.sales_questionnaire.locale_ru', { defaultValue: 'Questionnaire in Russian' })
  return ''
}

export function formatSubmittedAt(iso: string | null | undefined, locale: string): string {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  const loc = locale === 'pl' ? 'pl-PL' : locale === 'ru' ? 'ru-RU' : 'en-US'
  return date.toLocaleString(loc, {
    day: 'numeric',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export async function loadGroupedSubmissionAnswersForLead(
  lead: { normalized?: Record<string, unknown> | null; id?: string },
  options: {
    t: TranslateFn
    locale: LocaleCode
    /** 0 = latest; older indexes from history (newest-first). */
    historyIndex?: number
  },
): Promise<GroupedSubmissionAnswers> {
  const history = readLeadSubmissions(lead)
  const historyNewestFirst = [...history].reverse()
  const historyIndex = Math.max(0, Math.min(options.historyIndex ?? 0, Math.max(historyNewestFirst.length - 1, 0)))
  const selected = historyNewestFirst[historyIndex] || readLatestSubmission(lead)
  const previous = historyNewestFirst[historyIndex + 1] || null
  const entityProfileCode = resolveSubmissionEntityProfileCode(selected, lead)
  const values = readSubmissionAnswerValues(lead as { id: string; normalized?: Record<string, unknown> | null }, selected, entityProfileCode)
  const previousValues = previous
    ? readSubmissionAnswerValues(lead as { id: string; normalized?: Record<string, unknown> | null }, previous, entityProfileCode)
    : null

  if (Object.keys(values).length === 0) {
    return {
      sections: [],
      submittedAt: selected?.submitted_at || null,
      formLocale: asLocaleCode(resolveFormLocale(lead, selected) || 'pl'),
      isResubmission: history.length > 1,
      history: historyNewestFirst,
      selectedSubmission: selected,
    }
  }

  const formLocale = asLocaleCode(resolveFormLocale(lead, selected) || 'pl')

  const [{ fields }, catalog] = await Promise.all([
    loadSubmissionPresentationFields(selected, entityProfileCode, formLocale),
    getEntityProfileFields(entityProfileCode).catch(() => ({ fields: [] as EntityProfileFieldOption[] })),
  ])

  const sections = buildGroupedSubmissionAnswerSections({
    values,
    previousValues,
    presentationFields: fields,
    catalogFields: catalog.fields,
    t: options.t,
    // Always localize answers in the questionnaire language, not CRM UI language.
    locale: formLocale,
    markChanges: history.length > 1 && historyIndex === 0,
  })

  return {
    sections,
    submittedAt: selected?.submitted_at || null,
    formLocale,
    isResubmission: history.length > 1,
    history: historyNewestFirst,
    selectedSubmission: selected,
  }
}

export async function loadSubmissionAnswerRowsForLead(
  lead: { normalized?: Record<string, unknown> | null },
  options: { t: TranslateFn; locale: string },
): Promise<SubmissionAnswerRow[]> {
  const grouped = await loadGroupedSubmissionAnswersForLead(lead, {
    t: options.t,
    locale: options.locale as LocaleCode,
  })
  return grouped.sections.flatMap((section) => section.rows)
}
