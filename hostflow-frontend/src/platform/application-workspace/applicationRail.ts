import type { Application } from '../../api/types/application'
import type { ApplicationStage } from '../../api/applications'

export type ApplicationRodoStatus =
  | 'sent'
  | 'failed'
  | 'deferred'
  | 'pending_channel'
  | 'pending_policy'
  | 'manual_required'
  | 'source_provided'

export type ApplicationRodoState = {
  status: ApplicationRodoStatus
  satisfied: boolean
  policyBlocked: boolean
}

export type ApplicationCommentEntry = {
  note: string
  at?: string | null
  by?: string | null
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

export function applicationRodoState(application: Application | null | undefined): ApplicationRodoState {
  if (application?.outcome_entity_type === 'candidate' && application.outcome_entity_id) {
    return { status: 'sent', satisfied: true, policyBlocked: false }
  }
  const raw = asRecord(application?.extensions?.rodo)
  const status = String(raw?.status || 'manual_required').trim().toLowerCase() as ApplicationRodoStatus
  const known: ApplicationRodoStatus[] = [
    'sent',
    'failed',
    'deferred',
    'pending_channel',
    'pending_policy',
    'manual_required',
    'source_provided',
  ]
  return {
    status: known.includes(status) ? status : 'manual_required',
    satisfied: Boolean(raw?.satisfied),
    policyBlocked: Boolean(raw?.policy_blocked),
  }
}

export function applicationStageCode(application: Application | null | undefined): string {
  const raw = String(application?.extensions?.stage || '').trim().toLowerCase()
  if (raw) return raw
  const status = application?.status
  if (status === 'rejected') return 'lost'
  if (status === 'completed') return 'converted'
  if (status === 'in_progress') return 'contacted'
  return 'new'
}

export const APPLICATION_STAGE_ACTIONS: ApplicationStage[] = ['contacted', 'qualified', 'lost']

export function applicationComments(application: Application | null | undefined): ApplicationCommentEntry[] {
  const raw = application?.extensions?.comments
  if (!Array.isArray(raw)) return []
  return raw
    .map((item) => {
      const rec = asRecord(item)
      if (!rec) return null
      const note = String(rec.note || '').trim()
      if (!note) return null
      return {
        note,
        at: rec.at != null ? String(rec.at) : null,
        by: rec.by != null ? String(rec.by) : null,
      }
    })
    .filter((x): x is ApplicationCommentEntry => Boolean(x))
}
