import { api } from './client'
import type { UUID } from './types'

export type ContactAttemptOut = {
  id: string
  candidate_id: string
  attempt_number: number
  attempted_at: string
  attempted_by_user_id: string | null
  channel: string
  result: string
  note: string | null
}

export type ContactPolicyOut = {
  enabled: boolean
  max_attempts: number
  post_action: string
  stage_code: string | null
  rodo_sent?: boolean
  tracking_disabled_reason?: string | null
}

export type ContactAttemptCreate = {
  channel: 'call' | 'sms' | 'email' | 'whatsapp' | 'messenger'
  result: 'no_answer' | 'answered' | 'wrong_number' | 'unavailable'
  note?: string | null
}

export async function listContactAttempts(candidateId: UUID): Promise<ContactAttemptOut[]> {
  const { data } = await api.get<ContactAttemptOut[]>(
    `/candidates/${candidateId}/contact-attempts`
  )
  return data
}

export async function getContactPolicy(candidateId: UUID): Promise<ContactPolicyOut> {
  const { data } = await api.get<ContactPolicyOut>(
    `/candidates/${candidateId}/contact-attempts/policy`
  )
  return data
}

export async function createContactAttempt(
  candidateId: UUID,
  payload: ContactAttemptCreate
): Promise<ContactAttemptOut> {
  const { data } = await api.post<ContactAttemptOut>(
    `/candidates/${candidateId}/contact-attempts`,
    payload
  )
  return data
}
