/**
 * HR workspace API — **only** `/api/v1/hr/*` and handoff snapshot.
 * Do not use this module for generic candidate CRUD; operational HR screens must not depend on Candidates API.
 */
import { api } from './client'

const HR = '/hr'
const HANDOFFS = '/handoffs'

export type HrAssigneeScope = 'mine' | 'team'

export async function fetchHrDashboardSummary(params?: { assignee_scope?: HrAssigneeScope }) {
  const { data } = await api.get(`${HR}/dashboard/summary`, {
    params: { assignee_scope: params?.assignee_scope ?? 'team' },
  })
  return data
}

export async function fetchHrDashboardHighRisk(params?: {
  horizon_days?: number
  assignee_scope?: HrAssigneeScope
  limit?: number
  offset?: number
}) {
  const { data } = await api.get(`${HR}/dashboard/high-risk`, {
    params: {
      horizon_days: params?.horizon_days ?? 30,
      assignee_scope: params?.assignee_scope ?? 'team',
      limit: params?.limit ?? 50,
      offset: params?.offset ?? 0,
    },
  })
  return data
}

export async function fetchHrHandoffsPending(params?: { limit?: number; offset?: number }) {
  const { data } = await api.get(`${HR}/handoffs/pending`, {
    params: { limit: params?.limit ?? 50, offset: params?.offset ?? 0 },
  })
  return data
}

export async function fetchHrHandoffsAccepted(params?: { limit?: number; offset?: number }) {
  const { data } = await api.get(`${HR}/handoffs/accepted`, {
    params: { limit: params?.limit ?? 50, offset: params?.offset ?? 0 },
  })
  return data
}

export async function fetchHrTasks(params?: { assignee_scope?: HrAssigneeScope; limit?: number }) {
  const { data } = await api.get(`${HR}/tasks`, {
    params: {
      assignee_scope: params?.assignee_scope ?? 'team',
      limit: params?.limit ?? 100,
    },
  })
  return data
}

/** Row from GET `/hr/documents/missing` and `/hr/documents/expiring` (HR legal queues). */
export type HrDocumentQueueItem = {
  handoff_id: string
  workforce_employee_id?: string | null
  candidate_snapshot_summary: Record<string, unknown>
  document_type: string
  current_status: string
  required: boolean
  snapshot_status?: string | null
  expires_at?: string | null
  risk: string
  assignee_user_id?: string | null
  recommended_action: string
}

export type HrDocumentQueueListOut = {
  total: number
  items: HrDocumentQueueItem[]
}

export async function fetchHrDocumentsMissing(params?: {
  assignee_scope?: HrAssigneeScope
  document_type?: string | null
  priority?: string | null
  handoff_id?: string | null
  candidate_id?: string | null
  limit?: number
  offset?: number
}) {
  const { data } = await api.get<HrDocumentQueueListOut>(`${HR}/documents/missing`, {
    params: {
      assignee_scope: params?.assignee_scope ?? 'team',
      document_type: params?.document_type?.trim() || undefined,
      priority: params?.priority?.trim() || undefined,
      handoff_id: params?.handoff_id?.trim() || undefined,
      candidate_id: params?.candidate_id?.trim() || undefined,
      limit: params?.limit ?? 100,
      offset: params?.offset ?? 0,
    },
  })
  return data
}

export async function fetchHrDocumentsExpiring(params?: {
  assignee_scope?: HrAssigneeScope
  horizon_days?: 7 | 30 | 60 | 90
  status?: 'all' | 'expired' | 'expiring'
  document_type?: string | null
  risk?: string | null
  handoff_id?: string | null
  candidate_id?: string | null
  limit?: number
  offset?: number
}) {
  const { data } = await api.get<HrDocumentQueueListOut>(`${HR}/documents/expiring`, {
    params: {
      assignee_scope: params?.assignee_scope ?? 'team',
      horizon_days: params?.horizon_days ?? 30,
      status: params?.status ?? 'all',
      document_type: params?.document_type?.trim() || undefined,
      risk: params?.risk?.trim() || undefined,
      handoff_id: params?.handoff_id?.trim() || undefined,
      candidate_id: params?.candidate_id?.trim() || undefined,
      limit: params?.limit ?? 100,
      offset: params?.offset ?? 0,
    },
  })
  return data
}

export async function fetchHandoffSnapshot(handoffId: string) {
  const { data } = await api.get(`${HANDOFFS}/${encodeURIComponent(handoffId)}/snapshot`)
  return data
}
