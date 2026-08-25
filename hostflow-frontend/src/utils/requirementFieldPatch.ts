import type { Candidate } from '../api/types'
import { makeAddress } from '../modules/candidate-card/utils'
import { legacyFieldKeyFromQualifiedCode } from './fieldLayoutUtils'

export type RequirementFieldInputKind =
  | 'text'
  | 'email'
  | 'phone'
  | 'number'
  | 'date'
  | 'country'
  | 'address_line'

const QUALIFIED_INPUT_KIND: Record<string, RequirementFieldInputKind> = {
  'recruitment.candidate.contacts.email': 'email',
  'recruitment.candidate.contacts.phone': 'phone',
  'platform.identity.citizenship': 'country',
  'platform.identity.birth_date': 'date',
  'platform.identity.address': 'address_line',
  'recruitment.candidate.experience.years_ce': 'number',
}

export function requirementFieldInputKind(qualifiedCode: string): RequirementFieldInputKind {
  return QUALIFIED_INPUT_KIND[qualifiedCode] || 'text'
}

export function formatAddressDisplay(value: unknown): string {
  if (!value) return ''
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'object') {
    const address = makeAddress(value as Record<string, string>)
    const parts = [
      [address.street, address.house].filter(Boolean).join(' '),
      address.apt,
      [address.zip, address.city].filter(Boolean).join(' '),
      address.country,
    ].filter(Boolean)
    return parts.join(', ')
  }
  return String(value).trim()
}

export function readRequirementFieldValue(candidate: Candidate, qualifiedCode: string): string {
  const extra = candidate.extra || {}

  switch (qualifiedCode) {
    case 'recruitment.candidate.first_name':
      return String(candidate.first_name || '').trim()
    case 'recruitment.candidate.last_name':
      return String(candidate.last_name || '').trim()
    case 'recruitment.candidate.contacts.phone':
      return String(candidate.phone || '').trim()
    case 'recruitment.candidate.contacts.email':
      return String(candidate.email || '').trim()
    case 'platform.identity.citizenship':
      return String(extra.citizenship || '').trim()
    case 'platform.identity.birth_date':
      return String(extra.birth_date || candidate.birth_date || '').slice(0, 10)
    case 'platform.identity.address':
      return formatAddressDisplay(extra.address || (candidate as { address?: unknown }).address)
    case 'recruitment.candidate.experience.years_ce': {
      const raw = extra.experience_eu_years ?? (extra as { years_ce?: unknown }).years_ce
      if (raw == null || raw === '') return ''
      const num = Number(raw)
      return Number.isFinite(num) ? String(num) : String(raw).trim()
    }
    default: {
      const key = legacyFieldKeyFromQualifiedCode(qualifiedCode)
      const top = (candidate as Record<string, unknown>)[key]
      if (top != null && typeof top !== 'object') return String(top).trim()
      const fromExtra = (extra as Record<string, unknown>)[key]
      if (fromExtra != null && typeof fromExtra !== 'object') return String(fromExtra).trim()
      return ''
    }
  }
}

export function buildRequirementFieldPatch(
  qualifiedCode: string,
  rawValue: string,
  candidate: Candidate,
): Record<string, unknown> {
  const value = rawValue.trim()
  const extra = { ...(candidate.extra || {}) }

  switch (qualifiedCode) {
    case 'recruitment.candidate.first_name':
      return { first_name: value }
    case 'recruitment.candidate.last_name':
      return { last_name: value }
    case 'recruitment.candidate.contacts.phone':
      return { phone: value }
    case 'recruitment.candidate.contacts.email':
      return { email: value || null }
    case 'platform.identity.citizenship':
      return {
        extra: { ...extra, citizenship: value || null },
        personal_data: { citizenship: value || null },
      }
    case 'platform.identity.birth_date':
      return {
        birth_date: value || null,
        extra: { ...extra, birth_date: value || null },
      }
    case 'platform.identity.address': {
      const current = makeAddress(extra.address)
      const nextAddress = value.includes(',')
        ? value
        : {
            ...current,
            street: value || current.street,
          }
      const patch: Record<string, unknown> = {
        extra: { ...extra, address: nextAddress },
        personal_data: { address: nextAddress },
      }
      if (typeof nextAddress === 'object' && nextAddress) {
        patch.address = nextAddress
        if (nextAddress.city) patch.city = nextAddress.city
        if (nextAddress.country) patch.country_code = nextAddress.country
      }
      return patch
    }
    case 'recruitment.candidate.experience.years_ce': {
      const parsed = value === '' ? null : Number(value)
      const years = parsed != null && Number.isFinite(parsed) ? parsed : null
      return {
        extra: {
          ...extra,
          experience_eu_years: years,
          years_ce: years,
        },
      }
    }
    default: {
      const key = legacyFieldKeyFromQualifiedCode(qualifiedCode)
      if (['first_name', 'last_name', 'phone', 'email', 'birth_date'].includes(key)) {
        return { [key]: value || null }
      }
      return { extra: { ...extra, [key]: value || null } }
    }
  }
}

export function requirementFieldLabelKey(qualifiedCode: string): string {
  const tail = qualifiedCode.split('.').pop()?.replace('[]', '') || qualifiedCode
  return `app.candidate_card.fields.${tail}`
}
