import type { Lead } from '../api/types'
import {
  leadIntakeResolutionRejected,
  leadIntakeWorkspaceBlocking,
  leadRoutingTableAction,
  leadStatusAllowsIntakeDecision,
  manualProcessBlockHint,
} from './intakeResolution'
import {
  clientLeadIsTerminal,
  clientLeadRejectionFinalized,
  isClientLead,
  leadSupportsManualProcess,
} from './leadCrm'

/** Normalize public intake source variants (`public_intake` P5C vs legacy `public-intake` client). */
export function leadPublicIntakeSourceKind(lead: Pick<Lead, 'source'> | null): 'candidate_form' | 'client_legacy' | null {
  const src = String(lead?.source || '').trim().toLowerCase()
  if (src === 'public_intake') return 'candidate_form'
  if (src === 'public-intake') return 'client_legacy'
  return null
}

/** Lead-first public form session still being filled (no CRM intake-decision API). */
export function leadPublicIntakeDraftSession(lead: Pick<Lead, 'source' | 'stage'> | null): boolean {
  if (!lead || leadPublicIntakeSourceKind(lead) !== 'candidate_form') return false
  return String(lead.stage || '').trim().toLowerCase() === 'intake_draft'
}

/** Public intake leads where CRM intake rail must stay read-only (decision on form submit or client branch). */
export function leadRecruitmentPublicIntakeReadonly(lead: Lead | null, isServicesTenant: boolean): boolean {
  if (!lead || isServicesTenant || lead.candidate_id) return false
  const kind = leadPublicIntakeSourceKind(lead)
  if (kind === 'client_legacy') return true
  if (kind === 'candidate_form') return true
  return false
}

export type LeadPublicIntakeReadonlyVariant = 'client_legacy' | 'draft' | 'submitted'

export function leadPublicIntakeReadonlyVariant(lead: Lead | null): LeadPublicIntakeReadonlyVariant {
  if (leadPublicIntakeDraftSession(lead)) return 'draft'
  if (leadPublicIntakeSourceKind(lead) === 'client_legacy') return 'client_legacy'
  return 'submitted'
}

/** One-line vacancy line for compact sticky header on lead intake workspace. */
export function intakeStickyVacancySummary(
  lead: Lead,
  t: (key: string, opts?: { values?: Record<string, string | number> }) => string,
): string {
  const title = (lead.vacancy_title || '').trim()
  const id = lead.vacancy_id != null ? String(lead.vacancy_id).trim() : ''
  const label = title || id
  const hasTarget = Boolean(label)
  if (lead.vacancy_routing_confirmed && hasTarget) {
    return label
  }
  if (hasTarget) {
    return t('app.leads.intake_workspace.sticky.vacancy_route_pending', { values: { title: label } })
  }
  return t('app.leads.intake_workspace.sticky.vacancy_none')
}

/** Short intake-focused label for the leads table (recruitment). */
export function leadIntakeColumnStatusKey(lead: Lead, isServicesTenant: boolean): string {
  if (isServicesTenant) return 'app.leads.intake_workspace.col.services'
  if (isClientLead(lead)) {
    if (clientLeadRejectionFinalized(lead)) return 'app.leads.intake_workspace.col.rejected'
    if (String(lead.stage || '').trim().toLowerCase() === 'lost') return 'app.leads.intake_workspace.col.rejected'
    if (lead.converted_client_id) return 'app.leads.intake_workspace.col.client_converted'
    return 'app.leads.intake_workspace.col.client_lead'
  }
  if (lead.candidate_id) return 'app.leads.intake_workspace.col.converted'
  if (!leadSupportsManualProcess(lead)) return 'app.leads.intake_workspace.col.unsupported'

  const st = String(lead.status || '')
    .trim()
    .toLowerCase()
  if (st === 'duplicate_review') return 'app.leads.intake_workspace.col.duplicate_review'
  if (st === 'failed') return 'app.leads.intake_workspace.col.failed'

  const hint = manualProcessBlockHint(lead)
  if (hint === 'INTAKE_REJECTED') return 'app.leads.intake_workspace.col.rejected'
  if (hint === 'INTAKE_INFO_REQUESTED') return 'app.leads.intake_workspace.col.info_requested'
  if (hint === 'INTAKE_IDENTITY_UNCLEAR') return 'app.leads.intake_workspace.col.identity_unclear'
  if (hint === 'INTAKE_POOL_PATH_REQUIRED') return 'app.leads.intake_workspace.col.pool_path'
  if (hint === 'DUPLICATE_REVIEW_PENDING') return 'app.leads.intake_workspace.col.duplicate_review'
  if (hint === 'VACANCY_NOT_CONFIRMED') return 'app.leads.intake_workspace.col.routing_unconfirmed'
  if (hint === 'INTAKE_ROUTING_INCOMPLETE') return 'app.leads.intake_workspace.col.routing_incomplete'

  if (st === 'needs_routing') return 'app.leads.intake_workspace.col.needs_routing'
  if (st === 'new') return 'app.leads.intake_workspace.col.new'
  if (st === 'processed') return 'app.leads.intake_workspace.col.awaiting_convert'
  if (st === 'duplicated') return 'app.leads.intake_workspace.col.duplicated'
  return 'app.leads.intake_workspace.col.other'
}

export type LeadRowPrimaryAction =
  | { kind: 'confirm_and_process'; vacancyId: string }
  | { kind: 'pick_vacancy' }
  | { kind: 'duplicate_review' }
  | { kind: 'process' }
  | { kind: 'open_candidate'; candidateId: string }
  | { kind: 'none' }

export function leadRowPrimaryAction(lead: Lead, isServicesTenant: boolean): LeadRowPrimaryAction {
  if (isServicesTenant) return { kind: 'none' }
  if (isClientLead(lead)) return { kind: 'none' }
  if (lead.candidate_id) return { kind: 'open_candidate', candidateId: String(lead.candidate_id) }

  const st = String(lead.status || '')
    .trim()
    .toLowerCase()
  if (st === 'duplicate_review') return { kind: 'duplicate_review' }

  if (!leadSupportsManualProcess(lead)) return { kind: 'none' }

  const routing = leadRoutingTableAction(lead, isServicesTenant)
  if (routing.kind === 'confirm_suggested' || routing.kind === 'confirm_current') {
    return { kind: 'confirm_and_process', vacancyId: routing.vacancyId }
  }
  if (routing.kind === 'pick_vacancy') return { kind: 'pick_vacancy' }

  const hint = manualProcessBlockHint(lead)
  if (
    hint === 'INTAKE_REJECTED' ||
    hint === 'INTAKE_INFO_REQUESTED' ||
    hint === 'INTAKE_IDENTITY_UNCLEAR' ||
    hint === 'INTAKE_POOL_PATH_REQUIRED'
  ) {
    return { kind: 'none' }
  }

  if (!lead.candidate_id && (st === 'new' || st === 'processed' || st === 'needs_routing')) {
    return { kind: 'process' }
  }

  return { kind: 'none' }
}

export type IntakeWorkspaceHeader =
  | { tone: 'routing_unconfirmed' }
  | { tone: 'routing_incomplete' }
  | { tone: 'duplicate' }
  | { tone: 'pool_path' }
  | { tone: 'info_requested' }
  | { tone: 'rejected' }
  | { tone: 'identity_unclear' }
  | { tone: 'needs_routing' }
  | { tone: 'ready' }
  | { tone: 'converted' }
  | { tone: 'services' }
  | { tone: 'failed' }

export function intakeWorkspaceHeader(lead: Lead, isServicesTenant: boolean): IntakeWorkspaceHeader {
  if (isServicesTenant) return { tone: 'services' }
  if (lead.candidate_id) return { tone: 'converted' }
  if (String(lead.status || '').toLowerCase() === 'failed') return { tone: 'failed' }

  const st = String(lead.status || '')
    .trim()
    .toLowerCase()
  if (st === 'duplicate_review') return { tone: 'duplicate' }

  const hint = manualProcessBlockHint(lead)
  if (hint === 'VACANCY_NOT_CONFIRMED') return { tone: 'routing_unconfirmed' }
  if (hint === 'INTAKE_ROUTING_INCOMPLETE') return { tone: 'routing_incomplete' }
  if (hint === 'DUPLICATE_REVIEW_PENDING') return { tone: 'duplicate' }
  if (hint === 'INTAKE_POOL_PATH_REQUIRED') return { tone: 'pool_path' }
  if (hint === 'INTAKE_INFO_REQUESTED') return { tone: 'info_requested' }
  if (hint === 'INTAKE_REJECTED') return { tone: 'rejected' }
  if (hint === 'INTAKE_IDENTITY_UNCLEAR') return { tone: 'identity_unclear' }
  if (st === 'needs_routing') return { tone: 'needs_routing' }
  return { tone: 'ready' }
}

/** Recruitment agency CRM uses intake-first workspace (list rail + detail page), not services/client chrome. */
export function recruitmentAgencyIntakeFirstLayout(isServicesTenant: boolean, isClientLead: boolean): boolean {
  return !isServicesTenant && !isClientLead
}

/** True when CRM noise (call/write, stage, reminders…) should stay under “More”, not in the main workspace. */
export function leadIntakeWorkspaceSuppressesCrmChrome(lead: Lead | null, isServicesTenant: boolean): boolean {
  if (!lead || isServicesTenant) return false
  if (lead.candidate_id) return false
  return leadIntakeWorkspaceBlocking(lead, isServicesTenant)
}

/** @deprecated import from `intakeResolution` — re-export for existing call sites. */
export { leadIntakeResolutionRejected } from './intakeResolution'

/** Same shell as `LeadIntakeDecisionRail` — recruitment manual intake list + detail. */
export function leadQueueIntakeShellOk(lead: Lead, isServicesTenant: boolean): boolean {
  if (isServicesTenant || lead.candidate_id) return false
  if (!leadSupportsManualProcess(lead)) return false
  if (leadIntakeResolutionRejected(lead)) return false
  const st = String(lead.status || '')
    .trim()
    .toLowerCase()
  if (st === 'rejected') return false
  const src = String(lead.source || '').toLowerCase()
  const srcOk =
    src === 'meta' ||
    src === 'csv_import' ||
    lead.status === 'needs_routing' ||
    lead.status === 'duplicate_review'
  const hint = manualProcessBlockHint(lead)
  const hintOk =
    hint === 'VACANCY_NOT_CONFIRMED' ||
    hint === 'INTAKE_ROUTING_INCOMPLETE' ||
    hint === 'INTAKE_POOL_PATH_REQUIRED' ||
    hint === 'DUPLICATE_REVIEW_PENDING'
  return Boolean(srcOk || hintOk)
}

/** Pool / request info / reject hotkeys — not while duplicate review queue (qualify first). */
export function leadQueueIntakeShortcutActionsAllowed(lead: Lead | null, isServicesTenant: boolean): boolean {
  if (!lead) return false
  if (String(lead.status || '').trim().toLowerCase() === 'duplicate_review') return false
  return (
    leadQueueIntakeShellOk(lead, isServicesTenant) &&
    leadStatusAllowsIntakeDecision(lead) &&
    !leadIntakeResolutionRejected(lead)
  )
}

export function leadQueueIntakeVacancyPickerAllowed(lead: Lead | null, isServicesTenant: boolean): boolean {
  if (!lead) return false
  return leadQueueIntakeShellOk(lead, isServicesTenant) && !leadIntakeResolutionRejected(lead)
}
