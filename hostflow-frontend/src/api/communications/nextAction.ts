/**
 * G-8 stage 2.3: per-thread primary "next action".
 *
 * Mirrors `backend/app/api/v1/communications/routes/threads_next_action.py`.
 * The backend always returns a DTO (`kind: idle` when nothing to do);
 * callers should treat a non-200 as a hard failure rather than as
 * "no action".
 *
 * Note: the canonical thread URL is `/app/inbox/threads/:threadId`; the
 * DTO's `href` (when set) points there so badge clicks land in the
 * inbox detail view.
 */
import api from '../client'
import type { NextActionDTO } from '../nextAction'

export type ThreadNextActionDTO = NextActionDTO & { entity_type: 'thread' }

export async function getThreadNextAction(threadId: string): Promise<ThreadNextActionDTO> {
  if (!threadId) {
    throw new Error('threadId is required')
  }
  const { data } = await api.get<ThreadNextActionDTO>(
    `/communications/threads/${threadId}/next-action`,
  )
  return data
}
