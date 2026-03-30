/** Shared with Settings landing + user menu: progressive areas (no flat dump of all cards). */
export const SETTINGS_AREA_KEYS = [
  'workspace',
  'crm_setup',
  'team',
  'automations',
  'integrations',
  'billing',
  'personal',
] as const

export type SettingsAreaKey = (typeof SETTINGS_AREA_KEYS)[number]

export function isSettingsAreaKey(raw: string | null): raw is SettingsAreaKey {
  return SETTINGS_AREA_KEYS.includes(raw as SettingsAreaKey)
}

export function settingsAreaHref(area: SettingsAreaKey): string {
  return `/app/settings?section=${area}`
}
