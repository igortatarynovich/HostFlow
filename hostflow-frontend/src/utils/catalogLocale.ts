/**
 * Localize country and language names using Intl.DisplayNames.
 * Replaces Russian-only backend catalog labels with locale-aware display names.
 */

type LocaleCode = 'pl' | 'en' | 'ru'

let regionDisplayCache: { locale: string; instance: Intl.DisplayNames } | null = null
let languageDisplayCache: { locale: string; instance: Intl.DisplayNames } | null = null

function getRegionDisplayNames(locale: LocaleCode): Intl.DisplayNames | null {
  if (typeof Intl === 'undefined' || typeof Intl.DisplayNames === 'undefined') return null
  const loc = locale === 'pl' ? 'pl-PL' : locale === 'ru' ? 'ru-RU' : 'en'
  if (regionDisplayCache?.locale === loc) return regionDisplayCache.instance
  try {
    const instance = new Intl.DisplayNames([loc, 'en'], { type: 'region' })
    regionDisplayCache = { locale: loc, instance }
    return instance
  } catch {
    try {
      const instance = new Intl.DisplayNames(['en'], { type: 'region' })
      regionDisplayCache = { locale: 'en', instance }
      return instance
    } catch {
      return null
    }
  }
}

function getLanguageDisplayNames(locale: LocaleCode): Intl.DisplayNames | null {
  if (typeof Intl === 'undefined' || typeof Intl.DisplayNames === 'undefined') return null
  const loc = locale === 'pl' ? 'pl-PL' : locale === 'ru' ? 'ru-RU' : 'en'
  if (languageDisplayCache?.locale === loc) return languageDisplayCache.instance
  try {
    const instance = new Intl.DisplayNames([loc, 'en'], { type: 'language' })
    languageDisplayCache = { locale: loc, instance }
    return instance
  } catch {
    try {
      const instance = new Intl.DisplayNames(['en'], { type: 'language' })
      languageDisplayCache = { locale: 'en', instance }
      return instance
    } catch {
      return null
    }
  }
}

/** Localize country/region code (e.g. PL, UA) for display. */
export function getRegionDisplayName(code: string, locale: LocaleCode): string {
  if (!code || typeof code !== 'string') return code ?? ''
  const upper = code.trim().toUpperCase()
  if (upper.length === 2) {
    const display = getRegionDisplayNames(locale)
    try {
      const name = display?.of(upper)
      if (name) return name
    } catch {
      /* ignore */
    }
  }
  return code
}

/** Localize language code (e.g. pl, en) for display. "other" maps to localized "Other". */
export function getLanguageDisplayName(code: string, locale: LocaleCode): string {
  if (!code || typeof code !== 'string') return code ?? ''
  const lower = code.trim().toLowerCase()
  if (lower === 'other') {
    // "Other" - use i18n keys or fallback
    return locale === 'pl' ? 'Inny' : locale === 'ru' ? 'Другое' : 'Other'
  }
  const display = getLanguageDisplayNames(locale)
  try {
    const name = display?.of(lower)
    if (name) return name
  } catch {
    /* ignore */
  }
  return code
}
