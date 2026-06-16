import type { EffectiveCardLayout, EffectiveCardLayoutField } from '../api/fieldRegistry'

export type VacancyRegistryFieldKey =
  | 'title'
  | 'description'
  | 'location'
  | 'employment_type'
  | 'headcount_target'
  | 'company_id'

const QUALIFIED_TO_VACANCY_KEY: Record<string, VacancyRegistryFieldKey> = {
  'recruitment.vacancy.title': 'title',
  'recruitment.vacancy.description': 'description',
  'recruitment.vacancy.location': 'location',
  'recruitment.vacancy.employment_type': 'employment_type',
  'recruitment.vacancy.headcount_target': 'headcount_target',
  'recruitment.vacancy.company_id': 'company_id',
}

const DEFAULT_VACANCY_FIELD_ORDER: VacancyRegistryFieldKey[] = [
  'title',
  'location',
  'employment_type',
  'company_id',
  'headcount_target',
  'description',
]

export function vacancyFieldKeyFromQualified(qualifiedCode: string): VacancyRegistryFieldKey | null {
  const direct = QUALIFIED_TO_VACANCY_KEY[qualifiedCode]
  if (direct) return direct
  const tail = qualifiedCode.split('.').pop()?.replace('[]', '') || ''
  const values = Object.values(QUALIFIED_TO_VACANCY_KEY)
  if (values.includes(tail as VacancyRegistryFieldKey)) {
    return tail as VacancyRegistryFieldKey
  }
  return null
}

export function resolveVacancyLayoutField(
  effectiveLayout: EffectiveCardLayout | null | undefined,
  fieldKey: VacancyRegistryFieldKey,
): EffectiveCardLayoutField | undefined {
  if (!effectiveLayout?.fields?.length) return undefined
  return effectiveLayout.fields.find((field) => {
    if (vacancyFieldKeyFromQualified(field.qualified_code) === fieldKey) return true
    const aliases = field.legacy_aliases || []
    return aliases.includes(fieldKey)
  })
}

export function hasActiveVacancyLayout(
  effectiveLayout: EffectiveCardLayout | null | undefined,
): boolean {
  return Boolean(
    effectiveLayout &&
      effectiveLayout.resolution_source !== 'not_found' &&
      effectiveLayout.fields?.length,
  )
}

export function vacancyFieldVisible(
  fieldKey: VacancyRegistryFieldKey,
  effectiveLayout: EffectiveCardLayout | null | undefined,
): boolean {
  if (!hasActiveVacancyLayout(effectiveLayout)) return true
  const field = resolveVacancyLayoutField(effectiveLayout, fieldKey)
  if (!field) return false
  return field.visible !== false
}

export function vacancyFieldRequired(
  fieldKey: VacancyRegistryFieldKey,
  effectiveLayout: EffectiveCardLayout | null | undefined,
): boolean {
  if (!hasActiveVacancyLayout(effectiveLayout)) return fieldKey === 'title'
  const field = resolveVacancyLayoutField(effectiveLayout, fieldKey)
  return field?.required === true
}

export function vacancyFieldLabel(
  fieldKey: VacancyRegistryFieldKey,
  defaultLabel: string,
  effectiveLayout: EffectiveCardLayout | null | undefined,
): string {
  const field = resolveVacancyLayoutField(effectiveLayout, fieldKey)
  const override = field?.label_override?.trim()
  if (override) return override
  if (field?.name?.trim()) return field.name.trim()
  return defaultLabel
}

export function getVacancyFieldOrder(
  effectiveLayout: EffectiveCardLayout | null | undefined,
): VacancyRegistryFieldKey[] | null {
  if (!hasActiveVacancyLayout(effectiveLayout)) return null
  const ordered: VacancyRegistryFieldKey[] = []
  const seen = new Set<VacancyRegistryFieldKey>()
  for (const section of effectiveLayout?.sections || []) {
    for (const field of section.fields || []) {
      const key = vacancyFieldKeyFromQualified(field.qualified_code)
      if (!key || seen.has(key)) continue
      seen.add(key)
      ordered.push(key)
    }
  }
  return ordered.length ? ordered : null
}

export function getVacancyFieldsRenderOrder(
  effectiveLayout: EffectiveCardLayout | null | undefined,
): VacancyRegistryFieldKey[] {
  return getVacancyFieldOrder(effectiveLayout) ?? DEFAULT_VACANCY_FIELD_ORDER
}
