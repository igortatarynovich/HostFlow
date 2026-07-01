import type { HrReviewPanel } from '../api/workforce'

/** True when UI should render Employment Case Workspace (not Employee Operational Profile). */
export function isEmploymentCaseWorkspace(hrReview: HrReviewPanel | null | undefined): boolean {
  if (!hrReview) return false
  if (hrReview.mode === 'employee_profile') return false
  if (hrReview.status === 'approved_for_employment') return false
  return true
}

export function isEmployeeOperationalProfile(hrReview: HrReviewPanel | null | undefined): boolean {
  if (!hrReview) return true
  return !isEmploymentCaseWorkspace(hrReview)
}
