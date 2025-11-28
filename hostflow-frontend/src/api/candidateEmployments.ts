import { api } from './client'
import type { CandidateEmploymentRecord, UUID } from './types'

export type CandidateEmploymentPayload = {
  employer_name: string;
  country?: string | null;
  position?: string | null;
  start_date: string;
  end_date?: string | null;
}

const asStringId = (id: UUID | string): string => String(id)

export async function listCandidateEmployments(candidateId: UUID | string): Promise<CandidateEmploymentRecord[]> {
  const { data } = await api.get(`/candidates/${asStringId(candidateId)}/employments`)
  return Array.isArray(data) ? data as CandidateEmploymentRecord[] : []
}

export async function createCandidateEmployment(
  candidateId: UUID | string,
  payload: CandidateEmploymentPayload,
): Promise<CandidateEmploymentRecord> {
  const { data } = await api.post(`/candidates/${asStringId(candidateId)}/employments`, payload)
  return data as CandidateEmploymentRecord
}

export async function updateCandidateEmployment(
  candidateId: UUID | string,
  employmentId: UUID | string,
  payload: CandidateEmploymentPayload,
): Promise<CandidateEmploymentRecord> {
  const { data } = await api.put(
    `/candidates/${asStringId(candidateId)}/employments/${asStringId(employmentId)}`,
    payload,
  )
  return data as CandidateEmploymentRecord
}

export async function deleteCandidateEmployment(candidateId: UUID | string, employmentId: UUID | string): Promise<void> {
  await api.delete(`/candidates/${asStringId(candidateId)}/employments/${asStringId(employmentId)}`)
}
