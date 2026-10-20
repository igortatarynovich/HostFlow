/**
 * Recruiter reading of professional vacancy eligibility.
 * Reason codes and provenance identifiers stay inputs. They are not labels.
 */

import { presentDuration, presentProfessionalCode, presentUnmapped } from '../../platform/professionalPresentation'

export type EligibilityRequirement = {
  qualified_code?: string | null
  strength?: string | null
  affects_eligibility?: boolean
  expected?: {
    domain?: string | null
    mode?: string | null
    code?: string | null
    minimum_days?: number | null
    subject?: string | null
  } | null
  evidence?: Record<string, unknown> | null
  result?: string | null
  reason?: string | null
  provenance?: Array<{ source?: string | null }> | null
}

export type EligibilityProjection = {
  candidate_id: string
  vacancy_id: string
  shadow_eligibility?: string | null
  requirements?: EligibilityRequirement[] | null
  unavailable?: string | null
}

export type EligibilityRowView = {
  requirement: string
  result: string
  evidence: string | null
  source: string | null
}

export type EligibilityView = {
  status: string
  statusLabel: string
  heading: string
  caption: string
  detailsLabel: string
  confirmed: number
  total: number
  countLabel: string
  rows: EligibilityRowView[]
}

type Copy = {
  status: Record<string, string>
  category: (code: string) => string
  experienceAtLeast: (duration: string) => string
  candidate: (value: string) => string
  calculated: (duration: string) => string
  notFound: string
  source: (name: string) => string
  qualification: string
  history: string
  constraints: string
  count: (confirmed: number, total: number) => string
  flags: Record<string, string>
  heading: string
  caption: string
  details: string
}

const COPY: Record<'ru' | 'en' | 'pl', Copy> = {
  ru: {
    status: {
      match: 'Соответствует',
      no_match: 'Не соответствует',
      needs_info: 'Недостаточно данных',
      needs_review: 'Требует проверки',
    },
    category: (code) => `Категория ${code}`,
    experienceAtLeast: (duration) => `Опыт ≥ ${duration}`,
    candidate: (value) => `Кандидат: ${value}`,
    calculated: (duration) => `Рассчитано: ${duration}`,
    notFound: 'В подтверждённой истории опыт не найден',
    source: (name) => `Источник: ${name}`,
    qualification: 'квалификация',
    history: 'история работы',
    constraints: 'ограничения',
    count: (confirmed, total) => `${confirmed}/${total} требований подтверждено`,
    flags: { code95: 'Code 95', adr: 'ADR', tachograph: 'Тахограф' },
    heading: 'Соответствие вакансии',
    caption: 'Соответствие профессиональным требованиям',
    details: 'Подробнее',
  },
  en: {
    status: {
      match: 'Matches',
      no_match: 'Does not match',
      needs_info: 'Not enough information',
      needs_review: 'Needs review',
    },
    category: (code) => `Category ${code}`,
    experienceAtLeast: (duration) => `Experience ≥ ${duration}`,
    candidate: (value) => `Candidate: ${value}`,
    calculated: (duration) => `Calculated: ${duration}`,
    notFound: 'Not found in confirmed work history',
    source: (name) => `Source: ${name}`,
    qualification: 'qualification',
    history: 'work history',
    constraints: 'constraints',
    count: (confirmed, total) => `${confirmed}/${total} requirements confirmed`,
    flags: { code95: 'Code 95', adr: 'ADR', tachograph: 'Tachograph' },
    heading: 'Vacancy match',
    caption: 'Professional requirements match',
    details: 'Details',
  },
  pl: {
    status: {
      match: 'Spełnia',
      no_match: 'Nie spełnia',
      needs_info: 'Za mało danych',
      needs_review: 'Wymaga sprawdzenia',
    },
    category: (code) => `Kategoria ${code}`,
    experienceAtLeast: (duration) => `Doświadczenie ≥ ${duration}`,
    candidate: (value) => `Kandydat: ${value}`,
    calculated: (duration) => `Obliczono: ${duration}`,
    notFound: 'Brak w potwierdzonej historii pracy',
    source: (name) => `Źródło: ${name}`,
    qualification: 'kwalifikacja',
    history: 'historia pracy',
    constraints: 'ograniczenia',
    count: (confirmed, total) => `${confirmed}/${total} wymagań potwierdzonych`,
    flags: { code95: 'Code 95', adr: 'ADR', tachograph: 'Tachograf' },
    heading: 'Zgodność z wakatem',
    caption: 'Zgodność z wymaganiami zawodowymi',
    details: 'Szczegóły',
  },
}

function localeCode(locale: string): 'ru' | 'en' | 'pl' {
  if (locale.startsWith('pl')) return 'pl'
  if (locale.startsWith('en')) return 'en'
  return 'ru'
}

function requirementTitle(row: EligibilityRequirement, copy: Copy, locale: string): string {
  const code = String(row.qualified_code || '')
  const expected = row.expected || {}
  const token = String(expected.code || '')
  if (code.startsWith('capability:driving_category:')) return copy.category(token)
  if (code.startsWith('capability:')) return copy.flags[token] || token
  if (code.startsWith('experience:trailer_hiring:')) {
    return presentProfessionalCode('trailer_hiring', token, locale) || presentUnmapped(token, locale)
  }
  if (code.startsWith('experience:') && expected.mode === 'minimum' && typeof expected.minimum_days === 'number') {
    return copy.experienceAtLeast(presentDuration(expected.minimum_days, null, locale))
  }
  const facet = code.split(':')[1] || ''
  const vocabulary = facet === 'operation_scope' || facet === 'movement_pattern' || facet === 'crew_mode' ? facet : ''
  if (vocabulary) return presentProfessionalCode(vocabulary, token, locale) || presentUnmapped(token, locale)
  if (facet === 'total') return copy.experienceAtLeast(presentDuration(0, null, locale))
  return presentProfessionalCode(facet, token, locale) || token
}

function evidenceText(row: EligibilityRequirement, copy: Copy, locale: string): string | null {
  const reason = String(row.reason || '')
  const evidence = row.evidence || {}
  const token = String(row.expected?.code || '')
  if (reason === 'capability_present' || reason === 'capability_absent') {
    const categories = Array.isArray(evidence.categories) ? evidence.categories.map(String) : []
    const value = reason === 'capability_present' && categories.includes(token) ? token : categories.join(', ')
    return value ? copy.candidate(value) : null
  }
  if (reason === 'calculated_meets_minimum' || reason === 'calculated_below_minimum') {
    const days = typeof evidence.days === 'number' ? evidence.days : null
    const years = typeof evidence.years === 'string' ? evidence.years : null
    const duration = presentDuration(days, years, locale)
    return duration ? copy.calculated(duration) : null
  }
  if (
    reason === 'experience_not_recorded'
    || reason === 'presence_only_not_duration'
    || reason === 'trailer_absent'
    || reason === 'experience_absent'
  ) {
    return copy.notFound
  }
  if (reason === 'capability_unmapped' || reason === 'trailer_unmapped' || reason === 'experience_unmapped') {
    const raw = Array.isArray(evidence.raw_unmapped) ? evidence.raw_unmapped : evidence.unmapped
    const first = Array.isArray(raw) ? String(raw[0] || '') : ''
    return first ? presentUnmapped(first, locale) : null
  }
  return null
}

function sourceText(row: EligibilityRequirement, copy: Copy): string | null {
  const source = String(row.provenance?.[0]?.source || '')
  if (source.startsWith('capabilities')) return copy.source(copy.qualification)
  if (source.startsWith('experience')) return copy.source(copy.history)
  if (source === 'constraints') return copy.source(copy.constraints)
  return null
}

export function presentVacancyEligibility(
  projection: EligibilityProjection | null | undefined,
  locale: string,
): EligibilityView | null {
  const status = projection?.shadow_eligibility
  if (!projection?.vacancy_id || !status) return null
  const copy = COPY[localeCode(locale)]
  const rows = (projection.requirements || []).filter((row) => row.affects_eligibility !== false && row.strength !== 'preferred')
  const confirmed = rows.filter((row) => row.result === 'match').length
  return {
    status,
    statusLabel: copy.status[status] || status,
    heading: copy.heading,
    caption: copy.caption,
    detailsLabel: copy.details,
    confirmed,
    total: rows.length,
    countLabel: copy.count(confirmed, rows.length),
    rows: rows.map((row) => ({
      requirement: requirementTitle(row, copy, locale),
      result: copy.status[String(row.result || '')] || String(row.result || ''),
      evidence: evidenceText(row, copy, locale),
      source: sourceText(row, copy),
    })),
  }
}
