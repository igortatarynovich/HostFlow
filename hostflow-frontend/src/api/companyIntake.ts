import http from './http'

export type CompanyIntakeCompany = {
  name: string
  legal_name?: string | null
  tax_id?: string | null
  country?: string | null
  country_code?: string | null
  city?: string | null
  address?: string | null
  website?: string | null
  fleet_size?: number | null
  transport_type?: 'international' | 'domestic' | 'mixed' | null
}

export type CompanyIntakeContact = {
  full_name: string
  role?: string | null
  email?: string | null
  phone?: string | null
  whatsapp?: boolean | null
}

export type CompanyIntakeNeed = {
  what_needed?: string | null
  people_count?: number | null
  needed_when?: string | null
  cooperation_type?: string | null
  candidate_countries?: string[]
  requirements?: string | null
}

export type CompanyIntakeTerms = {
  rate?: string | null
  rate_amount?: string | null
  rate_currency?: string | null
  rate_period?: string | null
  rate_tax_mode?: string | null
  bonus?: string | null
  schedule?: string | null
  work_systems?: string[]
  route_directions?: string[]
  cargo_types?: string[]
  work_conditions?: string[]
  base_location?: string | null
  truck_brands?: string[]
  body_type?: string | null
  additional?: string | null
}

export type CompanyIntakeConsent = {
  terms_accepted: boolean
  privacy_accepted: boolean
  data_processing_accepted: boolean
  accuracy_confirmed: boolean
  marketing_contact_accepted?: boolean
  terms_version?: string | null
  privacy_version?: string | null
}

export type CompanyIntakeSubmitPayload = {
  company: CompanyIntakeCompany
  contact: CompanyIntakeContact
  need?: CompanyIntakeNeed
  terms?: CompanyIntakeTerms
  consent?: CompanyIntakeConsent
  source?: string | null
  service_intent?: string | null
  language?: string | null
  source_context?: Record<string, unknown> | null
  turnstile_token?: string | null
}

export type CompanyIntakeSubmitResponse = {
  lead_id: string
  status: string
  stage: string
  own_company_id: string
  company_id?: string | null
  duplicate: boolean
  lead_url: string
}

export async function submitCompanyIntake(
  publicToken: string,
  payload: CompanyIntakeSubmitPayload,
): Promise<CompanyIntakeSubmitResponse> {
  const { data } = await http.post<CompanyIntakeSubmitResponse>(
    `/public/company-intake/${encodeURIComponent(publicToken)}/submit`,
    payload,
  )
  return data
}
