import { api } from './client'
import type { DeletionRequest, DeletionDecision } from './types'

function normalizeList(payload: any): DeletionRequest[] {
  if (Array.isArray(payload)) return payload as DeletionRequest[]
  if (payload && Array.isArray(payload.items)) return payload.items as DeletionRequest[]
  return []
}

export async function createDeleteRequest(candidateId: string, reason?: string | null) {
  const { data } = await api.post(`/candidates/${candidateId}/delete-request`, { reason })
  return data as DeletionRequest
}

export async function listDeleteRequests(params?: { status?: 'pending' | 'approved' | 'rejected' }) {
  const { data } = await api.get('/delete-requests', { params })
  return normalizeList(data)
}

export async function approveDeleteRequest(requestId: string, payload?: DeletionDecision) {
  const body = { decision: 'approve', ...(payload ?? {}) }
  const { data } = await api.post(`/delete-requests/${requestId}/approve`, body)
  return data as DeletionRequest
}

export async function rejectDeleteRequest(requestId: string, payload?: DeletionDecision) {
  const body = { decision: 'reject', ...(payload ?? {}) }
  const { data } = await api.post(`/delete-requests/${requestId}/reject`, body)
  return data as DeletionRequest
}
