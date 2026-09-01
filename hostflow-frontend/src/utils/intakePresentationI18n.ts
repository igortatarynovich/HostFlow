import type { FormPresentationRuntime } from '../modules/public-intake/types'
import { lookupScopedTranslation, type LocaleCode } from '../i18n'

type TFn = (key: string, options?: { defaultValue?: string; values?: Record<string, unknown> }) => string

function scopedLabel(
  locale: LocaleCode | undefined,
  basePath: string,
  leafKey: string,
  fallback: string,
): string {
  if (locale && leafKey) {
    const translated = lookupScopedTranslation(locale, basePath, leafKey)
    if (translated) return translated
  }
  return fallback
}

export function intakePresentationProfileTitle(
  t: TFn,
  presentation: Pick<FormPresentationRuntime, 'entity_profile_code' | 'profile_name'>,
  locale?: LocaleCode,
): string {
  const code = String(presentation.entity_profile_code || '').trim()
  const fallback = String(presentation.profile_name || code).trim()
  if (!code) return fallback
  return scopedLabel(locale, 'public.intake.presentation.profiles', code, fallback)
}

function looksLikeI18nKey(value: string): boolean {
  return /^(fields|admin|public|forms)\./.test(value)
}

function humanizeQualifiedCode(code: string): string {
  const last = code.split('.').pop() || code
  return last.replace(/_/g, ' ')
}

export function intakePresentationFieldLabel(
  t: TFn,
  field: Pick<FormPresentationRuntime['fields'][number], 'qualified_code' | 'label'>,
  locale?: LocaleCode,
): string {
  const code = String(field.qualified_code || '').trim()
  const raw = String(field.label || '').trim()
  if (!code) return raw
  const scoped = locale ? lookupScopedTranslation(locale, 'public.intake.presentation.fields', code) : undefined
  if (scoped) return scoped
  if (raw && !looksLikeI18nKey(raw)) return raw
  if (raw) {
    const viaT = t(raw, { defaultValue: '' })
    if (viaT && viaT !== raw) return viaT
  }
  return humanizeQualifiedCode(code)
}

export function intakePresentationSearchRoleLabel(
  t: TFn,
  searchRole: string | undefined | null,
  locale?: LocaleCode,
): string | null {
  const role = String(searchRole || '').trim()
  if (!role) return null
  const key = `public.intake.presentation.search_roles.${role}`
  const translated = t(key, { defaultValue: '' })
  if (translated && translated !== key) return translated
  if (locale) {
    const scoped = lookupScopedTranslation(locale, 'public.intake.presentation.search_roles', role)
    if (scoped) return scoped
  }
  return role
}
