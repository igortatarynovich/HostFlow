/**
 * Lead criteria form utilities for vacancy workspace.
 * Handles conversion between form values (string[]) and API payload.
 */

/**
 * Document statuses considered "OK" for lead qualification.
 * Mirrors backend DEFAULT_CANDIDATE_DOCUMENT_OK_STATUSES.
 */
export const DOC_OK_STATUSES = [
  'approved',
  'completed',
  'verified',
  'received',
  'delivered',
  'issued',
  'active',
  'registered',
  'valid',
  'confirmed',
] as const

export type DocOkStatus = (typeof DOC_OK_STATUSES)[number]

/**
 * Form criteria values (arrays, not CSV strings).
 */
export type CriteriaFormValues = {
  minExperienceEuYears: number | null
  requiresDocuments: string[]
  requiresCandidateDocumentsV1: string[]
  candidateDocumentsAllowStatuses: string[]
  allowedGeoCountries: string[]
  blockedGeoCountries: string[]
  preferredDocuments: string[]
  preferredGeoCountries: string[]
  leadFitEvaluationEnabled: boolean
  disableAutoConvertOnFit: boolean
}

/**
 * Parse lead_criteria_v1 from vacancy.extra into form values.
 */
export function criteriaFromExtra(extra: unknown): CriteriaFormValues {
  const defaults: CriteriaFormValues = {
    minExperienceEuYears: null,
    requiresDocuments: [],
    requiresCandidateDocumentsV1: [],
    candidateDocumentsAllowStatuses: [],
    allowedGeoCountries: [],
    blockedGeoCountries: [],
    preferredDocuments: [],
    preferredGeoCountries: [],
    leadFitEvaluationEnabled: false,
    disableAutoConvertOnFit: false,
  }

  if (!extra || typeof extra !== 'object') return defaults

  const ex = extra as Record<string, unknown>
  const crit = ex.lead_criteria_v1 as Record<string, unknown> | undefined

  if (!crit || typeof crit !== 'object') {
    // Check explicit fit evaluation flag
    if (ex.lead_fit_evaluation_enabled_v1 === true) {
      defaults.leadFitEvaluationEnabled = true
    }
    if (ex.leads_auto_convert_on_fit_v1 === false) {
      defaults.disableAutoConvertOnFit = true
    }
    return defaults
  }

  const toArray = (v: unknown): string[] => {
    if (Array.isArray(v)) return v.map(String).filter(Boolean)
    if (typeof v === 'string') return v.split(',').map((s) => s.trim()).filter(Boolean)
    return []
  }

  const toNumber = (v: unknown): number | null => {
    if (v == null) return null
    const n = Number(v)
    return Number.isFinite(n) && n > 0 ? n : null
  }

  return {
    minExperienceEuYears: toNumber(crit.min_experience_eu_years),
    requiresDocuments: toArray(crit.requires_documents),
    requiresCandidateDocumentsV1: toArray(crit.requires_candidate_documents_v1),
    candidateDocumentsAllowStatuses: toArray(crit.candidate_documents_allow_statuses),
    allowedGeoCountries: toArray(crit.allowed_geo_countries).map((s) => s.toUpperCase()),
    blockedGeoCountries: toArray(crit.blocked_geo_countries).map((s) => s.toUpperCase()),
    preferredDocuments: toArray(crit.preferred_documents),
    preferredGeoCountries: toArray(crit.preferred_geo_countries).map((s) => s.toUpperCase()),
    leadFitEvaluationEnabled:
      ex.lead_fit_evaluation_enabled_v1 === true ||
      (Object.keys(crit).length > 0 && ex.lead_fit_evaluation_enabled_v1 !== false),
    disableAutoConvertOnFit: ex.leads_auto_convert_on_fit_v1 === false,
  }
}

/**
 * Apply form criteria values to vacancy payload.extra.lead_criteria_v1.
 * Mutates the payload in place.
 */
export function applyCriteriaToPayload(
  payload: { extra?: Record<string, unknown> },
  values: CriteriaFormValues,
): void {
  if (!payload.extra || typeof payload.extra !== 'object') {
    payload.extra = {}
  }

  const criteria: Record<string, unknown> = {}

  if (values.minExperienceEuYears != null && values.minExperienceEuYears > 0) {
    criteria.min_experience_eu_years = Math.floor(values.minExperienceEuYears)
  }

  if (values.requiresDocuments.length > 0) {
    criteria.requires_documents = values.requiresDocuments
  }

  if (values.requiresCandidateDocumentsV1.length > 0) {
    criteria.requires_candidate_documents_v1 = values.requiresCandidateDocumentsV1
  }

  if (values.candidateDocumentsAllowStatuses.length > 0) {
    criteria.candidate_documents_allow_statuses = values.candidateDocumentsAllowStatuses
  }

  if (values.allowedGeoCountries.length > 0) {
    criteria.allowed_geo_countries = values.allowedGeoCountries
  }

  if (values.blockedGeoCountries.length > 0) {
    criteria.blocked_geo_countries = values.blockedGeoCountries
  }

  if (values.preferredDocuments.length > 0) {
    criteria.preferred_documents = values.preferredDocuments
  }

  if (values.preferredGeoCountries.length > 0) {
    criteria.preferred_geo_countries = values.preferredGeoCountries
  }

  payload.extra.lead_criteria_v1 = criteria
  payload.extra.lead_fit_evaluation_enabled_v1 = values.leadFitEvaluationEnabled

  if (values.disableAutoConvertOnFit) {
    payload.extra.leads_auto_convert_on_fit_v1 = false
  } else {
    delete payload.extra.leads_auto_convert_on_fit_v1
  }
}

/**
 * Summarize criteria for display (counts of mandatory vs preferred).
 */
export type CriteriaSummary = {
  mandatoryDocsCount: number
  mandatoryGeoCount: number
  preferredDocsCount: number
  preferredGeoCount: number
  minExperience: number | null
  hasAnyCriteria: boolean
}

export function summarizeCriteria(values: CriteriaFormValues): CriteriaSummary {
  const mandatoryDocsCount =
    values.requiresDocuments.length + values.requiresCandidateDocumentsV1.length
  const mandatoryGeoCount =
    values.allowedGeoCountries.length + values.blockedGeoCountries.length
  const preferredDocsCount = values.preferredDocuments.length
  const preferredGeoCount = values.preferredGeoCountries.length
  const minExperience = values.minExperienceEuYears

  const hasAnyCriteria =
    mandatoryDocsCount > 0 ||
    mandatoryGeoCount > 0 ||
    preferredDocsCount > 0 ||
    preferredGeoCount > 0 ||
    minExperience != null

  return {
    mandatoryDocsCount,
    mandatoryGeoCount,
    preferredDocsCount,
    preferredGeoCount,
    minExperience,
    hasAnyCriteria,
  }
}
