/**
 * Lead criteria form helpers — arrays in UI, arrays in lead_criteria_v1.
 * Mirrors backend DEFAULT_CANDIDATE_DOCUMENT_OK_STATUSES in lead_criteria_eval.py.
 */

export const DOC_OK_STATUSES = [
  'completed',
  'approved',
  'verified',
  'delivered',
  'received',
  'issued',
  'active',
  'registered',
] as const

export type CriteriaFormSlice = {
  criteria_min_experience_eu_years?: string | number
  criteria_requires_documents: string[]
  criteria_requires_candidate_documents_v1: string[]
  criteria_candidate_documents_allow_statuses: string[]
  criteria_allowed_geo_countries: string[]
  criteria_blocked_geo_countries: string[]
  criteria_preferred_documents: string[]
  criteria_preferred_languages: string[]
  vacancy_disable_auto_convert_on_fit: boolean
  lead_fit_evaluation_enabled: boolean
}

function asStringArray(v: unknown): string[] {
  if (Array.isArray(v)) {
    return v.map((x) => String(x || '').trim()).filter(Boolean)
  }
  if (typeof v === 'string' && v.trim()) {
    return v
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
  }
  return []
}

function parseExtra(raw: unknown): Record<string, unknown> {
  if (!raw) return {}
  if (typeof raw === 'string') {
    try {
      const p = JSON.parse(raw)
      return p && typeof p === 'object' && !Array.isArray(p) ? p : {}
    } catch {
      return {}
    }
  }
  if (typeof raw === 'object' && !Array.isArray(raw)) return raw as Record<string, unknown>
  return {}
}

export function criteriaDefaultsFromSource(source: any): CriteriaFormSlice {
  const extra = parseExtra(source?.extra)
  const crit =
    extra.lead_criteria_v1 && typeof extra.lead_criteria_v1 === 'object'
      ? (extra.lead_criteria_v1 as Record<string, unknown>)
      : {}

  const explicitFit = extra.lead_fit_evaluation_enabled_v1
  let leadFitEvaluationEnabled = false
  if (explicitFit === true) leadFitEvaluationEnabled = true
  else if (explicitFit === false) leadFitEvaluationEnabled = false
  else leadFitEvaluationEnabled = Object.keys(crit).length > 0

  return {
    criteria_min_experience_eu_years:
      crit.min_experience_eu_years != null ? String(crit.min_experience_eu_years) : '',
    criteria_requires_documents: asStringArray(crit.requires_documents),
    criteria_requires_candidate_documents_v1: asStringArray(
      crit.requires_candidate_documents_v1,
    ),
    criteria_candidate_documents_allow_statuses: asStringArray(
      crit.candidate_documents_allow_statuses,
    ),
    criteria_allowed_geo_countries: asStringArray(crit.allowed_geo_countries).map((c) =>
      c.toUpperCase(),
    ),
    criteria_blocked_geo_countries: asStringArray(crit.blocked_geo_countries).map((c) =>
      c.toUpperCase(),
    ),
    criteria_preferred_documents: asStringArray(
      crit.preferred_documents ?? crit.preferred_requires_documents,
    ),
    criteria_preferred_languages: asStringArray(
      crit.preferred_languages ?? crit.requires_languages_any,
    ),
    vacancy_disable_auto_convert_on_fit: extra.leads_auto_convert_on_fit_v1 === false,
    lead_fit_evaluation_enabled: leadFitEvaluationEnabled,
  }
}

export function applyCriteriaToPayload(
  payload: { extra?: Record<string, unknown> | string | null },
  values: CriteriaFormSlice,
): void {
  const prevExtra =
    payload.extra && typeof payload.extra === 'object' && !Array.isArray(payload.extra)
      ? { ...(payload.extra as Record<string, unknown>) }
      : {}

  const prevCrit =
    prevExtra.lead_criteria_v1 &&
    typeof prevExtra.lead_criteria_v1 === 'object' &&
    !Array.isArray(prevExtra.lead_criteria_v1)
      ? { ...(prevExtra.lead_criteria_v1 as Record<string, unknown>) }
      : {}

  const criteria: Record<string, unknown> = { ...prevCrit }

  const minRaw = values.criteria_min_experience_eu_years
  if (minRaw !== undefined && minRaw !== null && String(minRaw).trim() !== '') {
    const parsed = Number(minRaw)
    if (Number.isFinite(parsed) && parsed > 0) {
      criteria.min_experience_eu_years = Math.floor(parsed)
    } else {
      delete criteria.min_experience_eu_years
    }
  } else {
    delete criteria.min_experience_eu_years
  }

  const docs = values.criteria_requires_documents || []
  if (docs.length) criteria.requires_documents = docs
  else delete criteria.requires_documents

  const modDocs = values.criteria_requires_candidate_documents_v1 || []
  if (modDocs.length) criteria.requires_candidate_documents_v1 = modDocs
  else delete criteria.requires_candidate_documents_v1

  const allowSts = values.criteria_candidate_documents_allow_statuses || []
  if (allowSts.length) criteria.candidate_documents_allow_statuses = allowSts
  else delete criteria.candidate_documents_allow_statuses

  const allowedGeo = (values.criteria_allowed_geo_countries || []).map((c) => c.toUpperCase())
  if (allowedGeo.length) criteria.allowed_geo_countries = allowedGeo
  else delete criteria.allowed_geo_countries

  const blockedGeo = (values.criteria_blocked_geo_countries || []).map((c) => c.toUpperCase())
  if (blockedGeo.length) criteria.blocked_geo_countries = blockedGeo
  else delete criteria.blocked_geo_countries

  const prefDocs = values.criteria_preferred_documents || []
  if (prefDocs.length) criteria.preferred_documents = prefDocs
  else delete criteria.preferred_documents

  const prefLang = values.criteria_preferred_languages || []
  if (prefLang.length) {
    criteria.preferred_languages = prefLang
    criteria.requires_languages_any = prefLang
  } else {
    delete criteria.preferred_languages
  }

  prevExtra.lead_criteria_v1 = criteria
  prevExtra.lead_fit_evaluation_enabled_v1 = Boolean(values.lead_fit_evaluation_enabled)
  if (values.vacancy_disable_auto_convert_on_fit) {
    prevExtra.leads_auto_convert_on_fit_v1 = false
  } else {
    delete prevExtra.leads_auto_convert_on_fit_v1
  }

  payload.extra = prevExtra
}

export type AutomationRuleView = {
  id: string
  when: string
  then: string
}

export function buildAutomationRules(
  values: CriteriaFormSlice,
  labels?: { docsWait?: string; rejected?: string; assign?: string },
): AutomationRuleView[] {
  const docsWait = labels?.docsWait || 'Waiting Docs'
  const rejected = labels?.rejected || 'Rejected'
  const assign = labels?.assign || 'Assign Recruiter'
  const rules: AutomationRuleView[] = []

  const allDocs = [
    ...(values.criteria_requires_candidate_documents_v1 || []),
    ...(values.criteria_requires_documents || []),
  ]
  for (const doc of allDocs) {
    rules.push({
      id: `doc-missing-${doc}`,
      when: `Missing document: ${doc}`,
      then: docsWait,
    })
  }

  const minRaw = values.criteria_min_experience_eu_years
  if (minRaw != null && String(minRaw).trim() !== '') {
    const n = Number(minRaw)
    if (Number.isFinite(n) && n > 0) {
      rules.push({
        id: 'exp-min',
        when: `Experience below ${n} year(s)`,
        then: rejected,
      })
    }
  }

  for (const c of values.criteria_blocked_geo_countries || []) {
    rules.push({
      id: `geo-block-${c}`,
      when: `Country blocked: ${c}`,
      then: rejected,
    })
  }

  if (values.criteria_allowed_geo_countries?.length) {
    rules.push({
      id: 'geo-allow',
      when: `Location outside allowed: ${values.criteria_allowed_geo_countries.join(', ')}`,
      then: rejected,
    })
  }

  if (allDocs.length && values.lead_fit_evaluation_enabled) {
    rules.push({
      id: 'docs-ok',
      when: 'All required documents OK',
      then: assign,
    })
  }

  if (values.vacancy_disable_auto_convert_on_fit) {
    rules.push({
      id: 'no-auto-convert',
      when: 'Lead fits criteria',
      then: 'Do not auto-convert (manual review)',
    })
  }

  return rules
}
