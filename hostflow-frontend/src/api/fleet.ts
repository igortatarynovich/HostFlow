import { api } from './client'

export type FleetStatusResponse = {
  ok: boolean
  module: string
}

export async function getFleetStatus(): Promise<FleetStatusResponse> {
  const { data } = await api.get<FleetStatusResponse>('/fleet/status')
  return data
}

export type FleetOperatingLine = {
  id: string
  name: string
  status?: string
  operating_company_id?: string | null
  client_company_id?: string | null
  seasonality_month_factors?: number[] | null
}

export type FleetOperatingLinesResponse = {
  items: FleetOperatingLine[]
}

export async function listFleetOperatingLines(): Promise<FleetOperatingLinesResponse> {
  const { data } = await api.get<FleetOperatingLinesResponse>('/fleet/operating-lines')
  return data
}

export type FleetOperatingLineCreatePayload = {
  name: string
  status?: string
  operating_company_id?: string | null
  client_company_id?: string | null
}

export async function createFleetOperatingLine(
  payload: FleetOperatingLineCreatePayload,
): Promise<FleetOperatingLine> {
  const { data } = await api.post<FleetOperatingLine>('/fleet/operating-lines', payload)
  return data
}

export async function getFleetOperatingLine(lineId: string): Promise<FleetOperatingLine> {
  const { data } = await api.get<FleetOperatingLine>(`/fleet/operating-lines/${encodeURIComponent(lineId)}`)
  return data
}

export type FleetOperatingLinePatchPayload = {
  name?: string
  status?: string
  operating_company_id?: string | null
  client_company_id?: string | null
  seasonality_month_factors?: number[] | null
}

export async function patchFleetOperatingLine(
  lineId: string,
  payload: FleetOperatingLinePatchPayload,
): Promise<FleetOperatingLine> {
  const { data } = await api.patch<FleetOperatingLine>(
    `/fleet/operating-lines/${encodeURIComponent(lineId)}`,
    payload,
  )
  return data
}

export async function deleteFleetOperatingLine(lineId: string): Promise<void> {
  await api.delete(`/fleet/operating-lines/${encodeURIComponent(lineId)}`)
}
