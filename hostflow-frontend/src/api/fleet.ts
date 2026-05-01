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
}

export type FleetOperatingLinesResponse = {
  items: FleetOperatingLine[]
}

export async function listFleetOperatingLines(): Promise<FleetOperatingLinesResponse> {
  const { data } = await api.get<FleetOperatingLinesResponse>('/fleet/operating-lines')
  return data
}
