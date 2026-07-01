import api, { withTenant } from './client'

export type RecruiterAvailabilityState = 'available' | 'paused' | 'offline' | 'vacation'

export type RecruiterAvailabilityTeamItem = {
  user_id: string
  state: RecruiterAvailabilityState | string
}

export type RecruiterAvailabilityTeamResponse = {
  items: RecruiterAvailabilityTeamItem[]
  recruiter_total: number
  available_for_auto_assign_count: number
}

export async function getRecruiterAvailabilityTeam(opts?: { tenantId?: string }): Promise<RecruiterAvailabilityTeamResponse> {
  const client = opts?.tenantId ? withTenant(opts.tenantId) : api
  const { data } = await client.get<RecruiterAvailabilityTeamResponse>('/recruiters/availability')
  return data
}

export async function getMyRecruiterAvailability(opts?: { tenantId?: string }): Promise<{ state: string }> {
  const client = opts?.tenantId ? withTenant(opts.tenantId) : api
  const { data } = await client.get<{ state: string }>('/recruiters/me/availability')
  return data
}

export async function patchMyRecruiterAvailability(
  state: RecruiterAvailabilityState,
  opts?: { tenantId?: string },
): Promise<{ state: string }> {
  const client = opts?.tenantId ? withTenant(opts.tenantId) : api
  const { data } = await client.patch<{ state: string }>('/recruiters/me/availability', { state })
  return data
}

export async function patchRecruiterUserAvailability(
  userId: string,
  state: RecruiterAvailabilityState,
  opts?: { tenantId?: string },
): Promise<{ state: string }> {
  const client = opts?.tenantId ? withTenant(opts.tenantId) : api
  const { data } = await client.patch<{ state: string }>(`/recruiters/users/${userId}/availability`, { state })
  return data
}
