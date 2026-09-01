import type { LocaleCode } from '../i18n'
import { lookupScopedTranslation } from '../i18n'

export const DRIVER_HIRING_QUESTIONNAIRE_PREFIX = 'service_sales.driver_hiring.'

type TFn = (key: string, options?: { defaultValue?: string }) => string
export type FieldOption = { value: string; label: string }

type OptionSpec = { values: string[]; fallbacks: Record<string, string> }

const YES_NO: OptionSpec = {
  values: ['yes', 'no'],
  fallbacks: { yes: 'Yes', no: 'No' },
}

const YES_NO_SOMETIMES: OptionSpec = {
  values: ['no', 'sometimes', 'yes'],
  fallbacks: { no: 'No', sometimes: 'Sometimes', yes: 'Yes' },
}

const YES_NO_INDIVIDUAL: OptionSpec = {
  values: ['yes', 'no', 'individual'],
  fallbacks: { yes: 'Yes', no: 'No', individual: 'Case by case' },
}

const YES_NO_PARTIAL: OptionSpec = {
  values: ['yes', 'partial', 'no'],
  fallbacks: { yes: 'Yes, in full', partial: 'Partially', no: 'No' },
}

const CURRENCY: OptionSpec = {
  values: ['pln', 'eur'],
  fallbacks: { pln: 'PLN', eur: 'EUR' },
}

export const DRIVER_HIRING_OPTIONS: Record<string, OptionSpec> = {
  driver_categories: {
    values: ['c', 'ce', 'd', 'other'],
    fallbacks: { c: 'C', ce: 'C+E', d: 'D', other: 'Other' },
  },
  first_drivers_when: {
    values: ['asap', 'within_2_weeks', 'within_month', '1_3_months', 'ongoing'],
    fallbacks: {
      asap: 'As soon as possible',
      within_2_weeks: 'Within 2 weeks',
      within_month: 'Within a month',
      '1_3_months': '1–3 months',
      ongoing: 'Ongoing hiring',
    },
  },
  monthly_hire_plan: {
    values: ['1_2', '3_5', '6_10', '11_20', '20_plus', 'unknown'],
    fallbacks: {
      '1_2': '1–2',
      '3_5': '3–5',
      '6_10': '6–10',
      '11_20': '11–20',
      '20_plus': 'More than 20',
      unknown: 'I don’t know',
    },
  },
  transport_scope: {
    values: ['international', 'poland', 'local', 'distribution', 'other'],
    fallbacks: {
      international: 'International',
      poland: 'Within Poland',
      local: 'Local',
      distribution: 'Distribution',
      other: 'Other',
    },
  },
  route_countries: {
    values: ['poland', 'germany', 'france', 'benelux', 'italy', 'spain', 'scandinavia', 'uk', 'other'],
    fallbacks: {
      poland: 'Poland',
      germany: 'Germany',
      france: 'France',
      benelux: 'Benelux',
      italy: 'Italy',
      spain: 'Spain',
      scandinavia: 'Scandinavia',
      uk: 'United Kingdom',
      other: 'Other',
    },
  },
  cargo_types: {
    values: ['ftl', 'ltl', 'distribution', 'containers', 'adr', 'car_transporter', 'other'],
    fallbacks: {
      ftl: 'FTL',
      ltl: 'LTL',
      distribution: 'Distribution',
      containers: 'Containers',
      adr: 'ADR',
      car_transporter: 'Car transporter',
      other: 'Other',
    },
  },
  loading_unloading: YES_NO_SOMETIMES,
  trailers: {
    values: ['curtain', 'reefer', 'container', 'tanker', 'dump', 'platform', 'other'],
    fallbacks: {
      curtain: 'Curtain',
      reefer: 'Reefer',
      container: 'Container',
      tanker: 'Tanker',
      dump: 'Dump',
      platform: 'Platform',
      other: 'Other',
    },
  },
  dedicated_vehicle: {
    values: ['yes', 'no', 'depends'],
    fallbacks: { yes: 'Yes', no: 'No', depends: 'Depends on the system' },
  },
  work_systems: {
    values: ['2_1', '3_1', '4_1', '6_2', '8_2', 'no_system', 'individual', 'other'],
    fallbacks: {
      '2_1': '2/1',
      '3_1': '3/1',
      '4_1': '4/1',
      '6_2': '6/2',
      '8_2': '8/2',
      no_system: 'No rotation system',
      individual: 'Individual',
      other: 'Other',
    },
  },
  individual_schedule: {
    values: ['yes', 'no', 'sometimes'],
    fallbacks: { yes: 'Yes', no: 'No', sometimes: 'In some cases' },
  },
  work_start: {
    values: ['always_base', 'route_changeover', 'other'],
    fallbacks: {
      always_base: 'Always from the base',
      route_changeover: 'Changeover on the route is possible',
      other: 'Other',
    },
  },
  travel_to_base_paid: YES_NO_PARTIAL,
  pay_system: {
    values: ['per_day', 'monthly_fixed', 'per_km', 'fixed_plus_bonus', 'other'],
    fallbacks: {
      per_day: 'Per day',
      monthly_fixed: 'Fixed monthly',
      per_km: 'Per km',
      fixed_plus_bonus: 'Fixed + bonus',
      other: 'Other',
    },
  },
  pay_netto_currency: CURRENCY,
  day_rate_currency: CURRENCY,
  guaranteed_min_income: YES_NO,
  extra_bonuses: YES_NO,
  pay_frequency: {
    values: ['monthly', 'twice_monthly', 'after_rotation', 'other'],
    fallbacks: {
      monthly: 'Once a month',
      twice_monthly: 'Twice a month',
      after_rotation: 'After rotation / trip',
      other: 'Other',
    },
  },
  advances: YES_NO_INDIVIDUAL,
  contract_types: {
    values: ['umowa_o_prace', 'umowa_zlecenie', 'b2b', 'other'],
    fallbacks: {
      umowa_o_prace: 'Umowa o pracę',
      umowa_zlecenie: 'Umowa zlecenie',
      b2b: 'B2B',
      other: 'Other',
    },
  },
  medical_psychotest_payer: {
    values: ['employer', 'driver', 'shared'],
    fallbacks: {
      employer: 'Employer',
      driver: 'Driver',
      shared: 'Partly employer',
    },
  },
  driver_certificate: {
    values: ['yes', 'no', 'not_required'],
    fallbacks: { yes: 'Yes', no: 'No', not_required: 'Not required' },
  },
  legalization_help: {
    values: ['work_permit', 'residence_card', 'code_95', 'license_exchange', 'driver_certificate', 'none', 'other'],
    fallbacks: {
      work_permit: 'Zezwolenie na pracę',
      residence_card: 'Karta pobytu',
      code_95: 'Code 95',
      license_exchange: 'Driving licence exchange',
      driver_certificate: 'Świadectwo kierowcy',
      none: 'We do not help',
      other: 'Other',
    },
  },
  min_experience: {
    values: ['none', '3_months', '6_months', '1_year', '2_years_plus'],
    fallbacks: {
      none: 'No experience',
      '3_months': '3 months',
      '6_months': '6 months',
      '1_year': '1 year',
      '2_years_plus': '2+ years',
    },
  },
  europe_experience: {
    values: ['yes', 'no', 'preferred'],
    fallbacks: { yes: 'Yes', no: 'No', preferred: 'Preferred' },
  },
  languages: {
    values: ['not_required', 'pl', 'en', 'de', 'other'],
    fallbacks: {
      not_required: 'No language required',
      pl: 'Polish',
      en: 'English',
      de: 'German',
      other: 'Other',
    },
  },
  language_level: {
    values: ['basic', 'conversational', 'good'],
    fallbacks: { basic: 'Basic', conversational: 'Conversational', good: 'Good' },
  },
  citizenships: {
    values: ['poland', 'ukraine', 'belarus', 'moldova', 'georgia', 'armenia', 'central_asia', 'asia', 'any_with_docs', 'other'],
    fallbacks: {
      poland: 'Poland',
      ukraine: 'Ukraine',
      belarus: 'Belarus',
      moldova: 'Moldova',
      georgia: 'Georgia',
      armenia: 'Armenia',
      central_asia: 'Central Asia',
      asia: 'Asia',
      any_with_docs: 'Any, if documents are in order',
      other: 'Other',
    },
  },
  required_documents: {
    values: ['driving_licence', 'code_95', 'driver_card', 'residence_card', 'work_visa', 'driver_certificate', 'other'],
    fallbacks: {
      driving_licence: 'Prawo jazdy',
      code_95: 'Code 95',
      driver_card: 'Karta kierowcy',
      residence_card: 'Karta pobytu',
      work_visa: 'Work visa',
      driver_certificate: 'Świadectwo kierowcy',
      other: 'Other',
    },
  },
  stay_document_min_validity: {
    values: ['any', '3_months', '6_months', '8_months', '12_months'],
    fallbacks: {
      any: 'Does not matter',
      '3_months': '3+ months',
      '6_months': '6+ months',
      '8_months': '8+ months',
      '12_months': '12+ months',
    },
  },
  housing: {
    values: ['free', 'paid', 'no'],
    fallbacks: { free: 'Free', paid: 'Paid', no: 'No' },
  },
  housing_between_trips: {
    values: ['yes', 'no', 'not_applicable'],
    fallbacks: { yes: 'Yes', no: 'No', not_applicable: 'Not applicable' },
  },
  personal_car_parking: YES_NO,
  selection_process: {
    values: ['document_check', 'phone_interview', 'video_interview', 'in_person', 'test_drive', 'other'],
    fallbacks: {
      document_check: 'Document check',
      phone_interview: 'Phone interview',
      video_interview: 'Video interview',
      in_person: 'In-person interview',
      test_drive: 'Test drive',
      other: 'Other',
    },
  },
  feedback_time: {
    values: ['same_day', 'within_24h', '1_3_days', 'over_3_days'],
    fallbacks: {
      same_day: 'Same day',
      within_24h: 'Within 24 hours',
      '1_3_days': '1–3 days',
      over_3_days: 'More than 3 days',
    },
  },
  start_after_approval: {
    values: ['immediately', 'within_week', '1_2_weeks', 'over_2_weeks', 'depends_on_docs'],
    fallbacks: {
      immediately: 'Immediately',
      within_week: 'Within a week',
      '1_2_weeks': '1–2 weeks',
      over_2_weeks: 'More than 2 weeks',
      depends_on_docs: 'Depends on documents',
    },
  },
  hire_themselves: YES_NO,
  other_agencies: YES_NO,
  hiring_problems: {
    values: [
      'not_enough_candidates',
      'low_lead_quality',
      'insufficient_experience',
      'document_issues',
      'no_shows',
      'high_turnover',
      'slow_process',
      'other',
    ],
    fallbacks: {
      not_enough_candidates: 'Not enough candidates',
      low_lead_quality: 'Low lead quality',
      insufficient_experience: 'Insufficient experience',
      document_issues: 'Document issues',
      no_shows: 'Candidates do not start work',
      high_turnover: 'High turnover',
      slow_process: 'Slow hiring process',
      other: 'Other',
    },
  },
  refusal_reasons: {
    values: [
      'pay',
      'work_system',
      'routes',
      'vehicles',
      'housing',
      'travel_to_base',
      'documents',
      'other_offer',
      'unknown',
      'other',
    ],
    fallbacks: {
      pay: 'Pay',
      work_system: 'Work system',
      routes: 'Routes',
      vehicles: 'Vehicles',
      housing: 'Housing',
      travel_to_base: 'Travel to base',
      documents: 'Documents',
      other_offer: 'They take another offer',
      unknown: 'We don’t know',
      other: 'Other',
    },
  },
  weekly_candidate_capacity: {
    values: ['1_5', '6_10', '11_20', '21_50', '50_plus'],
    fallbacks: {
      '1_5': '1–5',
      '6_10': '6–10',
      '11_20': '11–20',
      '21_50': '21–50',
      '50_plus': '50+',
    },
  },
}

function scopedOption(
  t: TFn,
  locale: LocaleCode,
  group: string,
  value: string,
  fallback: string,
): FieldOption {
  const scoped = lookupScopedTranslation(locale, `public.intake.presentation.options.${group}`, value)
  if (scoped) return { value, label: scoped }
  const key = `public.intake.presentation.options.${group}.${value}`
  const translated = t(key, { defaultValue: '' })
  if (translated && translated !== key) return { value, label: translated }
  return { value, label: fallback }
}

export function driverHiringFieldSuffix(qualifiedCode: string): string | null {
  const code = String(qualifiedCode || '').trim()
  if (!code.startsWith(DRIVER_HIRING_QUESTIONNAIRE_PREFIX)) return null
  return code.slice(DRIVER_HIRING_QUESTIONNAIRE_PREFIX.length)
}

export function driverHiringOptionsForSuffix(t: TFn, locale: LocaleCode, suffix: string): FieldOption[] {
  const spec = DRIVER_HIRING_OPTIONS[suffix]
  if (!spec) return []
  const group = `service_sales.driver_hiring.${suffix}`
  return spec.values.map((value) => scopedOption(t, locale, group, value, spec.fallbacks[value] ?? value))
}
