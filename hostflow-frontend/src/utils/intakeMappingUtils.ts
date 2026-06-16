/** Lead intake Meta mapping — qualified field codes ↔ legacy normalized targets (P5). */

export const LEAD_INTAKE_QUALIFIED_PRESETS = [
  'recruitment.candidate.first_name',
  'recruitment.candidate.last_name',
  'recruitment.candidate.contacts.phone',
  'recruitment.candidate.contacts.phone_country_code',
  'recruitment.candidate.contacts.email',
  'recruitment.candidate.contacts.preferred_messenger',
  'platform.identity.birth_date',
  'platform.identity.citizenship',
  'platform.identity.address',
  'recruitment.candidate.personal.residency_status',
  'recruitment.candidate.personal.current_location',
  'recruitment.candidate.personal.in_poland',
  'recruitment.candidate.experience.years_ce',
] as const

const QUALIFIED_TO_LEGACY_TARGET: Record<string, string> = {
  'recruitment.candidate.first_name': 'first_name',
  'recruitment.candidate.last_name': 'last_name',
  'recruitment.candidate.contacts.phone': 'phone',
  'recruitment.candidate.contacts.phone_country_code': 'phone_country_code',
  'recruitment.candidate.contacts.email': 'email',
  'recruitment.candidate.contacts.preferred_messenger': 'preferred_contact',
  'platform.identity.birth_date': 'birth_date',
  'platform.identity.citizenship': 'citizenship',
  'platform.identity.address': 'address',
  'recruitment.candidate.personal.residency_status': 'poland_stay_basis',
  'recruitment.candidate.personal.current_location': 'current_location',
  'recruitment.candidate.personal.in_poland': 'in_poland',
  'recruitment.candidate.experience.years_ce': 'experience_eu_years',
}

const LEGACY_TO_QUALIFIED: Record<string, string> = Object.fromEntries(
  Object.entries(QUALIFIED_TO_LEGACY_TARGET).map(([q, legacy]) => [legacy, q]),
)

export function legacyTargetFromQualified(qualifiedCode: string): string {
  const code = qualifiedCode.trim()
  if (!code) return ''
  return QUALIFIED_TO_LEGACY_TARGET[code] || ''
}

export function qualifiedCodeFromLegacyTarget(target: string): string {
  const key = target.trim()
  if (!key) return ''
  if (key.includes('.') && key.startsWith('recruitment.') || key.startsWith('platform.')) {
    return key
  }
  return LEGACY_TO_QUALIFIED[key] || ''
}

export function isQualifiedFieldCode(value: string): boolean {
  const v = value.trim()
  return v.startsWith('recruitment.') || v.startsWith('platform.')
}

export function resolveMappingDisplayTarget(target: string, qualifiedFieldCode?: string | null): string {
  const qualified = String(qualifiedFieldCode || '').trim()
  if (qualified) return qualified
  const legacy = target.trim()
  if (isQualifiedFieldCode(legacy)) return legacy
  const inferred = qualifiedCodeFromLegacyTarget(legacy)
  return inferred || legacy
}

export function resolveMappingLegacyTarget(target: string, qualifiedFieldCode?: string | null): string {
  const qualified = String(qualifiedFieldCode || '').trim()
  if (qualified) {
    const legacy = legacyTargetFromQualified(qualified)
    if (legacy) return legacy
  }
  const raw = target.trim()
  if (isQualifiedFieldCode(raw)) {
    return legacyTargetFromQualified(raw) || raw
  }
  return raw
}
