import { useEffect, useMemo, useState } from 'react'
import { fetchVacancyCategoryOptions, type CatalogOptionDto } from '../api/catalogs'
import { detectStoredLocale, lookupScopedTranslation, type LocaleCode } from '../i18n'
import type { SearchRole } from '../services/createLaunchSearch'
import { catalogOptionDescription, catalogOptionLabel } from '../utils/catalogOptions'

const FALLBACK_ROLE_IDS: SearchRole[] = ['driver', 'warehouse', 'office', 'other']

const FALLBACK_EMOJI: Record<SearchRole, string> = {
  driver: '🚛',
  warehouse: '📦',
  office: '🏢',
  other: '✏️',
}

const FALLBACK_TITLE: Record<SearchRole, string> = {
  driver: 'Driver',
  warehouse: 'Warehouse',
  office: 'Office',
  other: 'Other',
}

const FALLBACK_SUBTITLE: Record<SearchRole, string> = {
  driver: 'CE, cat. C, international routes',
  warehouse: 'Picker, forklift, logistics',
  office: 'Dispatcher, accountant, manager',
  other: 'Custom role',
}

function buildFallbackRoles(locale?: string): CatalogOptionDto[] {
  const code = (locale?.startsWith('ru')
    ? 'ru'
    : locale?.startsWith('pl')
      ? 'pl'
      : locale?.startsWith('en')
        ? 'en'
        : detectStoredLocale()) as LocaleCode
  return FALLBACK_ROLE_IDS.map((id) => {
    const title =
      lookupScopedTranslation(code, `app.vacancy_categories.${id}`, 'title') || FALLBACK_TITLE[id]
    const subtitle =
      lookupScopedTranslation(code, `app.vacancy_categories.${id}`, 'subtitle') ||
      FALLBACK_SUBTITLE[id]
    return {
      value: id,
      label: title,
      meta: {
        emoji: FALLBACK_EMOJI[id],
        label_en: FALLBACK_TITLE[id],
        label_ru:
          lookupScopedTranslation('ru', `app.vacancy_categories.${id}`, 'title') || FALLBACK_TITLE[id],
        subtitle_en: FALLBACK_SUBTITLE[id],
        subtitle_ru:
          lookupScopedTranslation('ru', `app.vacancy_categories.${id}`, 'subtitle') ||
          FALLBACK_SUBTITLE[id],
        launch_search_supported: true,
        description_en: FALLBACK_SUBTITLE[id],
        description_ru:
          lookupScopedTranslation('ru', `app.vacancy_categories.${id}`, 'subtitle') ||
          FALLBACK_SUBTITLE[id],
      },
    }
  })
}

export type VacancyCategoryOption = {
  id: SearchRole
  emoji: string
  title: string
  subtitle: string
}

function mapRoleOption(row: CatalogOptionDto, locale?: string): VacancyCategoryOption {
  const meta = row.meta ?? {}
  return {
    id: row.value as SearchRole,
    emoji: String(meta.emoji ?? '💼'),
    title: catalogOptionLabel(row, locale),
    subtitle: catalogOptionDescription(row, locale),
  }
}

export function useVacancyCategoryOptions(locale?: string, launchSearchOnly = true) {
  const fallbackRows = useMemo(() => buildFallbackRoles(locale), [locale])
  const fallback = useMemo(
    () => fallbackRows.map((row) => mapRoleOption(row, locale)),
    [fallbackRows, locale],
  )
  const [options, setOptions] = useState<VacancyCategoryOption[]>(fallback)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    void fetchVacancyCategoryOptions(launchSearchOnly)
      .then((rows) => {
        if (cancelled) return
        const mapped = (rows.length ? rows : fallbackRows).map((row) => mapRoleOption(row, locale))
        setOptions(mapped)
      })
      .catch(() => {
        if (!cancelled) setOptions(fallback)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [fallback, fallbackRows, launchSearchOnly, locale])

  return { options, loading }
}
