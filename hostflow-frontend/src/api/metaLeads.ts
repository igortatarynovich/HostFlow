import { api } from './client'
import type {
  MetaAdsMapCreatePayload,
  MetaAdsMapEntry,
  MetaAdsMapUpdatePayload,
  MetaCredentialCreatePayload,
  MetaCredentialRotateResponse,
  MetaCredentialUpdatePayload,
  MetaLeadAdminResponse,
  MetaLeadCredential,
  MetaLeadReroutePayload,
  MetaLeadSettings,
  MetaLeadSettingsPatch,
} from './types'

const BASE = '/settings/leads'

export async function getMetaLeadSettings(): Promise<MetaLeadSettings> {
  const { data } = await api.get(`${BASE}/settings`)
  return data
}

export async function updateMetaLeadSettings(payload: MetaLeadSettingsPatch): Promise<MetaLeadSettings> {
  const { data } = await api.patch(`${BASE}/settings`, payload)
  return data
}

export async function listMetaLeadCredentials(): Promise<MetaLeadCredential[]> {
  const { data } = await api.get(`${BASE}/credentials`)
  return data
}

export async function createMetaLeadCredential(payload: MetaCredentialCreatePayload): Promise<MetaLeadCredential> {
  const { data } = await api.post(`${BASE}/credentials`, payload)
  return data
}

export async function updateMetaLeadCredential(
  credentialId: string,
  payload: MetaCredentialUpdatePayload,
): Promise<MetaLeadCredential> {
  const { data } = await api.patch(`${BASE}/credentials/${credentialId}`, payload)
  return data
}

export async function deleteMetaLeadCredential(credentialId: string): Promise<void> {
  await api.delete(`${BASE}/credentials/${credentialId}`)
}

export async function rotateMetaLeadCredential(credentialId: string): Promise<MetaCredentialRotateResponse> {
  const { data } = await api.post(`${BASE}/credentials/${credentialId}/rotate`)
  return data
}

export async function listMetaAdsMap(opts?: { search?: string; limit?: number }): Promise<MetaAdsMapEntry[]> {
  const params: Record<string, any> = {}
  if (opts?.search) params.search = opts.search
  if (opts?.limit) params.limit = opts.limit
  const { data } = await api.get(`${BASE}/mapping`, { params })
  return data
}

export async function createMetaAdsMap(payload: MetaAdsMapCreatePayload): Promise<MetaAdsMapEntry> {
  const { data } = await api.post(`${BASE}/mapping`, payload)
  return data
}

export async function updateMetaAdsMap(adId: string, payload: MetaAdsMapUpdatePayload): Promise<MetaAdsMapEntry> {
  const { data } = await api.patch(`${BASE}/mapping/${adId}`, payload)
  return data
}

export async function deleteMetaAdsMap(adId: string): Promise<void> {
  await api.delete(`${BASE}/mapping/${adId}`)
}

export async function rerouteMetaLead(leadId: string, payload: MetaLeadReroutePayload): Promise<MetaLeadAdminResponse> {
  const { data } = await api.post(`${BASE}/leads/${leadId}/reroute`, payload)
  return data
}
