import { api } from './client'

export type ClientChannelDayItem = {
  id: string
  severity: 'error' | 'warning' | 'success' | 'info' | string
  headline: string
  message: string
  reason?: string
  action_label: string
  target: string
  href: string
  bucket?: 'today' | 'later'
  icon?: string
  kind?: string
  work_kind?: 'call' | 'convert' | 'share' | string | null
  queue?: string[]
  count?: number | null
}

export type ClientChannelDayMode = 'operate' | 'wait_inquiries' | 'idle'

export type ClientChannelWorkspaceStatus = {
  label?: string
  open_inquiries?: number
  today_inquiries?: number
  converted_clients?: number
  public_slug?: string | null
  public_url_path?: string | null
}

export type ClientChannelWorkspacePulse = {
  channel_id: string
  mode: ClientChannelDayMode
  mode_label?: string
  next_action?: ClientChannelDayItem | null
  after_that: ClientChannelDayItem[]
  today: ClientChannelDayItem[]
  later: ClientChannelDayItem[]
  attention: ClientChannelDayItem[]
  status: ClientChannelWorkspaceStatus
}

export async function getClientChannelWorkspacePulse(channelId: string): Promise<ClientChannelWorkspacePulse> {
  const { data } = await api.get<ClientChannelWorkspacePulse>(
    `/settings/leads/company-intake-source-profiles/${encodeURIComponent(channelId)}/workspace`,
  )
  return data
}
