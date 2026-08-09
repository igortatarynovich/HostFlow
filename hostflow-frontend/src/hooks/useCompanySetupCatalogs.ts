import { useEffect, useMemo, useRef, useState } from 'react'
import {
  fetchCompanySetupCatalogs,
  type CatalogOptionDto,
  type CompanySetupCatalogsDto,
} from '../api/catalogs'
import {
  FIRST_MODULE_OPTIONS,
  INDUSTRY_OPTIONS,
  PLATFORM_IDENTITY_OPTIONS,
  TEAM_SIZE_OPTIONS,
  type CompanyActivityOption,
  type FirstModuleOption,
  type IndustryOption,
  type TeamSizeOption,
} from '../constants/companySetupCatalog'
import { buildCountryOptions } from '../data/countries'
import { withOtherCountryOption } from '../utils/catalogOptions'

function fallbackCompanySetup(locale?: string): CompanySetupCatalogsDto {
  const isRu = locale?.startsWith('ru')
  const countries = withOtherCountryOption(
    buildCountryOptions(locale).map((row) => ({
      value: row.value,
      label: row.label,
      meta: { label_ru: row.label, label_en: row.label },
    })),
    locale,
  )
  return {
    countries,
    industries: INDUSTRY_OPTIONS.map((row) => ({
      value: row.id,
      label: isRu ? row.labelRu : row.labelEn,
      meta: { label_ru: row.labelRu, label_en: row.labelEn },
    })),
    team_sizes: TEAM_SIZE_OPTIONS.map((row) => ({
      value: row.id,
      label: isRu ? row.labelRu : row.labelEn,
      meta: { label_ru: row.labelRu, label_en: row.labelEn },
    })),
    platform_identities: PLATFORM_IDENTITY_OPTIONS.map((row) => ({
      value: row.id,
      label: isRu ? row.labelRu : row.labelEn,
      meta: {
        label_ru: row.labelRu,
        label_en: row.labelEn,
        emoji: row.emoji,
        business_type: row.business_type,
        industry_hint: row.industry_hint,
        business_model: row.business_model,
      },
    })),
    first_modules: FIRST_MODULE_OPTIONS.map((row) => ({
      value: row.id,
      label: isRu ? row.labelRu : row.labelEn,
      meta: {
        label_ru: row.labelRu,
        label_en: row.labelEn,
        emoji: row.emoji,
        description_ru: row.descriptionRu,
        description_en: row.descriptionEn,
        enabled: row.enabled,
      },
    })),
    business_types: [],
  }
}

export function useCompanySetupCatalogs(locale?: string) {
  const fallback = useMemo(() => fallbackCompanySetup(locale), [locale])
  const [catalogs, setCatalogs] = useState<CompanySetupCatalogsDto>(fallback)
  const [loading, setLoading] = useState(true)
  const fetchedForLocale = useRef<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const localeKey = locale ?? ''
    // One attempt per locale — prevents retry storms when the catalog API fails.
    if (fetchedForLocale.current === localeKey) {
      setLoading(false)
      return
    }
    setLoading(true)
    void fetchCompanySetupCatalogs()
      .then((data) => {
        if (cancelled) return
        fetchedForLocale.current = localeKey
        setCatalogs({
          ...data,
          countries: withOtherCountryOption(data.countries ?? fallback.countries, locale),
        })
      })
      .catch(() => {
        if (cancelled) return
        fetchedForLocale.current = localeKey
        setCatalogs(fallback)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [fallback, locale])

  return { catalogs, loading }
}

export function resolvePlatformIdentityFromCatalog(
  id: string,
  options: CatalogOptionDto[],
): CompanyActivityOption {
  const match = options.find((row) => row.value === id)
  if (!match) return PLATFORM_IDENTITY_OPTIONS[0]
  const meta = match.meta ?? {}
  return {
    id: match.value as CompanyActivityOption['id'],
    emoji: String(meta.emoji ?? '💼'),
    labelRu: String(meta.label_ru ?? match.label),
    labelEn: String(meta.label_en ?? match.label),
    business_type: (meta.business_type as CompanyActivityOption['business_type']) ?? 'employer',
    industry_hint: meta.industry_hint as IndustryOption['id'] | undefined,
    business_model: String(meta.business_model ?? match.value),
  }
}

export function resolveFirstModuleFromCatalog(
  id: string,
  options: CatalogOptionDto[],
): FirstModuleOption {
  const match = options.find((row) => row.value === id)
  if (!match) return FIRST_MODULE_OPTIONS[0]
  const meta = match.meta ?? {}
  return {
    id: match.value as FirstModuleOption['id'],
    emoji: String(meta.emoji ?? '🔍'),
    labelRu: String(meta.label_ru ?? match.label),
    labelEn: String(meta.label_en ?? match.label),
    descriptionRu: String(meta.description_ru ?? ''),
    descriptionEn: String(meta.description_en ?? ''),
    enabled: Boolean(meta.enabled),
  }
}

export type { IndustryOption, TeamSizeOption, CompanyActivityOption, FirstModuleOption }
