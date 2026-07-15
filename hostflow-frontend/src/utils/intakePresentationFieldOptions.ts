import type { FormPresentationField } from '../modules/public-intake/types'
import type { LocaleCode } from '../i18n'
import { buildCountryOptions } from '../data/countries'

export type FieldOption = { value: string; label: string }

export type IntakeSectionKey = 'contact' | 'identity' | 'experience' | 'qualifications' | 'legal'

export const INTAKE_SECTION_ORDER: IntakeSectionKey[] = [
  'contact',
  'identity',
  'experience',
  'qualifications',
  'legal',
]

const SECTION_BY_CODE: Record<string, IntakeSectionKey> = {
  'recruitment.candidate.first_name': 'contact',
  'recruitment.candidate.last_name': 'contact',
  'recruitment.candidate.contacts.phone': 'contact',
  'recruitment.candidate.contacts.email': 'contact',
  'platform.identity.citizenship': 'identity',
  'platform.identity.birth_date': 'identity',
  'platform.identity.address': 'identity',
  'recruitment.candidate.personal.current_location': 'identity',
  'recruitment.candidate.experience.years_ce': 'experience',
  'recruitment.candidate.experience.years_similar_role': 'experience',
  'recruitment.candidate.experience.trailer_types[]': 'experience',
  'recruitment.candidate.experience.route_types[]': 'experience',
  'recruitment.candidate.qualifications.forklift_license': 'qualifications',
  'recruitment.candidate.qualifications.eu_license_with_code_95': 'qualifications',
  'recruitment.candidate.qualifications.tachograph_card': 'qualifications',
  'recruitment.candidate.personal.has_adr': 'qualifications',
  'recruitment.candidate.personal.residency_status': 'legal',
  'recruitment.candidate.personal.in_poland': 'legal',
}

const WIDGET_BY_CODE: Record<string, string> = {
  'recruitment.candidate.contacts.email': 'email',
  'recruitment.candidate.contacts.phone': 'phone',
  'platform.identity.birth_date': 'date',
  'platform.identity.citizenship': 'select',
  'recruitment.candidate.personal.current_location': 'select',
  'recruitment.candidate.personal.residency_status': 'select',
  'recruitment.candidate.experience.years_ce': 'select',
  'recruitment.candidate.experience.years_similar_role': 'select',
  'recruitment.candidate.experience.trailer_types[]': 'multiselect',
  'recruitment.candidate.qualifications.forklift_license': 'yes_no',
  'recruitment.candidate.qualifications.eu_license_with_code_95': 'yes_no',
  'recruitment.candidate.qualifications.tachograph_card': 'yes_no',
  'recruitment.candidate.personal.has_adr': 'yes_no',
  'recruitment.candidate.personal.in_poland': 'yes_no',
}

type TFn = (key: string, options?: { defaultValue?: string }) => string

function scopedOption(
  t: TFn,
  locale: LocaleCode,
  group: string,
  value: string,
  fallback: string,
): FieldOption {
  const key = `public.intake.presentation.options.${group}.${value}`
  const translated = t(key, { defaultValue: '' })
  if (translated && translated !== key) {
    return { value, label: translated }
  }
  return { value, label: fallback }
}

function optionGroup(
  t: TFn,
  locale: LocaleCode,
  group: string,
  values: string[],
  fallbacks: Record<string, string>,
): FieldOption[] {
  return values.map((value) => scopedOption(t, locale, group, value, fallbacks[value] ?? value))
}

export function sectionForField(qualifiedCode: string): IntakeSectionKey {
  return SECTION_BY_CODE[qualifiedCode] ?? 'identity'
}

export function resolveFieldWidget(field: Pick<FormPresentationField, 'qualified_code' | 'widget_hint' | 'field_type'>): string {
  const hint = String(field.widget_hint || '').trim()
  if (hint) return hint
  const code = String(field.qualified_code || '').trim()
  if (WIDGET_BY_CODE[code]) return WIDGET_BY_CODE[code]
  const fieldType = String(field.field_type || '').trim().toLowerCase()
  if (fieldType === 'email') return 'email'
  if (fieldType === 'phone_e164' || fieldType === 'phone') return 'phone'
  if (fieldType === 'boolean') return 'yes_no'
  if (fieldType === 'integer' || fieldType === 'number') return 'number'
  if (fieldType === 'date') return 'date'
  return 'text'
}

export function fieldOptionsForCode(
  qualifiedCode: string,
  t: TFn,
  locale: LocaleCode,
): FieldOption[] {
  const code = String(qualifiedCode || '').trim()

  if (code === 'platform.identity.citizenship') {
    return buildCountryOptions(locale)
  }

  if (code === 'recruitment.candidate.personal.current_location') {
    return optionGroup(t, locale, 'location', ['in_poland', 'not_in_poland', 'other'], {
      in_poland: 'In Poland',
      not_in_poland: 'Outside Poland',
      other: 'Other country',
    })
  }

  if (code === 'recruitment.candidate.personal.residency_status') {
    return optionGroup(t, locale, 'residency', ['visa', 'karta_pobytu', 'in_process', 'none', 'eu_citizen'], {
      visa: 'Visa',
      karta_pobytu: 'Residence card',
      in_process: 'Residence permit in process',
      none: 'No document yet',
      eu_citizen: 'EU citizen',
    })
  }

  if (
    code === 'recruitment.candidate.experience.years_ce' ||
    code === 'recruitment.candidate.experience.years_similar_role'
  ) {
    return optionGroup(t, locale, 'years', ['0', '1', '2', '3', '5', '10', '10+'], {
      '0': 'No experience',
      '1': '1 year',
      '2': '2 years',
      '3': '3 years',
      '5': '5 years',
      '10': '10 years',
      '10+': '10+ years',
    })
  }

  if (code === 'recruitment.candidate.experience.trailer_types[]') {
    return optionGroup(
      t,
      locale,
      'trailer_types',
      ['mega', 'standard', 'platform', 'frigo', 'tent', 'container', 'tandem', 'car_transporter'],
      {
        mega: 'Mega',
        standard: 'Standard curtain',
        platform: 'Platform',
        frigo: 'Refrigerated',
        tent: 'Tent',
        container: 'Container',
        tandem: 'Tandem',
        car_transporter: 'Car transporter',
      },
    )
  }

  if (
    code === 'recruitment.candidate.qualifications.forklift_license' ||
    code === 'recruitment.candidate.qualifications.eu_license_with_code_95' ||
    code === 'recruitment.candidate.qualifications.tachograph_card' ||
    code === 'recruitment.candidate.personal.has_adr' ||
    code === 'recruitment.candidate.personal.in_poland'
  ) {
    return optionGroup(t, locale, 'yes_no', ['yes', 'no'], { yes: 'Yes', no: 'No' })
  }

  return []
}

export function normalizeFieldValue(raw: unknown): string | string[] {
  if (Array.isArray(raw)) {
    return raw.map((item) => String(item).trim()).filter(Boolean)
  }
  if (raw === null || raw === undefined) return ''
  if (typeof raw === 'boolean') return raw ? 'yes' : 'no'
  return String(raw)
}

export function serializeValuesForApi(values: Record<string, string | string[]>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [key, raw] of Object.entries(values)) {
    if (Array.isArray(raw)) {
      out[key] = raw
      continue
    }
    const text = String(raw ?? '').trim()
    if (!text) continue
    if (text === 'yes') {
      out[key] = 'yes'
      continue
    }
    if (text === 'no') {
      out[key] = 'no'
      continue
    }
    out[key] = text
  }
  return out
}

export function isEmptyFieldValue(value: string | string[] | undefined): boolean {
  if (value === undefined || value === null) return true
  if (Array.isArray(value)) return value.length === 0
  return !String(value).trim()
}
