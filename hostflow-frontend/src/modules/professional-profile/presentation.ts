/**
 * Shared presentation of professional-profile codes, durations and pay.
 * The resolver keeps exact days and catalog codes. This module is the operator reading.
 */

import { lookupScopedTranslation, type LocaleCode } from '../../i18n'

const PROFESSIONAL_LABELS: Record<string, Record<string, string>> = {
  ru: {
    'operation_scope.international': 'Международные',
    'operation_scope.domestic': 'Внутренние перевозки',
    'movement_pattern.long_haul': 'Дальние рейсы',
    'movement_pattern.distribution': 'Дистрибуция',
    'crew_mode.solo': 'Solo',
    'crew_mode.double': 'Двойной экипаж',
    'work_area_region.eu': 'ЕС',
    'work_area_region.cis': 'СНГ',
    'work_area_region.uk': 'Великобритания',
    'work_area_region.scandi': 'Скандинавия',
    'work_area_region.local': 'Местные',
    'pay_rate.monthly_fixed': 'месяц',
    'pay_rate.per_day': 'день',
    'pay_rate.per_km': 'км',
    'pay_rate.fixed_plus_bonus': 'месяц + бонус',
  },
  en: {
    'operation_scope.international': 'International',
    'operation_scope.domestic': 'Domestic',
    'movement_pattern.long_haul': 'Long haul',
    'movement_pattern.distribution': 'Distribution',
    'crew_mode.solo': 'Solo',
    'crew_mode.double': 'Double crew',
    'work_area_region.eu': 'EU',
    'work_area_region.cis': 'CIS',
    'work_area_region.uk': 'United Kingdom',
    'work_area_region.scandi': 'Scandinavia',
    'work_area_region.local': 'Local',
    'pay_rate.monthly_fixed': 'month',
    'pay_rate.per_day': 'day',
    'pay_rate.per_km': 'km',
    'pay_rate.fixed_plus_bonus': 'month + bonus',
  },
  pl: {
    'operation_scope.international': 'Międzynarodowe',
    'operation_scope.domestic': 'Krajowe',
    'movement_pattern.long_haul': 'Trasy dalekobieżne',
    'movement_pattern.distribution': 'Dystrybucja',
    'crew_mode.solo': 'Solo',
    'crew_mode.double': 'Załoga',
    'work_area_region.eu': 'UE',
    'work_area_region.cis': 'WNP',
    'work_area_region.uk': 'Wielka Brytania',
    'work_area_region.scandi': 'Skandynawia',
    'work_area_region.local': 'Lokalne',
    'pay_rate.monthly_fixed': 'miesiąc',
    'pay_rate.per_day': 'dzień',
    'pay_rate.per_km': 'km',
    'pay_rate.fixed_plus_bonus': 'miesiąc + premia',
  },
}

function localeCode(locale: string): 'ru' | 'en' | 'pl' {
  if (locale.startsWith('pl')) return 'pl'
  if (locale.startsWith('en')) return 'en'
  return 'ru'
}

function hiringLabel(locale: string, suffix: string, code: string): string | null {
  const label = lookupScopedTranslation(
    localeCode(locale) as LocaleCode,
    `public.intake.presentation.options.service_sales.driver_hiring.${suffix}`,
    code,
  )
  return label ?? null
}

/** Label for a system catalog code. Null means the code is not in the catalog. */
export function presentProfessionalCode(vocabulary: string, code: string, locale: string): string | null {
  if (vocabulary === 'work_system') return hiringLabel(locale, 'work_systems', code)
  if (vocabulary === 'trailer_hiring') return hiringLabel(locale, 'trailers', code)
  const labels = PROFESSIONAL_LABELS[localeCode(locale)]
  return labels[`${vocabulary}.${code}`] ?? null
}

export function presentCountry(code: string, locale: string): string {
  const normalized = code.trim().toUpperCase()
  if (normalized.length !== 2) return code
  try {
    return new Intl.DisplayNames(localeCode(locale), { type: 'region' }).of(normalized) || code
  } catch {
    return code
  }
}

function yearWord(count: number, locale: string): string {
  const lang = localeCode(locale)
  if (lang === 'en') return count === 1 ? 'year' : 'years'
  if (lang === 'pl') {
    if (count === 1) return 'rok'
    const mod10 = count % 10
    const mod100 = count % 100
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'lata'
    return 'lat'
  }
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod10 === 1 && mod100 !== 11) return 'год'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'года'
  return 'лет'
}

function monthWord(locale: string): string {
  const lang = localeCode(locale)
  if (lang === 'en') return 'mo'
  if (lang === 'pl') return 'mies.'
  return 'мес.'
}

/** Operator duration from resolver days. Exact days stay on the resolver. */
export function presentDuration(days: number | null | undefined, years: string | null, locale: string): string {
  let totalDays = typeof days === 'number' && Number.isFinite(days) ? Math.max(0, Math.round(days)) : null
  if (totalDays == null && years) {
    const numeric = Number(years)
    if (Number.isFinite(numeric)) totalDays = Math.max(0, Math.round(numeric * 365))
  }
  if (totalDays == null) return years ?? ''
  let wholeYears = Math.floor(totalDays / 365)
  let months = Math.round((totalDays - wholeYears * 365) / (365 / 12))
  if (months >= 12) {
    wholeYears += 1
    months = 0
  }
  const parts: string[] = []
  if (wholeYears > 0) parts.push(`${wholeYears} ${yearWord(wholeYears, locale)}`)
  if (months > 0) parts.push(`${months} ${monthWord(locale)}`)
  if (!parts.length) return `0 ${monthWord(locale)}`
  return parts.join(' ')
}

export function presentMonthSpan(start: string | null, end: string | null, openEnded: string): string | null {
  const month = (iso: string | null) => {
    if (!iso || iso.length < 7) return null
    const [year, mon] = iso.split('-')
    if (!year || !mon) return null
    return `${mon}.${year}`
  }
  const from = month(start)
  if (!from) return null
  const to = month(end)
  return `${from}–${to || openEnded}`
}

export function presentCompensation(
  amount: string | null,
  currency: string | null,
  period: string | null,
  locale: string,
): string {
  const numeric = amount == null ? null : Number(amount)
  const formatted = numeric != null && Number.isFinite(numeric)
    ? new Intl.NumberFormat(localeCode(locale), { maximumFractionDigits: 0 }).format(numeric).replace(/[\u00a0\u202f]/g, ' ')
    : (amount ?? '')
  const unit = period ? presentProfessionalCode('pay_rate', period, locale) : null
  const money = [formatted, currency ? currency.toUpperCase() : ''].filter(Boolean).join(' ')
  return unit ? `${money} / ${unit}` : money
}

/** Operator count of employment records. */
export function presentJobCount(count: number, locale: string): string {
  const lang = localeCode(locale)
  const mod10 = count % 10
  const mod100 = count % 100
  if (lang === 'en') return count === 1 ? '1 job' : `${count} jobs`
  if (lang === 'pl') {
    if (count === 1) return '1 miejsce pracy'
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return `${count} miejsca pracy`
    return `${count} miejsc pracy`
  }
  if (mod10 === 1 && mod100 !== 11) return `${count} место работы`
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return `${count} места работы`
  return `${count} мест работы`
}
