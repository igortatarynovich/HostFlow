import { detectStoredLocale, lookupScopedTranslation, type LocaleCode } from '../i18n'
import type { SearchRole } from './launchSearchRoleDefaults'

export function launchSearchRoleTitle(
  role: SearchRole,
  locale: LocaleCode = detectStoredLocale(),
  otherLabel?: string,
): string {
  if (role === 'other') {
    const custom = String(otherLabel || '').trim()
    if (custom) return custom
  }
  const translated = lookupScopedTranslation(locale, 'app.recruitment.launch_search.roles', role)
  if (translated) return translated
  const fallbacks: Record<SearchRole, string> = {
    driver: 'CE drivers',
    warehouse: 'Warehouse',
    office: 'Office',
    other: 'Hiring',
  }
  return fallbacks[role]
}

export function buildLaunchSearchTitle(
  role: SearchRole,
  companyName: string,
  locale?: LocaleCode,
  otherLabel?: string,
): string {
  const rolePart = launchSearchRoleTitle(role, locale, otherLabel)
  return `${rolePart} — ${companyName}`
}
