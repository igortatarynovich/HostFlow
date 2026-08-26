import type { OwnCompanyRecord } from '../../api/client'

export type OwnCompanyProfileTab =
  | 'overview'
  | 'requisites'
  | 'bank'
  | 'documents'
  | 'contacts'
  | 'related'
  | 'history'

export const OWN_COMPANY_PROFILE_TABS: OwnCompanyProfileTab[] = [
  'overview',
  'requisites',
  'bank',
  'documents',
  'contacts',
  'related',
  'history',
]

export type OwnCompanyBankAccount = {
  label: string
  bank_name: string
  iban: string
  swift_bic: string
  currency: string
  country: string
  is_primary: boolean
}

export type OwnCompanyContact = {
  full_name: string
  role: string
  email: string
  phone: string
  is_primary: boolean
}

export function parseOwnCompanyProfileTab(raw: string | null | undefined): OwnCompanyProfileTab {
  const value = String(raw || '')
    .trim()
    .toLowerCase()
  return OWN_COMPANY_PROFILE_TABS.includes(value as OwnCompanyProfileTab)
    ? (value as OwnCompanyProfileTab)
    : 'overview'
}

export function companyInitials(name: string): string {
  const parts = String(name || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
  if (!parts.length) return 'HF'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0] || ''}${parts[1][0] || ''}`.toUpperCase()
}

export function asRecord(value: unknown): Record<string, any> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, any>) : {}
}

function text(value: unknown): string {
  return String(value ?? '').trim()
}

export function resolveBusinessType(company: OwnCompanyRecord): string {
  const extra = asRecord(company.extra)
  return text(extra.business_type || extra.company_type || extra.company_kind)
}

export function resolveIndustry(company: OwnCompanyRecord): string {
  return text(asRecord(company.extra).industry)
}

export function resolveRegon(company: OwnCompanyRecord): string {
  const extra = asRecord(company.extra)
  return text(extra.regon || extra.REGON)
}

export function resolveVatEu(company: OwnCompanyRecord): string {
  const extra = asRecord(company.extra)
  return text(extra.vat_eu || extra.vat_number || extra.eu_vat)
}

export function resolveLogoUrl(company: OwnCompanyRecord): string {
  const extra = asRecord(company.extra)
  const branding = asRecord(extra.branding)
  return text(branding.logo_url || extra.logo_url)
}

export function resolveBrandColors(company: OwnCompanyRecord): { primary: string; secondary: string } {
  const extra = asRecord(company.extra)
  const branding = asRecord(extra.branding)
  return {
    primary: text(branding.primary_color || extra.primary_color),
    secondary: text(branding.secondary_color || extra.secondary_color),
  }
}

export function resolveBrandDomain(company: OwnCompanyRecord): string {
  const extra = asRecord(company.extra)
  const branding = asRecord(extra.branding)
  return text(branding.domain || extra.domain || company.website)
}

export function resolveBankAccounts(company: OwnCompanyRecord): OwnCompanyBankAccount[] {
  const bd = asRecord(company.bank_details)
  const list = Array.isArray(bd.bank_accounts) ? bd.bank_accounts : []
  const fromList = list
    .filter((item): item is Record<string, any> => Boolean(item) && typeof item === 'object')
    .map((item) => ({
      label: text(item.label || item.name),
      bank_name: text(item.bank_name || item.bank),
      iban: text(item.iban || item.account_number),
      swift_bic: text(item.swift_bic || item.swift),
      currency: text(item.currency || 'PLN'),
      country: text(item.country),
      is_primary: Boolean(item.is_primary),
    }))
    .filter((item) => item.iban || item.bank_name || item.label)

  if (fromList.length) return fromList

  const iban = text(bd.iban)
  if (!iban && !text(bd.bank_name)) return []
  return [
    {
      label: text(bd.label) || 'Primary',
      bank_name: text(bd.bank_name),
      iban,
      swift_bic: text(bd.swift_bic || bd.swift),
      currency: text(bd.currency || 'PLN'),
      country: text(bd.country),
      is_primary: true,
    },
  ]
}

export function resolveContacts(company: OwnCompanyRecord): OwnCompanyContact[] {
  const raw = company.contacts
  const list = Array.isArray(raw)
    ? raw
    : Array.isArray(asRecord(raw).items)
      ? asRecord(raw).items
      : Object.values(asRecord(raw)).filter((item) => item && typeof item === 'object')

  return list
    .filter((item): item is Record<string, any> => Boolean(item) && typeof item === 'object')
    .map((item) => ({
      full_name: text(item.full_name || item.name),
      role: text(item.role || item.title),
      email: text(item.email),
      phone: text(item.phone),
      is_primary: Boolean(item.is_primary),
    }))
    .filter((item) => item.full_name || item.email || item.phone)
}

export function formatLocation(company: OwnCompanyRecord): string {
  return [company.city, company.country || company.country_code].map(text).filter(Boolean).join(', ')
}

export function formatLegalAddress(company: OwnCompanyRecord): string {
  return [company.address, company.city, company.country || company.country_code].map(text).filter(Boolean).join(', ')
}
