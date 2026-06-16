export type OperationalSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info'
export type OperationalImpact =
  | 'legal_blocker'
  | 'dispatch_blocker'
  | 'onboarding_delay'
  | 'compliance_risk'
  | 'payroll_risk'
  | 'document_missing'
  | 'verification_pending'
export type OperationalNextAction =
  | 'upload_document'
  | 'verify_document'
  | 'renew_document'
  | 'contact_employee'
  | 'request_signature'
  | 'assign_manager'
  | 'escalate'
  | 'archive_case'
export type OperationalStatus = 'blocked' | 'at_risk' | 'warning' | 'compliant' | 'pending_review'
export type OperationalSignal =
  | 'critical_blockers'
  | 'missing_required'
  | 'expiring_7d'
  | 'expiring_30d'
  | 'verification_needed'
  | 'ready_employees'

export const SEVERITY_META: Record<OperationalSeverity, { tone: string; icon: string; slaHours: number }> = {
  critical: { tone: 'border-rose-200 bg-rose-50 text-rose-900', icon: '!', slaHours: 4 },
  high: { tone: 'border-amber-200 bg-amber-50 text-amber-900', icon: '!', slaHours: 24 },
  medium: { tone: 'border-orange-200 bg-orange-50 text-orange-900', icon: '•', slaHours: 48 },
  low: { tone: 'border-slate-200 bg-slate-50 text-slate-700', icon: '•', slaHours: 120 },
  info: { tone: 'border-brand-200 bg-brand-50 text-brand-900', icon: 'i', slaHours: 168 },
}

export const IMPACT_LABEL: Record<OperationalImpact, string> = {
  legal_blocker: 'Blocks employee activation',
  dispatch_blocker: 'Blocks route assignment',
  onboarding_delay: 'Delays onboarding',
  compliance_risk: 'Compliance risk',
  payroll_risk: 'Payroll risk',
  document_missing: 'Required document missing',
  verification_pending: 'Verification pending',
}

export const NEXT_ACTION_LABEL: Record<OperationalNextAction, string> = {
  upload_document: 'Upload document',
  verify_document: 'Verify document',
  renew_document: 'Renew document',
  contact_employee: 'Contact employee',
  request_signature: 'Request signature',
  assign_manager: 'Assign manager',
  escalate: 'Escalate',
  archive_case: 'Archive case',
}

