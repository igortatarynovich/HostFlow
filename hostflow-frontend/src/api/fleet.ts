import { api } from './client'

export type FleetStatusResponse = {
  ok: boolean
  module: string
}

export async function getFleetStatus(): Promise<FleetStatusResponse> {
  const { data } = await api.get<FleetStatusResponse>('/fleet/status')
  return data
}

export type FleetOverviewResponse = {
  vehicles_total: number
  vehicles_by_status?: Record<string, number>
  trailers_total: number
  trailers_by_status?: Record<string, number>
  drivers_total: number
  drivers_by_status?: Record<string, number>
  drivers_with_workforce_total?: number
  operating_lines_total: number
  operating_lines_by_status?: Record<string, number>
  work_models_total: number
  line_roster_vehicles_total?: number
  line_roster_drivers_total?: number
  line_roster_drivers_effective_today_total?: number
  assignments_total: number
  assignments_by_status?: Record<string, number>
  assignments_overlapping_today_utc_total?: number
  assignments_overlapping_month_utc_total?: number
}

export async function getFleetOverview(): Promise<FleetOverviewResponse> {
  const { data } = await api.get<FleetOverviewResponse>('/fleet/overview')
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

// --- Park: vehicles / trailers / drivers ------------------------------------

export type FleetVehicle = {
  id: string
  internal_code?: string | null
  registration_plate?: string | null
  vin?: string | null
  brand?: string | null
  model?: string | null
  year?: number | null
  status?: string
  operating_company_id?: string | null
  notes?: string | null
}

export type FleetVehiclesResponse = { items: FleetVehicle[] }

export async function listFleetVehicles(): Promise<FleetVehiclesResponse> {
  const { data } = await api.get<FleetVehiclesResponse>('/fleet/vehicles')
  return data
}

export async function createFleetVehicle(payload: Partial<FleetVehicle> & { status?: string }): Promise<FleetVehicle> {
  const { data } = await api.post<FleetVehicle>('/fleet/vehicles', payload)
  return data
}

export async function patchFleetVehicle(id: string, payload: Partial<FleetVehicle>): Promise<FleetVehicle> {
  const { data } = await api.patch<FleetVehicle>(`/fleet/vehicles/${encodeURIComponent(id)}`, payload)
  return data
}

export async function deleteFleetVehicle(id: string): Promise<void> {
  await api.delete(`/fleet/vehicles/${encodeURIComponent(id)}`)
}

export type FleetTrailer = {
  id: string
  internal_code?: string | null
  registration_plate?: string | null
  trailer_type?: string | null
  status?: string
  operating_company_id?: string | null
  notes?: string | null
}

export type FleetTrailersResponse = { items: FleetTrailer[] }

export async function listFleetTrailers(): Promise<FleetTrailersResponse> {
  const { data } = await api.get<FleetTrailersResponse>('/fleet/trailers')
  return data
}

export async function createFleetTrailer(payload: Partial<FleetTrailer> & { status?: string }): Promise<FleetTrailer> {
  const { data } = await api.post<FleetTrailer>('/fleet/trailers', payload)
  return data
}

export async function patchFleetTrailer(id: string, payload: Partial<FleetTrailer>): Promise<FleetTrailer> {
  const { data } = await api.patch<FleetTrailer>(`/fleet/trailers/${encodeURIComponent(id)}`, payload)
  return data
}

export async function deleteFleetTrailer(id: string): Promise<void> {
  await api.delete(`/fleet/trailers/${encodeURIComponent(id)}`)
}

export type FleetDriver = {
  id: string
  display_code?: string | null
  first_name?: string | null
  last_name?: string | null
  status?: string
  operating_company_id?: string | null
  workforce_employee_id?: string | null
  phone?: string | null
  notes?: string | null
}

export type FleetDriversResponse = { items: FleetDriver[] }

export async function listFleetDrivers(): Promise<FleetDriversResponse> {
  const { data } = await api.get<FleetDriversResponse>('/fleet/drivers')
  return data
}

export async function createFleetDriver(payload: Partial<FleetDriver> & { status?: string }): Promise<FleetDriver> {
  const { data } = await api.post<FleetDriver>('/fleet/drivers', payload)
  return data
}

export async function patchFleetDriver(id: string, payload: Partial<FleetDriver>): Promise<FleetDriver> {
  const { data } = await api.patch<FleetDriver>(`/fleet/drivers/${encodeURIComponent(id)}`, payload)
  return data
}

export async function deleteFleetDriver(id: string): Promise<void> {
  await api.delete(`/fleet/drivers/${encodeURIComponent(id)}`)
}
