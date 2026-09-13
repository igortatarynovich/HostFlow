/**
 * ESO-1 host-binding helpers — pure decisions for HR handoff case UI.
 * SoT: employment_accept_policy.v1 / docs/specs/architecture/employment-accept-policy.md
 */

export type EmploymentAcceptBlocker = {
  code?: string
  message?: string
  [key: string]: unknown
}

export type EmploymentAcceptPolicyView = {
  decision?: string | null
  ritual_accept_forbidden?: boolean | null
  accepted?: boolean | null
  employment_started?: boolean | null
  blockers?: EmploymentAcceptBlocker[] | null
  message?: string | null
}

/** Pending handoffs should apply policy on open — never ritual Accept first. */
export function shouldApplyEmploymentAcceptPolicyOnOpen(args: {
  handoffStatus?: string | null
  operationalQueue?: string | null
}): boolean {
  const status = String(args.handoffStatus || '')
    .trim()
    .toLowerCase()
  const queue = String(args.operationalQueue || '')
    .trim()
    .toLowerCase()
  if (queue === 'awaiting_hr_pickup') return true
  return status === 'pending_review' || status === 'pending'
}

/** Gate 3: auto_accept forbids a separate Accept chore. */
export function isRitualAcceptForbidden(policy: EmploymentAcceptPolicyView | null | undefined): boolean {
  if (!policy) return false
  if (policy.ritual_accept_forbidden === true) return true
  if (policy.accepted === true) return true
  return String(policy.decision || '').trim().toLowerCase() === 'auto_accept'
}

/**
 * Ritual Accept CTA on the HR handoff host — always off for ESO-1 binding.
 * Blockers use retry-policy; auto_accept never shows «Take into HR review».
 */
export function shouldShowRitualAcceptButton(
  _policy?: EmploymentAcceptPolicyView | null,
): false {
  return false
}

export function primaryEmploymentAcceptBlocker(
  policy: EmploymentAcceptPolicyView | null | undefined,
): EmploymentAcceptBlocker | null {
  const blockers = policy?.blockers
  if (!Array.isArray(blockers) || blockers.length === 0) return null
  const first = blockers[0]
  if (!first || typeof first !== 'object') return null
  return first as EmploymentAcceptBlocker
}

export function employmentAcceptBlockerLabel(blocker: EmploymentAcceptBlocker | null | undefined): string {
  if (!blocker) return ''
  const message = String(blocker.message || '').trim()
  if (message) return message
  const code = String(blocker.code || '').trim()
  return code ? code.replace(/_/g, ' ') : ''
}
