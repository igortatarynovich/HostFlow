import { api } from './client'
import type { NextActionDTO } from './nextAction'

/**
 * G-8 stage 2.0: per-lead primary "next action".
 *
 * Mirrors `backend/app/modules/leads/next_action_api.py`. The backend
 * always returns a DTO (`kind: idle` when there's nothing to do); callers
 * should treat a non-200 as a hard failure rather than as "no action".
 */
export type LeadNextActionDTO = NextActionDTO & { entity_type: 'lead' }

export async function getLeadNextAction(leadId: string): Promise<LeadNextActionDTO> {
  if (!leadId) {
    throw new Error('leadId is required')
  }
  const { data } = await api.get<LeadNextActionDTO>(`/leads/${leadId}/next-action`)
  return data
}
