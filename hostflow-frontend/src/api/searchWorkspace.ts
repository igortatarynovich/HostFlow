import { api } from './client'

export type SearchDayItem = {
  id: string
  severity: 'error' | 'warning' | 'success' | 'info' | string
  headline: string
  message: string
  reason?: string
  action_label: string
  target: string
  href: string
  bucket?: 'today' | 'later'
  activity_id?: string
  icon?: string
  kind?: string
  work_kind?: 'call' | 'docs' | 'interview' | string | null
  queue?: string[]
  count?: number | null
  activity_name?: string | null
  channel?: string | null
}

export type SearchDayMode = 'operate' | 'wait_leads' | 'near_goal' | 'filled' | 'idle'

export type SearchWorkspaceStatus = {
  label?: string
  fill_pct?: number | null
  hired?: number
  headcount_target?: number | null
  active_candidates?: number
  awaiting_call?: number
  leads_7d?: number
}

export type SearchWorkspacePulse = {
  search_id: string
  mode: SearchDayMode
  mode_label?: string
  next_action?: SearchDayItem | null
  after_that: SearchDayItem[]
  today: SearchDayItem[]
  later: SearchDayItem[]
  attention: SearchDayItem[]
  status: SearchWorkspaceStatus
}

export async function getSearchWorkspacePulse(searchId: string): Promise<SearchWorkspacePulse> {
  const { data } = await api.get<SearchWorkspacePulse>(`/vacancies/${encodeURIComponent(searchId)}/workspace`)
  return data
}
