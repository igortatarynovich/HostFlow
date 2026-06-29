import type { Lead, LeadStage } from '../api/types'

/** CRM funnel stages for leads (inbox + full-page). */
export const CRM_STAGE_VALUES: LeadStage[] = ['new', 'contacted', 'qualified', 'converted', 'lost']

export function leadAssignmentLocked(lead: Lead | null): boolean {
  const n = lead?.normalized
  if (!n || typeof n !== 'object' || Array.isArray(n)) return false
  const lock = (n as Record<string, unknown>).assignment_lock_v1
  return typeof lock === 'object' && lock !== null && Boolean((lock as { locked?: boolean }).locked)
}

/** POST /leads/:id/process — backend allows meta + csv_import (same mapping pipeline). */
const MANUAL_PROCESS_SOURCES = new Set(['meta', 'csv_import'])

export function leadSupportsManualProcess(lead: Pick<Lead, 'source'> | null): boolean {
  return MANUAL_PROCESS_SOURCES.has(String(lead?.source || '').toLowerCase())
}

export function isClientLead(
  lead: Pick<Lead, 'lead_type' | 'lead_target_type'> | null | undefined,
): boolean {
  return lead?.lead_type === 'client' && lead?.lead_target_type === 'client_lead'
}

export function clientLeadRejectionFinalized(lead: Lead | null | undefined): boolean {
  if (!lead || !isClientLead(lead)) return false
  if (String(lead.status || '').trim().toLowerCase() === 'rejected') return true
  const n = lead.normalized
  if (!n || typeof n !== 'object' || Array.isArray(n)) return false
  const ir = (n as Record<string, unknown>).intake_resolution_v1
  if (!ir || typeof ir !== 'object' || Array.isArray(ir)) return false
  return (
    String((ir as { status?: string }).status || '')
      .trim()
      .toLowerCase() === 'rejected'
  )
}

export function clientLeadIsTerminal(lead: Lead | null | undefined): boolean {
  if (clientLeadRejectionFinalized(lead)) return true
  if (!lead || !isClientLead(lead)) return false
  if (String(lead.stage || '').trim().toLowerCase() === 'lost') return true
  return false
}

/** Meta source + non-empty error + failed / needs_routing (list, inbox Fix, full-page Meta panel). */
export function isMetaProblemLead(lead: Lead): boolean {
  if (isClientLead(lead)) return false
  const metaSource = String(lead.source || '').toLowerCase() === 'meta'
  const metaErrorCode = (lead.error ?? '').trim()
  return metaSource && metaErrorCode.length > 0 && (lead.status === 'failed' || lead.status === 'needs_routing')
}
