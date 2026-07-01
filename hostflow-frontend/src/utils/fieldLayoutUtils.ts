import type { EffectiveCardLayout, EffectiveCardLayoutField } from '../api/fieldRegistry'
import type { CandidateProfile } from '../api/candidate_profiles'

export type RegistryCardSectionCode = 'basic' | 'personal' | 'experience' | 'employments' | 'agreements' | 'operations'

const QUALIFIED_TO_LEGACY: Record<string, string> = {
  'recruitment.candidate.first_name': 'first_name',
  'recruitment.candidate.last_name': 'last_name',
  'recruitment.candidate.contacts.phone_country_code': 'phone_country_code',
  'recruitment.candidate.contacts.phone': 'phone',
  'recruitment.candidate.contacts.email': 'email',
  'recruitment.candidate.contacts.preferred_messenger': 'preferred_contact',
  'platform.identity.birth_date': 'birth_date',
  'platform.identity.citizenship': 'citizenship',
  'platform.identity.address': 'address',
  'recruitment.candidate.personal.residency_status': 'poland_stay_basis',
  'recruitment.candidate.personal.current_location': 'current_location',
  'recruitment.candidate.personal.in_poland': 'in_poland',
  'recruitment.candidate.experience.years_ce': 'experience_eu_years',
  'recruitment.candidate.experience.intl_experience': 'intl_experience',
  'recruitment.candidate.experience.trailer_types[]': 'trailer_types',
  'recruitment.candidate.experience.route_types[]': 'route_types',
  'recruitment.candidate.employments[]': 'employment_history',
  'recruitment.candidate.operations.stage': 'stage',
}

export function legacyFieldKeyFromQualifiedCode(qualifiedCode: string): string {
  const direct = QUALIFIED_TO_LEGACY[qualifiedCode]
  if (direct) return direct
  const parts = qualifiedCode.split('.')
  return parts[parts.length - 1]?.replace('[]', '') || qualifiedCode
}

export function resolveLayoutField(
  effectiveLayout: EffectiveCardLayout | null | undefined,
  fieldKey: string,
): EffectiveCardLayoutField | undefined {
  if (!effectiveLayout?.fields?.length) return undefined
  const key = String(fieldKey || '').trim()
  if (!key) return undefined
  return effectiveLayout.fields.find((field) => {
    const aliases = field.legacy_aliases || []
    if (aliases.includes(key)) return true
    if (legacyFieldKeyFromQualifiedCode(field.qualified_code) === key) return true
    return field.qualified_code.endsWith(`.${key}`)
  })
}

export function hasActiveEffectiveLayout(
  effectiveLayout: EffectiveCardLayout | null | undefined,
): boolean {
  return Boolean(
    effectiveLayout &&
      effectiveLayout.resolution_source !== 'not_found' &&
      (effectiveLayout.fields?.length || effectiveLayout.sections?.length),
  )
}

export function isCardSectionVisible(
  sectionCode: RegistryCardSectionCode | string,
  effectiveLayout: EffectiveCardLayout | null | undefined,
): boolean {
  if (!hasActiveEffectiveLayout(effectiveLayout)) return true
  const code = String(sectionCode)
  const section = effectiveLayout?.sections?.find((row) => row.code === code)
  if (!section) {
    if (code === 'experience') {
      const employments = effectiveLayout?.sections?.find((row) => row.code === 'employments')
      return Boolean(employments?.fields?.some((field) => field.visible !== false))
    }
    return false
  }
  return section.fields.some((field) => field.visible !== false)
}

export function getCardSectionOrder(
  effectiveLayout: EffectiveCardLayout | null | undefined,
): RegistryCardSectionCode[] | null {
  if (!hasActiveEffectiveLayout(effectiveLayout)) return null
  const ordered: RegistryCardSectionCode[] = []
  for (const section of effectiveLayout?.sections || []) {
    if (section.code === 'employments') {
      if (!ordered.includes('experience')) ordered.push('experience')
      continue
    }
    if (section.code === 'basic' || section.code === 'personal' || section.code === 'experience') {
      if (!ordered.includes(section.code)) ordered.push(section.code)
    }
  }
  return ordered.length ? ordered : null
}

export function layoutFieldVisible(
  profile: CandidateProfile | null | undefined,
  fieldKey: string,
  effectiveLayout: EffectiveCardLayout | null | undefined,
  profileFallback: (profile: CandidateProfile | null | undefined, fieldKey: string) => boolean,
): boolean {
  const layoutField = resolveLayoutField(effectiveLayout, fieldKey)
  if (layoutField) return layoutField.visible !== false
  if (hasActiveEffectiveLayout(effectiveLayout)) return profileFallback(profile, fieldKey)
  return profileFallback(profile, fieldKey)
}

export function layoutFieldRequired(
  profile: CandidateProfile | null | undefined,
  fieldKey: string,
  effectiveLayout: EffectiveCardLayout | null | undefined,
  profileFallback: (profile: CandidateProfile | null | undefined, fieldKey: string) => boolean,
): boolean {
  const layoutField = resolveLayoutField(effectiveLayout, fieldKey)
  if (layoutField) return layoutField.required === true
  if (hasActiveEffectiveLayout(effectiveLayout)) return profileFallback(profile, fieldKey)
  return profileFallback(profile, fieldKey)
}

export function layoutFieldLabel(
  profile: CandidateProfile | null | undefined,
  fieldKey: string,
  defaultLabel: string,
  effectiveLayout: EffectiveCardLayout | null | undefined,
  profileFallback: (
    profile: CandidateProfile | null | undefined,
    fieldKey: string,
    defaultLabel: string,
  ) => string,
): string {
  const layoutField = resolveLayoutField(effectiveLayout, fieldKey)
  const override = layoutField?.label_override?.trim()
  if (override) return override
  if (layoutField?.name?.trim()) return layoutField.name.trim()
  return profileFallback(profile, fieldKey, defaultLabel)
}
