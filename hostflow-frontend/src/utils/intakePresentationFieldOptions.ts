import type { FormPresentationField } from '../modules/public-intake/types'
import { lookupScopedTranslation, type LocaleCode } from '../i18n'
import { buildCountryOptions } from '../data/countries'
import {
  driverHiringFieldSuffix,
  driverHiringOptionsForSuffix,
} from './driverHiringFieldOptions'
import {
  warehouseHiringFieldSuffix,
  warehouseHiringOptionsForSuffix,
} from './warehouseHiringFieldOptions'

export type FieldOption = { value: string; label: string }

export const SERVICE_SALES_QUESTIONNAIRE_PREFIX = 'service_sales.targeted_advertising.'

export type PresentationFieldValue = string | string[]

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
  // Prefer the requested locale (submission / public form), not the CRM UI language.
  const scoped = lookupScopedTranslation(locale, `public.intake.presentation.options.${group}`, value)
  if (scoped) return { value, label: scoped }
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
  if (fieldType === 'single_select') return 'single_select'
  if (fieldType === 'multi_select') return 'multi_select'
  if (fieldType === 'textarea') return 'textarea'
  return 'text'
}

function salesQuestionnaireFieldSuffix(qualifiedCode: string): string | null {
  const code = String(qualifiedCode || '').trim()
  if (!code.startsWith(SERVICE_SALES_QUESTIONNAIRE_PREFIX)) return null
  return code.slice(SERVICE_SALES_QUESTIONNAIRE_PREFIX.length)
}

function salesQuestionnaireOptions(t: TFn, locale: LocaleCode, suffix: string): FieldOption[] {
  const pl = (value: string, label: string) => scopedOption(t, locale, `service_sales.${suffix}`, value, label)

  switch (suffix) {
    case 'need_type':
      return [
        pl('employee_recruitment', 'Hiring employees'),
        pl('client_acquisition', 'Finding clients'),
        pl('product_sales', 'Product sales'),
        pl('service_promotion', 'Service promotion'),
      ]
    case 'primary_outcome':
      return [
        pl('more_inquiries', 'More client inquiries'),
        pl('more_applications', 'More candidate applications'),
        pl('more_sales', 'More sales'),
        pl('brand_awareness', 'Greater brand awareness'),
        pl('other', 'Other result'),
      ]
    case 'recruitment_roles':
      return [
        pl('driver_ce', 'C+E driver'),
        pl('driver_c', 'C driver'),
        pl('warehouse', 'Warehouse worker'),
        pl('mechanic', 'Mechanic'),
        pl('dispatcher', 'Dispatcher'),
        pl('other', 'Other role'),
      ]
    case 'recruitment_headcount':
      return [
        pl('1_3', '1–3 people'),
        pl('4_10', '4–10 people'),
        pl('11_20', '11–20 people'),
        pl('21_50', '21–50 people'),
        pl('50_plus', 'More than 50 people'),
      ]
    case 'work_location_country':
      return [
        pl('poland', 'Poland'),
        pl('germany', 'Germany'),
        pl('other_eu', 'Other EU country'),
        pl('other', 'Other country'),
      ]
    case 'application_channel':
      return [
        pl('phone', 'Phone'),
        pl('whatsapp', 'WhatsApp'),
        pl('form', 'Online form'),
        pl('email', 'Email'),
      ]
    case 'job_posting_ready':
      return [
        pl('ready', 'Yes, the posting is ready'),
        pl('partial', 'Partially prepared'),
        pl('need_help', 'We need help'),
      ]
    case 'recruitment_materials':
      return [
        pl('photos', 'Photos'),
        pl('logo', 'Company logo'),
        pl('job_description', 'Job description'),
        pl('video', 'Video'),
        pl('none', 'No materials'),
      ]
    case 'promotion_subject':
      return [
        pl('service', 'Service'),
        pl('product', 'Product'),
        pl('company_brand', 'Company brand'),
      ]
    case 'industry':
      return [
        pl('transport', 'Transport and logistics'),
        pl('logistics', 'Freight forwarding'),
        pl('construction', 'Construction'),
        pl('manufacturing', 'Manufacturing'),
        pl('services', 'Services'),
        pl('other', 'Other industry'),
      ]
    case 'client_geo_scope':
      return [
        pl('poland', 'All of Poland'),
        pl('single_city', 'One city'),
        pl('selected_region', 'Selected region'),
        pl('europe', 'Europe'),
        pl('international', 'International'),
      ]
    case 'conversion_destination':
      return [
        pl('whatsapp', 'WhatsApp'),
        pl('phone', 'Phone'),
        pl('form', 'Website form'),
        pl('website', 'Website'),
        pl('messenger', 'Messenger'),
      ]
    case 'offer_ready':
      return [
        pl('ready', 'Yes, the offer is ready'),
        pl('partial', 'Partially prepared'),
        pl('need_help', 'We need help'),
      ]
    case 'marketing_materials':
      return [
        pl('photos', 'Photos'),
        pl('logo', 'Company logo'),
        pl('video', 'Video'),
        pl('catalog', 'Catalog / price list'),
        pl('none', 'No materials'),
      ]
    case 'prior_ads_experience':
      return optionGroup(t, locale, 'yes_no', ['yes', 'no'], { yes: 'Yes', no: 'No' })
    case 'monthly_ad_budget':
      return [
        pl('under_1000', 'Up to 1,000 PLN'),
        pl('1000_2000', '1,000 – 2,000 PLN'),
        pl('2000_5000', '2,000 – 5,000 PLN'),
        pl('5000_10000', '5,000 – 10,000 PLN'),
        pl('over_10000', 'Over 10,000 PLN'),
        pl('undecided', 'Not decided yet'),
      ]
    case 'start_timeline':
      return [
        pl('asap', 'As soon as possible'),
        pl('two_weeks', 'Within 2 weeks'),
        pl('one_month', 'Within a month'),
        pl('later', 'Later'),
        pl('undecided', 'Not decided yet'),
      ]
    case 'decision_maker':
      return [
        pl('owner', 'Company owner'),
        pl('manager', 'Manager'),
        pl('marketing', 'Marketing person'),
        pl('other', 'Someone else'),
      ]
    default:
      return []
  }
}

export function fieldOptionsForCode(
  qualifiedCode: string,
  t: TFn,
  locale: LocaleCode,
): FieldOption[] {
  const code = String(qualifiedCode || '').trim()
  const salesSuffix = salesQuestionnaireFieldSuffix(code)
  if (salesSuffix) {
    return salesQuestionnaireOptions(t, locale, salesSuffix)
  }
  const hiringSuffix = driverHiringFieldSuffix(code)
  if (hiringSuffix) {
    return driverHiringOptionsForSuffix(t, locale, hiringSuffix)
  }
  const warehouseSuffix = warehouseHiringFieldSuffix(code)
  if (warehouseSuffix) {
    return warehouseHiringOptionsForSuffix(t, locale, warehouseSuffix)
  }

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

  if (code === 'recruitment.candidate.experience.route_types[]') {
    return optionGroup(t, locale, 'route_types', ['eu', 'cis', 'uk', 'scandi', 'local'], {
      eu: 'EU',
      cis: 'CIS',
      uk: 'United Kingdom',
      scandi: 'Scandinavia',
      local: 'Local',
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

export function normalizeFieldValue(raw: unknown): PresentationFieldValue {
  if (Array.isArray(raw)) {
    return raw.map((item) => String(item).trim()).filter(Boolean)
  }
  if (raw === null || raw === undefined) return ''
  if (typeof raw === 'boolean') return raw ? 'yes' : 'no'
  return String(raw)
}

export function serializeValuesForApi(values: Record<string, PresentationFieldValue>): Record<string, unknown> {
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

export function isEmptyFieldValue(value: PresentationFieldValue | undefined): boolean {
  if (value === undefined || value === null) return true
  if (Array.isArray(value)) return value.length === 0
  return !String(value).trim()
}
