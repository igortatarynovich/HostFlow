/** Display model for the Candidate Professional Profile tab.

The screen renders this model and does not read legacy experience scalars.
*/

import { presentDuration, presentProfessionalCode } from '../professional-profile/presentation'

export type AggregateStatus =
  | 'calculated'
  | 'presence_only'
  | 'insufficient_history'
  | 'ambiguous_history'
  | 'no_evidence'

export type DurationAggregate = {
  status: AggregateStatus
  years: string | null
  days?: number | null
  presence?: string[]
  raw_presence?: string[]
}

export type ProfessionalProfileProjection = {
  capabilities: {
    licence: { categories: string[]; raw_unmapped: string[]; issuing_country: string | null; valid_to: string | null }
    code95: { presence: boolean | null; valid_to: string | null }
    tachograph: { presence: boolean | null; issuing_country: string | null; valid_to: string | null }
    adr: { presence: boolean | null; issuing_country: string | null; valid_to: string | null }
  }
  experience: {
    employments: Array<{
      id: string
      employer_name: string
      country: string | null
      position: string | null
      start_date: string | null
      end_date: string | null
      driving_categories: string[]
      operation_scopes: string[]
      movement_patterns: string[]
      crew_modes: string[]
      work_areas: Array<{ kind: string; code: string }>
      trailer_types: string[]
    }>
    aggregates: {
      total_tenure: DurationAggregate
      ce: DurationAggregate
      international: DurationAggregate
      eu: DurationAggregate
      movement_pattern?: Record<string, DurationAggregate>
      crew_mode?: Record<string, DurationAggregate>
    }
    practical_experience: {
      trailers: {
        status: AggregateStatus
        years: string | null
        items: Array<{ code: string; mapping: 'mapped' | 'unmapped'; target_code: string | null }>
      }
    }
    geography: { work_areas: Array<{ kind: string; code: string; resolution: 'catalog' | 'unmapped' }> }
    work_character: {
      operation_scopes: Array<{ code: string; resolution: 'catalog' | 'unmapped' }>
      movement_patterns: Array<{ code: string; resolution: 'catalog' | 'unmapped' }>
      crew_modes: Array<{ code: string; resolution: 'catalog' | 'unmapped' }>
    }
    declared: {
      ce: { status: string; years: string | null; origin: string | null }
      eu: { status: string; years: string | null }
      non_eu_years: { stored_value: unknown; interpreted_as: string }
      legacy_total: { stored_value: unknown; interpreted_as: string }
    }
  }
  constraints: Array<{
    id: string
    subject: string
    code: string
    effect: string
    source: string
    valid_from: string | null
    valid_to: string | null
    activity: 'active' | 'expired' | 'scheduled' | 'unknown'
    note: string | null
  }>
  preferences_and_availability: {
    choices: Array<{ id: string; subject: string; kind: string | null; code: string }>
    compensation: { amount: string | null; currency: string | null; period: string | null } | null
    availability: { available_from: string | null; status: string }
  }
}

export type DurationKind = 'hidden' | 'history' | 'declared' | 'both' | 'presence' | 'insufficient' | 'period_error'

export type DurationLine = {
  id: string
  label: string
  kind: DurationKind
  text: string
}

export type ProfileCopy = {
  history: (years: string) => string
  declared: (years: string) => string
  both: (calculated: string, declared: string) => string
  presence: string
  insufficient: string
  periodError: string
  rowPeriodError: string
  hasExperience: string
  unmapped: (code: string) => string
  openEnded: string
  noEmployment: string
  noPreferences: string
  availableFrom: (date: string) => string
  present: string
  absent: string
  unknown: string
  expired: string
  scheduled: string
  validityUnknown: string
}

export function formatProfileYears(years: string, locale: string): string {
  const value = Number(years)
  if (!Number.isFinite(value)) return years
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value)
}

export function durationReading(
  aggregate: DurationAggregate | undefined,
  declaredYears: string | null,
): { kind: DurationKind; calculated: string | null; declared: string | null; days: number | null } {
  const status = aggregate?.status ?? 'no_evidence'
  const calculated = status === 'calculated' && aggregate?.years ? aggregate.years : null
  const declared = declaredYears
  const days = typeof aggregate?.days === 'number' ? aggregate.days : null
  if (status === 'ambiguous_history') return { kind: 'period_error', calculated: null, declared, days: null }
  if (status === 'insufficient_history') return { kind: 'insufficient', calculated: null, declared, days: null }
  if (status === 'presence_only') return { kind: 'presence', calculated: null, declared, days: null }
  if (calculated && declared) return { kind: 'both', calculated, declared, days }
  if (calculated) return { kind: 'history', calculated, declared: null, days }
  if (declared) return { kind: 'declared', calculated: null, declared, days: null }
  return { kind: 'hidden', calculated: null, declared: null, days: null }
}

export function durationText(
  reading: { kind: DurationKind; calculated: string | null; declared: string | null; days?: number | null },
  copy: ProfileCopy,
  locale: string,
): string {
  const calculated = reading.calculated ? presentDuration(reading.days, reading.calculated, locale) : ''
  const declared = reading.declared ? formatProfileYears(reading.declared, locale) : ''
  const withDeclared = (base: string) => (declared ? `${base} (${copy.declared(declared)})` : base)
  if (reading.kind === 'both') return `${calculated} (${copy.declared(declared)})`
  if (reading.kind === 'history') return calculated
  if (reading.kind === 'declared') return copy.declared(declared)
  if (reading.kind === 'presence') return withDeclared(copy.presence)
  if (reading.kind === 'insufficient') return withDeclared(copy.insufficient)
  if (reading.kind === 'period_error') return withDeclared(copy.periodError)
  return ''
}

function storedYears(value: unknown): string | null {
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  if (typeof value === 'string' && value.trim()) return value.trim()
  return null
}

const SUMMARY_FACTS = ['ce', 'international', 'eu'] as const

function summaryName(id: (typeof SUMMARY_FACTS)[number], locale: string): string {
  if (id === 'ce') return 'CE'
  if (id === 'international') return presentProfessionalCode('operation_scope', 'international', locale) || 'International'
  return presentProfessionalCode('work_area_region', 'eu', locale) || 'EU'
}

export function professionalSummary(profile: ProfessionalProfileProjection, copy: ProfileCopy, locale: string): string[] {
  const parts: string[] = []
  const declared = {
    ce: profile.experience.declared.ce.years,
    international: null,
    eu: null,
  }
  for (const id of SUMMARY_FACTS) {
    const aggregate = profile.experience.aggregates[id]
    const reading = durationReading(aggregate, declared[id])
    const text = durationText(reading, copy, locale)
    if (reading.kind === 'hidden' || !text) continue
    const name = summaryName(id, locale)
    parts.push(reading.kind === 'history' || reading.kind === 'both' ? `${name} ${text}` : `${name} · ${text}`)
  }
  if (profile.capabilities.code95.presence === true) parts.push('Code 95')
  if (profile.capabilities.adr.presence === true) parts.push('ADR')
  return parts
}

export function durationLines(profile: ProfessionalProfileProjection, copy: ProfileCopy, locale: string): DurationLine[] {
  const declaredTotal =
    profile.experience.declared.legacy_total.interpreted_as === 'legacy_declared_total'
      ? storedYears(profile.experience.declared.legacy_total.stored_value)
      : null
  const rows: Array<[string, string, DurationAggregate | undefined, string | null]> = [
    ['total', 'total', profile.experience.aggregates.total_tenure, declaredTotal],
  ]
  const lines: DurationLine[] = []
  for (const [id, label, aggregate, declared] of rows) {
    const reading = durationReading(aggregate, declared)
    const text = durationText(reading, copy, locale)
    if (reading.kind !== 'hidden' && text) lines.push({ id, label, kind: reading.kind, text })
  }
  const declaredNonEu =
    profile.experience.declared.non_eu_years.interpreted_as === 'declared_non_eu_years'
      ? storedYears(profile.experience.declared.non_eu_years.stored_value)
      : null
  if (declaredNonEu) {
    lines.push({
      id: 'non_eu_declared',
      label: 'non_eu',
      kind: 'declared',
      text: copy.declared(formatProfileYears(declaredNonEu, locale)),
    })
  }
  for (const [code, aggregate] of Object.entries(profile.experience.aggregates.movement_pattern || {})) {
    const reading = durationReading(aggregate, null)
    const text = durationText(reading, copy, locale)
    if (reading.kind !== 'hidden' && text) lines.push({ id: `movement:${code}`, label: code, kind: reading.kind, text })
  }
  for (const [code, aggregate] of Object.entries(profile.experience.aggregates.crew_mode || {})) {
    const reading = durationReading(aggregate, null)
    const text = durationText(reading, copy, locale)
    if (reading.kind !== 'hidden' && text) lines.push({ id: `crew:${code}`, label: code, kind: reading.kind, text })
  }
  return lines
}

export function trailerLines(
  profile: ProfessionalProfileProjection,
  copy: ProfileCopy,
  locale: string,
): Array<{ code: string; text: string; unmapped: boolean }> {
  return profile.experience.practical_experience.trailers.items.map((item) => {
    const mappedLabel = item.mapping === 'mapped' && item.target_code
      ? presentProfessionalCode('trailer_hiring', item.target_code, locale)
      : null
    return {
      code: item.code,
      unmapped: !mappedLabel,
      text: mappedLabel ? `${mappedLabel} · ${copy.hasExperience}` : copy.unmapped(item.code),
    }
  })
}

export function employmentPeriodError(start: string | null, end: string | null): boolean {
  return Boolean(start && end && end < start)
}

export function splitConstraints(profile: ProfessionalProfileProjection): {
  current: ProfessionalProfileProjection['constraints']
  history: ProfessionalProfileProjection['constraints']
} {
  const current = profile.constraints.filter((row) => row.activity === 'active')
  const history = profile.constraints.filter((row) => row.activity !== 'active')
  return { current, history }
}
