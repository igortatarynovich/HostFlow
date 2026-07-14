import { useEffect, useMemo, useState } from 'react'
import { fetchVacancyCategoryOptions, type CatalogOptionDto } from '../api/catalogs'
import type { SearchRole } from '../services/createLaunchSearch'
import { catalogOptionDescription, catalogOptionLabel } from '../utils/catalogOptions'

const FALLBACK_ROLES: CatalogOptionDto[] = [
  {
    value: 'driver',
    label: 'Водитель',
    meta: { emoji: '🚛', subtitle_ru: 'CE, кат. C, международные рейсы', launch_search_supported: true },
  },
  {
    value: 'warehouse',
    label: 'Склад',
    meta: { emoji: '📦', subtitle_ru: 'Комплектовщик, погрузчик, логистика', launch_search_supported: true },
  },
  {
    value: 'office',
    label: 'Офис',
    meta: { emoji: '🏢', subtitle_ru: 'Диспетчер, бухгалтер, менеджер', launch_search_supported: true },
  },
  {
    value: 'other',
    label: 'Другое',
    meta: { emoji: '✏️', subtitle_ru: 'Своя формулировка', launch_search_supported: true },
  },
]

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
  const fallback = useMemo(
    () => FALLBACK_ROLES.map((row) => mapRoleOption(row, locale)),
    [locale],
  )
  const [options, setOptions] = useState<VacancyCategoryOption[]>(fallback)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    void fetchVacancyCategoryOptions(launchSearchOnly)
      .then((rows) => {
        if (cancelled) return
        const mapped = (rows.length ? rows : FALLBACK_ROLES).map((row) => mapRoleOption(row, locale))
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
  }, [fallback, launchSearchOnly, locale])

  return { options, loading }
}
