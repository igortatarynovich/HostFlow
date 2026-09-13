/**
 * ESO-2 + ESO-3 Employment Decision Surface — pure UI decisions.
 * One operator surface: employability → one missing → resolve → auto re-eval.
 * SoT: early_employability.v1 + employment_missing_resolution.v1
 */

export type EmployabilityDecision = 'employable' | 'blocked' | 'insufficient_facts' | string

export type EmploymentNextStep = {
  code?: string
  label?: string
}

export type EarlyEmployabilityView = {
  decision?: EmployabilityDecision | null
  blockers?: Array<{ code?: string; message?: string } | Record<string, unknown>> | null
  requirements?: Array<{ code?: string; message?: string } | Record<string, unknown>> | null
  next_step?: EmploymentNextStep | null
  citizenship?: string | null
  legal_pathway?: { pathway_id?: string; selection_required?: boolean } | null
  pathway_selection_required?: boolean | null
  employee_created?: boolean | null
}

export type ResolutionView = {
  resolution_decision?: string | null
  primary_item?: { code?: string; message?: string } | null
  active_items?: Array<{ code?: string; message?: string } | Record<string, unknown>> | null
  employability?: EarlyEmployabilityView | null
  employee_created?: boolean | null
  rejection_reason?: string | null
}

/** Codes the operator can clear with a minimal patch on this thin surface. */
export const RESOLVABLE_NEXT_STEP_CODES = new Set([
  'provide_citizenship',
  'provide_work_authorization_evidence',
  'provide_employment_country',
])

/** Package-authoritative codes — must not be re-asked as a ritual form when known. */
export const PACKAGE_AUTHORITATIVE_UI_CODES = new Set([
  'person',
  'person_id',
  'candidate_id',
  'citizenship',
  'nationality',
  'first_name',
  'last_name',
  'vacancy_id',
  'employer_id',
  'target_work',
])

export function normalizeDecision(value: unknown): string {
  return String(value || '')
    .trim()
    .toLowerCase()
}

export function decisionSurfaceMode(emp: EarlyEmployabilityView | null | undefined): {
  mode: 'employable' | 'insufficient_facts' | 'blocked' | 'unknown'
  readyForFormalize: boolean
} {
  const d = normalizeDecision(emp?.decision)
  if (d === 'employable') return { mode: 'employable', readyForFormalize: true }
  if (d === 'insufficient_facts') return { mode: 'insufficient_facts', readyForFormalize: false }
  if (d === 'blocked') return { mode: 'blocked', readyForFormalize: false }
  return { mode: 'unknown', readyForFormalize: false }
}

export function primaryNextStep(emp: EarlyEmployabilityView | null | undefined): EmploymentNextStep | null {
  const step = emp?.next_step
  if (!step || typeof step !== 'object') return null
  const code = String(step.code || '').trim()
  if (!code) return null
  return { code, label: String(step.label || '').trim() || code }
}

export function operatorCanResolveCurrentGap(emp: EarlyEmployabilityView | null | undefined): boolean {
  const { mode } = decisionSurfaceMode(emp)
  if (mode !== 'insufficient_facts') return false
  const step = primaryNextStep(emp)
  if (!step) return false
  return RESOLVABLE_NEXT_STEP_CODES.has(normalizeDecision(step.code).replace(/-/g, '_'))
}

/** Blocked with no operator-fixable patch — explain only, no fake CTA. */
export function blockedHasOperatorAction(emp: EarlyEmployabilityView | null | undefined): boolean {
  const { mode } = decisionSurfaceMode(emp)
  if (mode !== 'blocked') return false
  return operatorCanResolveCurrentGap({ ...emp, decision: 'insufficient_facts' })
}

export function shouldShowPathwaySelector(emp: EarlyEmployabilityView | null | undefined): false {
  // Zero-choice: unique pathway is system-set; never offer a pathway/status/permit menu.
  void emp
  return false
}

export function wouldReaskKnownPackageFact(
  fieldCode: string,
  known: { citizenship?: string | null; packageFactCodes?: Iterable<string> },
): boolean {
  const code = normalizeDecision(fieldCode).replace(/-/g, '_')
  if (!PACKAGE_AUTHORITATIVE_UI_CODES.has(code)) return false
  if (code === 'citizenship' || code === 'nationality') {
    return Boolean(String(known.citizenship || '').trim())
  }
  const set = new Set(
    [...(known.packageFactCodes || [])].map((c) => normalizeDecision(c).replace(/-/g, '_')),
  )
  return set.has(code)
}

export function buildResolutionPatchForNextStep(
  nextStepCode: string,
  input: { citizenship?: string; employmentCountry?: string; workAuthorizationPresent?: boolean },
): { facts?: Record<string, unknown>; evidence?: Record<string, unknown> } | null {
  const code = normalizeDecision(nextStepCode).replace(/-/g, '_')
  if (code === 'provide_citizenship') {
    const citizenship = String(input.citizenship || '')
      .trim()
      .toUpperCase()
    if (citizenship.length !== 2) return null
    return { facts: { citizenship } }
  }
  if (code === 'provide_employment_country') {
    const employment_country = String(input.employmentCountry || '')
      .trim()
      .toUpperCase()
    if (!employment_country) return null
    return { facts: { employment_country } }
  }
  if (code === 'provide_work_authorization_evidence') {
    if (!input.workAuthorizationPresent) return null
    return { evidence: { has_work_authorization: true } }
  }
  return null
}

export function employabilityFromResolution(
  resolution: ResolutionView | null | undefined,
  fallback: EarlyEmployabilityView | null | undefined,
): EarlyEmployabilityView | null {
  const emp = resolution?.employability
  if (emp && typeof emp === 'object') return emp as EarlyEmployabilityView
  return fallback ?? null
}

export function assertNoEmployeeCreated(
  emp: EarlyEmployabilityView | null | undefined,
  resolution?: ResolutionView | null,
): boolean {
  if (emp?.employee_created === true) return false
  if (resolution?.employee_created === true) return false
  return true
}
