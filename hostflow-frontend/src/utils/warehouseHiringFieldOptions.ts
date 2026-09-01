import type { LocaleCode } from '../i18n'
import { lookupScopedTranslation } from '../i18n'

export const WAREHOUSE_HIRING_QUESTIONNAIRE_PREFIX = 'service_sales.warehouse_hiring.'

type TFn = (key: string, options?: { defaultValue?: string }) => string
export type FieldOption = { value: string; label: string }

type OptionSpec = { values: string[]; fallbacks: Record<string, string> }

const YES_NO: OptionSpec = {
  values: ['yes', 'no'],
  fallbacks: { yes: 'Yes', no: 'No' },
}

export const WAREHOUSE_HIRING_OPTIONS: Record<string, OptionSpec> = {
  worker_roles: {
    values: [
      'warehouse',
      'picker',
      'packer',
      'sorter',
      'loader',
      'production',
      'laborer',
      'forklift_operator',
      'other',
    ],
    fallbacks: {
      warehouse: 'Warehouse worker',
      picker: 'Order picker',
      packer: 'Packer',
      sorter: 'Sorter',
      loader: 'Loader',
      production: 'Production worker',
      laborer: 'General laborer',
      forklift_operator: 'Forklift operator',
      other: 'Other',
    },
  },
  first_workers_when: {
    values: ['asap', 'within_2_weeks', 'within_month', '1_3_months', 'ongoing'],
    fallbacks: {
      asap: 'As soon as possible',
      within_2_weeks: 'Within 2 weeks',
      within_month: 'Within a month',
      '1_3_months': '1–3 months',
      ongoing: 'Ongoing hiring',
    },
  },
  monthly_hire_volume: {
    values: ['1_5', '6_10', '11_20', '21_50', '50_plus', 'unknown'],
    fallbacks: {
      '1_5': '1–5',
      '6_10': '6–10',
      '11_20': '11–20',
      '21_50': '21–50',
      '50_plus': '50+',
      unknown: 'I don’t know',
    },
  },
  job_tasks: {
    values: [
      'picking',
      'packing',
      'sorting',
      'loading',
      'scanner',
      'goods_receipt',
      'putaway',
      'production',
      'cleaning',
      'physical',
      'other',
    ],
    fallbacks: {
      picking: 'Order picking',
      packing: 'Packing',
      sorting: 'Sorting',
      loading: 'Loading / unloading',
      scanner: 'Scanner work',
      goods_receipt: 'Goods receipt',
      putaway: 'Putaway',
      production: 'Production work',
      cleaning: 'Workplace cleaning',
      physical: 'Physical work',
      other: 'Other',
    },
  },
  physical_demand: {
    values: ['light', 'medium', 'heavy'],
    fallbacks: { light: 'Light', medium: 'Medium', heavy: 'Heavy' },
  },
  max_lift_weight: {
    values: ['up_to_5', '5_10', '10_15', '15_20', 'over_20', 'not_required'],
    fallbacks: {
      up_to_5: 'Up to 5 kg',
      '5_10': '5–10 kg',
      '10_15': '10–15 kg',
      '15_20': '15–20 kg',
      over_20: 'More than 20 kg',
      not_required: 'Lifting is not required',
    },
  },
  work_posture: {
    values: ['standing', 'sitting', 'moving', 'mixed'],
    fallbacks: {
      standing: 'Standing',
      sitting: 'Sitting',
      moving: 'On the move',
      mixed: 'Mixed',
    },
  },
  has_productivity_norms: YES_NO,
  kpi_system: {
    values: ['no', 'yes', 'partial'],
    fallbacks: { no: 'No', yes: 'Yes', partial: 'Partially' },
  },
  workplace_temperature: {
    values: ['room', 'cool', 'fridge', 'freezer', 'hot', 'outdoor'],
    fallbacks: {
      room: 'Room temperature',
      cool: 'Cool',
      fridge: 'Refrigerator',
      freezer: 'Freezer',
      hot: 'High temperature',
      outdoor: 'Outdoor work',
    },
  },
  shift_length: {
    values: ['hours_8', 'hours_10', 'hours_12', 'other'],
    fallbacks: {
      hours_8: '8 hours',
      hours_10: '10 hours',
      hours_12: '12 hours',
      other: 'Other',
    },
  },
  shift_count: {
    values: ['one', 'two', 'three', 'flexible'],
    fallbacks: { one: '1', two: '2', three: '3', flexible: 'Flexible schedule' },
  },
  shift_types: {
    values: ['morning', 'day', 'evening', 'night'],
    fallbacks: {
      morning: 'Morning',
      day: 'Day',
      evening: 'Evening',
      night: 'Night',
    },
  },
  workdays_per_week: {
    values: ['days_5', 'days_6', 'flexible', 'by_schedule'],
    fallbacks: {
      days_5: '5',
      days_6: '6',
      flexible: 'Flexible schedule',
      by_schedule: 'According to schedule',
    },
  },
  weekend_work: {
    values: ['no', 'sometimes', 'regularly'],
    fallbacks: { no: 'No', sometimes: 'Sometimes', regularly: 'Regularly' },
  },
  overtime: {
    values: ['no', 'optional', 'regularly'],
    fallbacks: { no: 'No', optional: 'Optional', regularly: 'Regularly' },
  },
  pay_system: {
    values: ['hourly', 'monthly', 'piece_rate', 'rate_plus_bonus', 'other'],
    fallbacks: {
      hourly: 'Hourly',
      monthly: 'Monthly rate',
      piece_rate: 'Piece-rate',
      rate_plus_bonus: 'Rate + bonus',
      other: 'Other',
    },
  },
  pay_netto_unit: {
    values: ['pln_hour', 'pln_month', 'eur_hour', 'eur_month'],
    fallbacks: {
      pln_hour: 'PLN / hour',
      pln_month: 'PLN / month',
      eur_hour: 'EUR / hour',
      eur_month: 'EUR / month',
    },
  },
  pay_brutto_unit: {
    values: ['pln_hour', 'pln_month', 'eur_hour', 'eur_month'],
    fallbacks: {
      pln_hour: 'PLN / hour',
      pln_month: 'PLN / month',
      eur_hour: 'EUR / hour',
      eur_month: 'EUR / month',
    },
  },
  guaranteed_hours: YES_NO,
  has_bonuses: YES_NO,
  bonus_types: {
    values: ['attendance', 'productivity', 'night_shifts', 'weekends', 'other'],
    fallbacks: {
      attendance: 'Attendance',
      productivity: 'Productivity',
      night_shifts: 'Night shifts',
      weekends: 'Weekends',
      other: 'Other',
    },
  },
  overtime_pay: {
    values: ['standard', 'increased', 'included', 'other'],
    fallbacks: {
      standard: 'At the standard rate',
      increased: 'At an increased rate',
      included: 'Included in the pay system',
      other: 'Other',
    },
  },
  pay_frequency: {
    values: ['monthly', 'twice_monthly', 'weekly', 'other'],
    fallbacks: {
      monthly: 'Once a month',
      twice_monthly: 'Twice a month',
      weekly: 'Weekly',
      other: 'Other',
    },
  },
  advances: {
    values: ['yes', 'no', 'individual'],
    fallbacks: { yes: 'Yes', no: 'No', individual: 'Case by case' },
  },
  contract_types: {
    values: ['employment', 'zlecenie', 'b2b', 'other'],
    fallbacks: {
      employment: 'Umowa o pracę',
      zlecenie: 'Umowa zlecenie',
      b2b: 'B2B',
      other: 'Other',
    },
  },
  has_probation: YES_NO,
  medical_exam_payer: {
    values: ['employer', 'worker'],
    fallbacks: { employer: 'Employer', worker: 'Worker' },
  },
  workwear: {
    values: ['full', 'partial', 'no'],
    fallbacks: { full: 'Fully', partial: 'Partially', no: 'No' },
  },
  experience_required: {
    values: ['not_required', 'preferred', 'required'],
    fallbacks: {
      not_required: 'Not required',
      preferred: 'Preferred',
      required: 'Required',
    },
  },
  min_experience: {
    values: ['up_to_3_months', '3_6_months', '6_12_months', '1_plus', '2_plus'],
    fallbacks: {
      up_to_3_months: 'Up to 3 months',
      '3_6_months': '3–6 months',
      '6_12_months': '6–12 months',
      '1_plus': '1+ year',
      '2_plus': '2+ years',
    },
  },
  extra_qualifications: {
    values: ['not_required', 'forklift_udt', 'sanitary_book', 'driving_license', 'other'],
    fallbacks: {
      not_required: 'Not required',
      forklift_udt: 'Forklift UDT',
      sanitary_book: 'Sanitary book',
      driving_license: 'Driving license',
      other: 'Other',
    },
  },
  language_required: {
    values: ['no', 'yes', 'preferred'],
    fallbacks: { no: 'No', yes: 'Yes', preferred: 'Preferred' },
  },
  languages: {
    values: ['polish', 'english', 'ukrainian', 'russian', 'other'],
    fallbacks: {
      polish: 'Polish',
      english: 'English',
      ukrainian: 'Ukrainian',
      russian: 'Russian',
      other: 'Other',
    },
  },
  language_level: {
    values: ['basic_commands', 'basic', 'conversational', 'good'],
    fallbacks: {
      basic_commands: 'Understanding basic commands',
      basic: 'Basic',
      conversational: 'Conversational',
      good: 'Good',
    },
  },
  gender_considered: {
    values: ['men', 'women', 'all_matching'],
    fallbacks: {
      men: 'Men',
      women: 'Women',
      all_matching: 'Anyone who matches the role requirements',
    },
  },
  citizenships: {
    values: [
      'poland',
      'ukraine',
      'belarus',
      'moldova',
      'georgia',
      'armenia',
      'central_asia',
      'asia',
      'all_with_documents',
      'other',
    ],
    fallbacks: {
      poland: 'Poland',
      ukraine: 'Ukraine',
      belarus: 'Belarus',
      moldova: 'Moldova',
      georgia: 'Georgia',
      armenia: 'Armenia',
      central_asia: 'Central Asia',
      asia: 'Asia',
      all_with_documents: 'Anyone with the required documents',
      other: 'Other',
    },
  },
  required_documents: {
    values: ['pesel', 'karta_pobytu', 'work_visa', 'work_permit', 'ukr_status', 'other'],
    fallbacks: {
      pesel: 'PESEL',
      karta_pobytu: 'Karta pobytu',
      work_visa: 'Work visa',
      work_permit: 'Work permit',
      ukr_status: 'UKR status',
      other: 'Other',
    },
  },
  stay_document_min_validity: {
    values: ['irrelevant', '3_plus', '6_plus', '9_plus', '12_plus'],
    fallbacks: {
      irrelevant: 'Does not matter',
      '3_plus': '3+ months',
      '6_plus': '6+ months',
      '9_plus': '9+ months',
      '12_plus': '12+ months',
    },
  },
  housing: {
    values: ['free', 'paid', 'no'],
    fallbacks: { free: 'Free', paid: 'Paid', no: 'No' },
  },
  roommates: {
    values: ['1', '2', '3', '4', '5_plus'],
    fallbacks: { '1': '1', '2': '2', '3': '3', '4': '4', '5_plus': '5+' },
  },
  transport_to_work: {
    values: ['free', 'paid', 'no', 'not_needed'],
    fallbacks: { free: 'Free', paid: 'Paid', no: 'No', not_needed: 'Not needed' },
  },
  selection_process: {
    values: ['application_review', 'phone', 'online', 'in_person', 'practical_test', 'no_interview'],
    fallbacks: {
      application_review: 'Application review',
      phone: 'Phone interview',
      online: 'Online interview',
      in_person: 'In-person interview',
      practical_test: 'Practical test',
      no_interview: 'No interview',
    },
  },
  decision_time: {
    values: ['same_day', 'within_24h', '1_3_days', 'more_than_3'],
    fallbacks: {
      same_day: 'Same day',
      within_24h: 'Within 24 hours',
      '1_3_days': '1–3 days',
      more_than_3: 'More than 3 days',
    },
  },
  start_after_approval: {
    values: ['immediately', 'within_week', '1_2_weeks', 'after_documents'],
    fallbacks: {
      immediately: 'Immediately',
      within_week: 'Within a week',
      '1_2_weeks': '1–2 weeks',
      after_documents: 'After documents are processed',
    },
  },
  has_onboarding: {
    values: ['paid', 'unpaid', 'no'],
    fallbacks: {
      paid: 'Yes, paid',
      unpaid: 'Yes, unpaid',
      no: 'No',
    },
  },
  onboarding_duration: {
    values: ['1_day', '2_3_days', 'up_to_week', 'more_than_week'],
    fallbacks: {
      '1_day': '1 day',
      '2_3_days': '2–3 days',
      up_to_week: 'Up to a week',
      more_than_week: 'More than a week',
    },
  },
  hire_themselves: YES_NO,
  other_agencies: YES_NO,
  hiring_problems: {
    values: [
      'not_enough_candidates',
      'mismatch',
      'no_show',
      'high_turnover',
      'documents',
      'language',
      'slow_process',
      'other',
    ],
    fallbacks: {
      not_enough_candidates: 'Not enough candidates',
      mismatch: 'Candidates do not match requirements',
      no_show: 'They do not show up for work',
      high_turnover: 'High turnover',
      documents: 'Documents',
      language: 'Language barrier',
      slow_process: 'Slow hiring process',
      other: 'Other',
    },
  },
  refusal_reasons: {
    values: [
      'pay',
      'few_hours',
      'schedule',
      'night_shifts',
      'hard_work',
      'housing',
      'transport',
      'location',
      'other_job',
      'unknown',
      'other',
    ],
    fallbacks: {
      pay: 'Pay',
      few_hours: 'Too few hours',
      schedule: 'Schedule',
      night_shifts: 'Night shifts',
      hard_work: 'Hard work',
      housing: 'Housing',
      transport: 'Transport',
      location: 'Location',
      other_job: 'They found another job',
      unknown: 'We don’t know',
      other: 'Other',
    },
  },
  weekly_candidate_capacity: {
    values: ['1_5', '6_10', '11_20', '21_50', '51_100', '100_plus'],
    fallbacks: {
      '1_5': '1–5',
      '6_10': '6–10',
      '11_20': '11–20',
      '21_50': '21–50',
      '51_100': '51–100',
      '100_plus': '100+',
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

export function warehouseHiringFieldSuffix(qualifiedCode: string): string | null {
  const code = String(qualifiedCode || '').trim()
  if (!code.startsWith(WAREHOUSE_HIRING_QUESTIONNAIRE_PREFIX)) return null
  return code.slice(WAREHOUSE_HIRING_QUESTIONNAIRE_PREFIX.length)
}

export function warehouseHiringOptionsForSuffix(t: TFn, locale: LocaleCode, suffix: string): FieldOption[] {
  const spec = WAREHOUSE_HIRING_OPTIONS[suffix]
  if (!spec) return []
  const group = `service_sales.warehouse_hiring.${suffix}`
  return spec.values.map((value) => scopedOption(t, locale, group, value, spec.fallbacks[value] ?? value))
}
