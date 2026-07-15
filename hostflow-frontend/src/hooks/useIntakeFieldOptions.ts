import { useEffect, useMemo, useState } from 'react'
import {
  fetchAdvertisedServiceOptions,
  fetchCityOptions,
  fetchCountryOptions,
  fetchProfessionOptions,
  fetchRegionOptions,
  type CatalogOptionDto,
} from '../api/catalogs'
import type { FormPresentationField } from '../modules/public-intake/types'

type FieldValue = string | string[]

function parentCountry(values: Record<string, FieldValue>, dependsOnField?: string): string | undefined {
  if (!dependsOnField) return undefined
  const raw = values[dependsOnField]
  const country = Array.isArray(raw) ? raw[0] : raw
  return country ? String(country) : undefined
}

export function useIntakeFieldOptions(
  field: FormPresentationField,
  values: Record<string, FieldValue>,
): CatalogOptionDto[] {
  const [loaded, setLoaded] = useState<CatalogOptionDto[]>([])
  const inlineOptions = field.options ?? []
  const domain = field.reference_domain || ''
  const countryCode = parentCountry(values, field.reference_meta?.depends_on_field)

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (inlineOptions.length > 0) {
        setLoaded(inlineOptions)
        return
      }
      if (!domain) {
        setLoaded([])
        return
      }
      try {
        let rows: CatalogOptionDto[] = []
        if (domain === 'countries') rows = await fetchCountryOptions()
        else if (domain === 'regions') rows = countryCode ? await fetchRegionOptions(countryCode) : []
        else if (domain === 'cities') rows = countryCode ? await fetchCityOptions(countryCode) : []
        else if (domain === 'professions') rows = await fetchProfessionOptions()
        else if (domain === 'services') rows = await fetchAdvertisedServiceOptions()
        if (!cancelled) setLoaded(rows)
      } catch {
        if (!cancelled) setLoaded([])
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [domain, countryCode, inlineOptions.length, field.qualified_code])

  return useMemo(() => {
    if (inlineOptions.length > 0) return inlineOptions
    return loaded
  }, [inlineOptions, loaded])
}
