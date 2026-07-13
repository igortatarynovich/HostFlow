import { useEffect, useState } from 'react'
import { fetchCityOptions, type CatalogOptionDto } from '../api/catalogs'
import { catalogOptionLabel } from '../utils/catalogOptions'

export function useCityOptions(countryCode?: string, locale?: string) {
  const [options, setOptions] = useState<CatalogOptionDto[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const cc = String(countryCode || '').trim().toUpperCase()
    if (!cc || cc === 'OTHER') {
      setOptions([])
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)
    void fetchCityOptions(cc)
      .then((rows) => {
        if (!cancelled) setOptions(rows)
      })
      .catch(() => {
        if (!cancelled) setOptions([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [countryCode])

  const labels = options.map((row) => ({
    value: row.value,
    label: catalogOptionLabel(row, locale),
  }))

  return { options, labels, loading }
}
