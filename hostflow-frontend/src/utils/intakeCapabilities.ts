/** User-facing Capability catalog for questionnaire creation (F3-B-10). */

export type IntakeCapabilityId = 'targeted_advertising' | 'driver_hiring'

export type IntakeCapability = {
  id: IntakeCapabilityId
  entityProfileCode: string
  defaultTitleKey: string
  defaultTitleFallback: string
  descriptionKey: string
  descriptionFallback: string
  slugPrefix: string
}

export const INTAKE_CAPABILITY_CATALOG: IntakeCapability[] = [
  {
    id: 'targeted_advertising',
    entityProfileCode: 'service_sales.targeted_advertising',
    defaultTitleKey: 'admin.capabilities.targeted_advertising.title',
    defaultTitleFallback: 'Таргетированная реклама',
    descriptionKey: 'admin.capabilities.targeted_advertising.description',
    descriptionFallback: 'Анкета для продажи услуги таргетированной рекламы компаниям.',
    slugPrefix: 'targeted-advertising',
  },
  {
    id: 'driver_hiring',
    entityProfileCode: 'recruitment.candidate.driver_ce',
    defaultTitleKey: 'admin.capabilities.driver_hiring.title',
    defaultTitleFallback: 'Найм водителей',
    descriptionKey: 'admin.capabilities.driver_hiring.description',
    descriptionFallback: 'Анкета для кандидатов на позицию водителя C+E.',
    slugPrefix: 'driver-hiring',
  },
]

export function capabilityById(id: IntakeCapabilityId): IntakeCapability | undefined {
  return INTAKE_CAPABILITY_CATALOG.find((row) => row.id === id)
}

export function capabilityForProfileCode(code: string): IntakeCapability | undefined {
  const needle = String(code || '').trim()
  return INTAKE_CAPABILITY_CATALOG.find((row) => row.entityProfileCode === needle)
}

export function filterAvailableCapabilities(
  profileCodes: string[],
): IntakeCapability[] {
  const available = new Set(profileCodes.map((code) => code.trim()).filter(Boolean))
  return INTAKE_CAPABILITY_CATALOG.filter((row) => available.has(row.entityProfileCode))
}

export function defaultSlugForCapability(capability: IntakeCapability): string {
  const suffix = Date.now().toString(36).slice(-4)
  return `${capability.slugPrefix}-${suffix}`
}
