/** Shared with Settings landing + user menu: progressive areas (no flat dump of all cards). */
export const SETTINGS_AREA_KEYS = [
  'workspace',
  'recruitment_setup',
  'sales_setup',
  'team',
  'automations',
  'integrations',
  'billing',
  'personal',
] as const

export type SettingsAreaKey = (typeof SETTINGS_AREA_KEYS)[number]

/** Legacy query value from pre-ADR-023 “CRM Setup” hub. */
const LEGACY_SETTINGS_AREA_ALIASES: Record<string, SettingsAreaKey> = {
  crm_setup: 'recruitment_setup',
}

export function isSettingsAreaKey(raw: string | null): raw is SettingsAreaKey {
  if (!raw) return false
  if (SETTINGS_AREA_KEYS.includes(raw as SettingsAreaKey)) return true
  return raw in LEGACY_SETTINGS_AREA_ALIASES
}

export function normalizeSettingsAreaKey(raw: string | null): SettingsAreaKey | null {
  if (!raw) return null
  if (SETTINGS_AREA_KEYS.includes(raw as SettingsAreaKey)) return raw as SettingsAreaKey
  return LEGACY_SETTINGS_AREA_ALIASES[raw] ?? null
}

export function settingsAreaHref(area: SettingsAreaKey): string {
  return `/app/settings?section=${area}`
}
