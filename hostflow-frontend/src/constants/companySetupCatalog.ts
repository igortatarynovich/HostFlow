export type BusinessType = 'agency' | 'employer' | 'services'

export type IndustryKey =
  | 'transport_logistics'
  | 'manufacturing'
  | 'construction'
  | 'retail'
  | 'horeca'
  | 'it'
  | 'healthcare'
  | 'finance'
  | 'other'

export type TeamSizeKey = 'solo' | '2_10' | '11_50' | '51_250' | '251_1000' | '1000_plus'

export type CompanyActivityKey =
  | 'recruitment_agency'
  | 'transport_company'
  | 'manufacturing_company'
  | 'construction_company'
  | 'logistics_operator'
  | 'cleaning_services'
  | 'horeca_business'
  | 'healthcare_business'
  | 'other'

export type FirstModuleKey = 'recruitment' | 'hr' | 'fleet' | 'orders' | 'explore'

export type IndustryOption = {
  id: IndustryKey
  labelRu: string
  labelEn: string
}

export type TeamSizeOption = {
  id: TeamSizeKey
  labelRu: string
  labelEn: string
}

export type CompanyActivityOption = {
  id: CompanyActivityKey
  emoji: string
  labelRu: string
  labelEn: string
  business_type: BusinessType
  /** Suggested industry when user has not picked a closer match */
  industry_hint?: IndustryKey
  business_model: string
}

export type FirstModuleOption = {
  id: FirstModuleKey
  emoji: string
  labelRu: string
  labelEn: string
  descriptionRu: string
  descriptionEn: string
  enabled: boolean
}

export const INDUSTRY_OPTIONS: IndustryOption[] = [
  { id: 'transport_logistics', labelRu: 'Транспорт и логистика', labelEn: 'Transport & logistics' },
  { id: 'manufacturing', labelRu: 'Производство', labelEn: 'Manufacturing' },
  { id: 'construction', labelRu: 'Строительство', labelEn: 'Construction' },
  { id: 'retail', labelRu: 'Розничная торговля', labelEn: 'Retail' },
  { id: 'horeca', labelRu: 'HoReCa', labelEn: 'HoReCa' },
  { id: 'it', labelRu: 'IT', labelEn: 'IT' },
  { id: 'healthcare', labelRu: 'Медицина', labelEn: 'Healthcare' },
  { id: 'finance', labelRu: 'Финансы', labelEn: 'Finance' },
  { id: 'other', labelRu: 'Другое', labelEn: 'Other' },
]

export const TEAM_SIZE_OPTIONS: TeamSizeOption[] = [
  { id: 'solo', labelRu: 'Только я', labelEn: 'Just me' },
  { id: '2_10', labelRu: '2–10', labelEn: '2–10' },
  { id: '11_50', labelRu: '11–50', labelEn: '11–50' },
  { id: '51_250', labelRu: '51–250', labelEn: '51–250' },
  { id: '251_1000', labelRu: '251–1000', labelEn: '251–1000' },
  { id: '1000_plus', labelRu: 'Более 1000', labelEn: '1000+' },
]

/** Platform identity — human question «Что описывает ваш бизнес?» */
export const PLATFORM_IDENTITY_OPTIONS: CompanyActivityOption[] = [
  {
    id: 'recruitment_agency',
    emoji: '👥',
    labelRu: 'Кадровое агентство',
    labelEn: 'Recruitment agency',
    business_type: 'agency',
    industry_hint: 'transport_logistics',
    business_model: 'recruitment_agency',
  },
  {
    id: 'transport_company',
    emoji: '🚛',
    labelRu: 'Транспортная компания',
    labelEn: 'Transport company',
    business_type: 'employer',
    industry_hint: 'transport_logistics',
    business_model: 'transport_company',
  },
  {
    id: 'manufacturing_company',
    emoji: '🏭',
    labelRu: 'Производственная компания',
    labelEn: 'Manufacturing company',
    business_type: 'employer',
    industry_hint: 'manufacturing',
    business_model: 'manufacturing_company',
  },
  {
    id: 'construction_company',
    emoji: '🏗️',
    labelRu: 'Строительство',
    labelEn: 'Construction',
    business_type: 'employer',
    industry_hint: 'construction',
    business_model: 'construction_company',
  },
  {
    id: 'cleaning_services',
    emoji: '🧹',
    labelRu: 'Клининг',
    labelEn: 'Cleaning services',
    business_type: 'services',
    industry_hint: 'other',
    business_model: 'cleaning_services',
  },
  {
    id: 'horeca_business',
    emoji: '🍽️',
    labelRu: 'Ресторан / HoReCa',
    labelEn: 'Restaurant / HoReCa',
    business_type: 'employer',
    industry_hint: 'horeca',
    business_model: 'horeca',
  },
  {
    id: 'healthcare_business',
    emoji: '🏥',
    labelRu: 'Медицина',
    labelEn: 'Healthcare',
    business_type: 'employer',
    industry_hint: 'healthcare',
    business_model: 'healthcare',
  },
  {
    id: 'other',
    emoji: '💼',
    labelRu: 'Другое',
    labelEn: 'Other',
    business_type: 'employer',
    industry_hint: 'other',
    business_model: 'other',
  },
]

/** @deprecated use PLATFORM_IDENTITY_OPTIONS */
export const COMPANY_ACTIVITY_OPTIONS = PLATFORM_IDENTITY_OPTIONS.filter((o) =>
  ['recruitment_agency', 'transport_company', 'manufacturing_company', 'construction_company', 'logistics_operator', 'other'].includes(o.id),
)

export const FIRST_MODULE_OPTIONS: FirstModuleOption[] = [
  {
    id: 'recruitment',
    emoji: '🔍',
    labelRu: 'Найти сотрудников',
    labelEn: 'Find employees',
    descriptionRu: 'Вакансии, кандидаты, источники',
    descriptionEn: 'Vacancies, candidates, sources',
    enabled: true,
  },
  {
    id: 'hr',
    emoji: '👤',
    labelRu: 'Управлять сотрудниками',
    labelEn: 'Manage employees',
    descriptionRu: 'Кадры, документы, отпуска',
    descriptionEn: 'HR, documents, time off',
    enabled: false,
  },
  {
    id: 'fleet',
    emoji: '🚛',
    labelRu: 'Управлять транспортом',
    labelEn: 'Manage fleet',
    descriptionRu: 'Автопарк, водители, рейсы',
    descriptionEn: 'Vehicles, drivers, trips',
    enabled: false,
  },
  {
    id: 'orders',
    emoji: '📋',
    labelRu: 'Управлять заказами',
    labelEn: 'Manage orders',
    descriptionRu: 'Клиенты, заказы, услуги',
    descriptionEn: 'Clients, orders, services',
    enabled: false,
  },
  {
    id: 'explore',
    emoji: '👀',
    labelRu: 'Просто посмотреть систему',
    labelEn: 'Just explore',
    descriptionRu: 'Ознакомительный режим',
    descriptionEn: 'Look around first',
    enabled: false,
  },
]

export type CountryOption = {
  code: string
  labelRu: string
  labelEn: string
}

export const COUNTRY_OPTIONS: CountryOption[] = [
  { code: 'PL', labelRu: 'Польша', labelEn: 'Poland' },
  { code: 'DE', labelRu: 'Германия', labelEn: 'Germany' },
  { code: 'UA', labelRu: 'Украина', labelEn: 'Ukraine' },
  { code: 'LT', labelRu: 'Литва', labelEn: 'Lithuania' },
  { code: 'CZ', labelRu: 'Чехия', labelEn: 'Czechia' },
  { code: 'SK', labelRu: 'Словакия', labelEn: 'Slovakia' },
  { code: 'GB', labelRu: 'Великобритания', labelEn: 'United Kingdom' },
  { code: 'US', labelRu: 'США', labelEn: 'United States' },
  { code: 'OTHER', labelRu: 'Другая страна', labelEn: 'Other country' },
]

export function resolveCompanyActivity(id: CompanyActivityKey): CompanyActivityOption {
  return PLATFORM_IDENTITY_OPTIONS.find((o) => o.id === id) ?? PLATFORM_IDENTITY_OPTIONS[0]
}
