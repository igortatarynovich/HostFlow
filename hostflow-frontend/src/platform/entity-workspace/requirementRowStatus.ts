/** Status mark of a requirement row. Owned by the entity record, not by a module. */
export type RequirementRowStatus =
  | 'missing'
  | 'selected'
  | 'pending_review'
  | 'approved'
  | 'rejected'
  | 'superseded'
  | 'not_applicable'

export function requirementStatusBadgeClass(status: RequirementRowStatus): string {
  switch (status) {
    case 'approved':
      return 'border-emerald-200 bg-emerald-50 text-emerald-900'
    case 'pending_review':
      return 'border-amber-200 bg-amber-50 text-amber-950'
    case 'selected':
      return 'border-blue-200 bg-blue-50 text-blue-900'
    case 'rejected':
      return 'border-rose-200 bg-rose-50 text-rose-900'
    case 'superseded':
      return 'border-slate-200 bg-slate-50 text-slate-600'
    case 'not_applicable':
      return 'border-slate-200 bg-white text-slate-500'
    default:
      return 'border-amber-200 bg-amber-50 text-amber-950'
  }
}

export function evidenceStatusLabelKey(status: string): string {
  return `app.candidate_card.requirements_checklist.status.${status}`
}
