import { api } from './client'

export type TikTokLeadForm = {
  page_id: string
  name: string
  intake_source_profile_id: string
}

export type TikTokConnection = {
  connected: boolean
  status: 'connected' | 'not_connected' | string
  advertiser_id?: string | null
  last_verified_at?: string | null
  last_error?: string | null
  forms: TikTokLeadForm[]
  imported?: number | null
}

const BASE = '/settings/leads/tiktok'

export async function getTikTokConnection(): Promise<TikTokConnection> {
  const { data } = await api.get<TikTokConnection>(BASE)
  return data
}

export async function connectTikTokAccount(payload: {
  advertiser_id: string
  access_token: string
}): Promise<TikTokConnection> {
  const { data } = await api.post<TikTokConnection>(`${BASE}/connect`, payload)
  return data
}

export async function importTikTokLeads(): Promise<TikTokConnection> {
  const { data } = await api.post<TikTokConnection>(`${BASE}/import`)
  return data
}

export async function disconnectTikTokAccount(): Promise<TikTokConnection> {
  const { data } = await api.delete<TikTokConnection>(`${BASE}/connect`)
  return data
}
