import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import en from './en.json'
import ru from './ru.json'
import pl from './pl.json'

const RESOURCES = {
  en,
  ru,
  pl,
} as const

const FALLBACK_ORDER: LocaleCode[] = ['en', 'ru', 'pl']
const LOCALE_STORAGE_KEY = 'hf:ui:lang'

export type LocaleCode = keyof typeof RESOURCES

export type TranslateOptions = {
  defaultValue?: string
  values?: Record<string, string | number>
  /**
   * Legacy ad-hoc interpolation keys passed at the top level (e.g. `{ count: 3 }`)
   * by older callers. The runtime currently only formats `options.values`, so any
   * top-level key is best-effort and only kept here to avoid breaking the type
   * surface. Prefer `values: { count: 3 }` for new code.
   */
  [extra: string]: unknown
}

export type TranslateFn = (key: string, options?: TranslateOptions) => string

type I18nContextValue = {
  locale: LocaleCode
  setLocale: (next: LocaleCode) => void
  t: TranslateFn
}

const I18nContext = createContext<I18nContextValue>({
  locale: 'en',
  setLocale: () => {},
  t: (key, options) => options?.defaultValue ?? key,
})

function detectLocale(): LocaleCode {
  if (typeof window !== 'undefined') {
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY)
    if (stored === 'ru' || stored === 'en' || stored === 'pl') {
      return stored
    }
  }
  return 'en'
}

function lookup(path: string, bundle: unknown): string | undefined {
  if (!bundle || typeof bundle !== 'object') return undefined
  const segments = path.split('.')
  let cursor: unknown = bundle
  for (const segment of segments) {
    if (!cursor || typeof cursor !== 'object') {
      return undefined
    }
    cursor = (cursor as Record<string, unknown>)[segment]
  }
  if (typeof cursor === 'string' || typeof cursor === 'number') {
    return String(cursor)
  }
  return undefined
}

function format(template: string, values?: Record<string, string | number>): string {
  if (!values) return template
  return Object.entries(values).reduce((acc, [key, value]) => {
    const token = `{${key}}`
    return acc.split(token).join(String(value))
  }, template)
}

export function I18nProvider({
  children,
  initialLocale,
}: {
  children: ReactNode
  initialLocale?: LocaleCode
}) {
  const [locale, setLocale] = useState<LocaleCode>(initialLocale ?? detectLocale())

  const value = useMemo<I18nContextValue>(() => {
    const translate: TranslateFn = (key, options) => {
      const tried = new Set<LocaleCode>()
      const chain = [locale, ...FALLBACK_ORDER].filter((code): code is LocaleCode => {
        if (tried.has(code)) return false
        tried.add(code)
        return Boolean(RESOURCES[code])
      })
      for (const code of chain) {
        const bundle = RESOURCES[code]
        const raw = lookup(key, bundle)
        if (raw) {
          return format(raw, options?.values)
        }
      }
      return format(options?.defaultValue ?? key, options?.values)
    }

    return {
      locale,
      setLocale,
      t: translate,
    }
  }, [locale])

  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, locale)
    }
  }, [locale])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextValue {
  return useContext(I18nContext)
}
