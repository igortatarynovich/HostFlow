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

export async function fetchCompanySetupCatalogs(): Promise<CompanySetupCatalogsDto> {
  if (companySetupCache) return companySetupCache
  if (companySetupInflight) return companySetupInflight
  companySetupInflight = api
    .get<CompanySetupCatalogsDto>('/catalogs/company-setup/options')
    .then(({ data }) => {
      companySetupCache = data
      return data
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

export async function fetchRegionOptions(countryCode?: string): Promise<CatalogOptionDto[]> {
  const params = countryCode && countryCode !== 'OTHER' ? { country: countryCode } : undefined
  const { data } = await api.get<CatalogOptionDto[]>('/catalogs/regions/options', { params })
  return data ?? []
}

export async function fetchProfessionOptions(): Promise<CatalogOptionDto[]> {
  const { data } = await api.get<CatalogOptionDto[]>('/catalogs/professions/options')
  return data ?? []
}

export async function fetchAdvertisedServiceOptions(): Promise<CatalogOptionDto[]> {
  const { data } = await api.get<CatalogOptionDto[]>('/catalogs/services/options')
  return data ?? []
}

export async function fetchCountryOptions(): Promise<CatalogOptionDto[]> {
  const { data } = await api.get<CatalogOptionDto[]>('/catalogs/countries/options')
  return data ?? []
}

export function invalidateCompanySetupCatalogsCache(): void {
  companySetupCache = null
}
