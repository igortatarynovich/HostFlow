/**
 * Mirrors backend `HR_DOCUMENT_REVIEW_ROLES` (hr_officer, administrator).
 * Recruiters/supervisors may have `workforce.manage` in the UI matrix but must not see HR-only review actions.
 */
export function userMayRecordHrDocumentReview(role: string | undefined | null): boolean {
  const r = String(role || '')
    .toLowerCase()
    .trim()
  return (
    r === 'hr_officer' ||
    r === 'people_ops' ||
    r === 'administrator' ||
    r === 'admin' ||
    r === 'owner' ||
    r === 'superadmin'
  )
}
