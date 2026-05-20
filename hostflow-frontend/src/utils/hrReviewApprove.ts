import type { HrReviewPanel } from '../api/workforce'

/** UI gate aligned with backend finalize_hr_review_can_approve + decision_readiness. */
export function isHrApproveAllowed(panel: HrReviewPanel): boolean {
  if (!panel.can_approve) return false
  const dr = panel.decision_readiness
  if (dr && dr.can_approve === false) return false
  if (dr?.approve_blocked_reason) return false
  if ((panel.failed_required_items?.length ?? 0) > 0) return false
  if ((panel.blockers?.length ?? 0) > 0) return false
  const dv = panel.data_verification_summary
  if (dv && (dv.total ?? 0) > 0 && !dv.ready_for_approval) return false
  const plan = panel.verification_plan
  if (plan) {
    if (plan.can_approve === false || plan.can_complete_verification === false) return false
    if ((plan.blocking_reasons?.length ?? 0) > 0) return false
  }
  return true
}
