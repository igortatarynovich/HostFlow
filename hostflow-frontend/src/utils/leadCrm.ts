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

/** Meta source + non-empty error + failed / needs_routing (list, inbox Fix, full-page Meta panel). */
export function isMetaProblemLead(lead: Lead): boolean {
  const metaSource = String(lead.source || '').toLowerCase() === 'meta'
  const metaErrorCode = (lead.error ?? '').trim()
  return metaSource && metaErrorCode.length > 0 && (lead.status === 'failed' || lead.status === 'needs_routing')
}
