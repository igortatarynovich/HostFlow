import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import type { ComboboxOption } from '../components/ui/comboboxShared'
import { buildCountryOptions } from '../data/countries'

type CatalogOption = { value: string; label: string }

function mapOptions(rows: CatalogOption[] | undefined, fallback: ComboboxOption[]): ComboboxOption[] {
  if (!rows?.length) return fallback
  return rows.map((row) => ({ value: row.value, label: row.label }))
}

export function usePlatformCountryOptions(locale?: string) {
  const fallback = useMemo(() => buildCountryOptions(locale), [locale])
  const [options, setOptions] = useState<ComboboxOption[]>(fallback)

  useEffect(() => {
    let cancelled = false
    void api
      .get<CatalogOption[]>('/catalogs/countries/options')
      .then((res) => {
        if (!cancelled) setOptions(mapOptions(res.data, fallback))
      })
      .catch(() => {
        if (!cancelled) setOptions(fallback)
      })
    return () => {
      cancelled = true
    }
  }, [fallback])

  return options
}

export function usePlatformDialCodeOptions() {
  const [options, setOptions] = useState<ComboboxOption[]>([])

  useEffect(() => {
    let cancelled = false
    void api
      .get<CatalogOption[]>('/catalogs/dial-codes/options')
      .then((res) => {
        if (!cancelled) setOptions(mapOptions(res.data, []))
      })
      .catch(() => {
        if (!cancelled) setOptions([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  return options
}
