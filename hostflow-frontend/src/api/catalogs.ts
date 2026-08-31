import { api } from './client'

export type CatalogOptionDto = {
  value: string
  label: string
  meta?: {
    label_ru?: string
    label_en?: string
    emoji?: string
    business_type?: string
    industry_hint?: string
    business_model?: string
    subtitle_ru?: string
    subtitle_en?: string
    launch_search_supported?: boolean
    country_code?: string
    code?: string
    name?: string
    dial_code?: string
    description_ru?: string
    description_en?: string
    enabled?: boolean
  }
}

export type CompanySetupCatalogsDto = {
  countries: CatalogOptionDto[]
  industries: CatalogOptionDto[]
  team_sizes: CatalogOptionDto[]
  platform_identities: CatalogOptionDto[]
  first_modules: CatalogOptionDto[]
  business_types: CatalogOptionDto[]
}

let companySetupCache: CompanySetupCatalogsDto | null = null
let companySetupInflight: Promise<CompanySetupCatalogsDto> | null = null
let companySetupFailure: unknown = null

export async function fetchCompanySetupCatalogs(): Promise<CompanySetupCatalogsDto> {
  if (companySetupCache) return companySetupCache
  if (companySetupFailure) return Promise.reject(companySetupFailure)
  if (companySetupInflight) return companySetupInflight
  companySetupInflight = api
    .get<CompanySetupCatalogsDto>('/catalogs/company-setup/options')
    .then(({ data }) => {
      companySetupCache = data
      companySetupFailure = null
      return data
    })
    .catch((err) => {
      companySetupFailure = err
      throw err
    })
    .finally(() => {
      companySetupInflight = null
    })
  return companySetupInflight
}

export async function fetchCityOptions(countryCode?: string): Promise<CatalogOptionDto[]> {
  const params = countryCode && countryCode !== 'OTHER' ? { country: countryCode } : undefined
  const { data } = await api.get<CatalogOptionDto[]>('/catalogs/cities/options', { params })
  return data ?? []
}

export async function fetchVacancyCategoryOptions(launchSearchOnly = true): Promise<CatalogOptionDto[]> {
  const { data } = await api.get<CatalogOptionDto[]>('/catalogs/vacancy-categories/options', {
    params: { launch_search_only: launchSearchOnly },
  })
  return data ?? []
}

export function invalidateCompanySetupCatalogsCache(): void {
  companySetupCache = null
  companySetupFailure = null
}
