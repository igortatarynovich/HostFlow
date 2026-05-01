import { api } from './client'

export type CalendarProvider = 'google' | 'microsoft'

export type CalendarConnection = {
  id: string
  provider: CalendarProvider
  account_ref?: string | null
  status: string
  user_id?: string | null
  scopes?: string[]
  token_meta?: Record<string, unknown>
  last_error?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export type CalendarSyncCursor = {
  id: string
  connection_id: string
  provider: string
  calendar_ref?: string | null
  cursor?: string | null
  cursor_meta?: Record<string, unknown>
  last_synced_at?: string | null
}

export type CalendarOAuthStartResponse = {
  provider: CalendarProvider
  auth_url: string
  redirect_uri: string
  state: string
  scopes: string[]
}

export type CalendarItem = {
  id: string
  kind: string
  status: string
  title: string
  description?: string | null
  timezone: string
  starts_at: string
  ends_at?: string | null
  all_day: boolean
  linked_entity_type?: string | null
  linked_entity_id?: string | null
  owner_id?: string | null
  assignee_id?: string | null
  source: string
  payload?: Record<string, unknown>
  created_at?: string | null
  updated_at?: string | null
}

export async function listCalendarConnections(provider?: CalendarProvider) {
  const { data } = await api.get<{ items: CalendarConnection[] }>('/calendar/integrations/connections', {
    params: provider ? { provider } : undefined,
  })
  return Array.isArray(data?.items) ? data.items : []
}

export async function startCalendarOAuthQuick(payload: { provider: CalendarProvider }) {
  const { data } = await api.post<CalendarOAuthStartResponse>('/calendar/integrations/oauth/start', payload)
  return data
}

export async function completeCalendarOAuthQuick(payload: {
  provider: CalendarProvider
  code: string
  state: string
  account_ref?: string
}) {
  const { data } = await api.post<CalendarConnection>(
    '/calendar/integrations/connections/oauth/complete/quick',
    payload,
  )
  return data
}

export async function completeCalendarConnectionOAuth(payload: {
  provider: CalendarProvider
  code: string
  client_id: string
  client_secret?: string
  redirect_uri: string
  account_ref?: string
  scopes?: string[]
}) {
  const { data } = await api.post<CalendarConnection>('/calendar/integrations/connections/oauth/complete', payload)
  return data
}

export async function refreshCalendarConnection(
  connectionId: string,
  payload: { client_id: string; client_secret?: string; scope?: string },
) {
  const { data } = await api.post<CalendarConnection>(
    `/calendar/integrations/connections/${encodeURIComponent(connectionId)}/refresh`,
    payload,
  )
  return data
}

export async function deleteCalendarConnection(connectionId: string) {
  await api.delete(`/calendar/integrations/connections/${encodeURIComponent(connectionId)}`)
}

export async function queueCalendarReconcile(payload: { connection_id?: string; provider?: CalendarProvider }) {
  const { data } = await api.post<{ queued: number }>('/calendar/integrations/reconcile', payload)
  return data
}

export async function queueCalendarRenew(payload: { connection_id?: string; provider?: CalendarProvider }) {
  const { data } = await api.post<{ queued: number }>('/calendar/integrations/subscriptions/renew', payload)
  return data
}

export async function listCalendarConnectionCursors(connectionId: string) {
  const { data } = await api.get<{ items: CalendarSyncCursor[] }>(
    `/calendar/integrations/connections/${encodeURIComponent(connectionId)}/cursor`,
  )
  return Array.isArray(data?.items) ? data.items : []
}

export async function listCalendarItems(params?: { start?: string; end?: string }) {
  const { data } = await api.get<{ items: CalendarItem[] }>('/calendar/items', { params })
  return Array.isArray(data?.items) ? data.items : []
}

export async function createCalendarItem(payload: {
  title: string
  description?: string
  kind?: string
  starts_at: string
  ends_at?: string
  timezone?: string
  all_day?: boolean
  assignee_id?: string
  payload?: Record<string, unknown>
}) {
  const { data } = await api.post<CalendarItem>('/calendar/items', payload)
  return data
}

export async function patchCalendarItem(
  itemId: string,
  payload: Partial<{
    title: string
    description: string
    starts_at: string
    ends_at: string
    timezone: string
    all_day: boolean
    assignee_id: string | null
    status: string
    payload: Record<string, unknown>
  }>,
) {
  const { data } = await api.patch<CalendarItem>(`/calendar/items/${encodeURIComponent(itemId)}`, payload)
  return data
}

export async function cancelCalendarItem(itemId: string) {
  const { data } = await api.post<CalendarItem>(`/calendar/items/${encodeURIComponent(itemId)}/cancel`, {})
  return data
}

export async function remindCalendarItem(
  itemId: string,
  payload: { remind_at?: string; channel?: string; note?: string } = {},
) {
  const { data } = await api.post<CalendarItem>(`/calendar/items/${encodeURIComponent(itemId)}/remind`, payload)
  return data
}

export async function assignCalendarItem(itemId: string, payload: { assignee_id: string; note?: string }) {
  const { data } = await api.post<CalendarItem>(`/calendar/items/${encodeURIComponent(itemId)}/assign`, payload)
  return data
}
