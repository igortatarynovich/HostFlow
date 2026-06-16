import type { HrReviewPanel } from '../../api/workforce'

export function isVerificationPlanReady(panel: HrReviewPanel): boolean {
  if (panel?.verification_plan?.can_approve === true) return true
  const readiness = panel?.decision_readiness
  if (readiness && readiness.can_approve === true) return true
  return false
}

