import { api } from './client'

export type AcquisitionFunnel = {
  leads?: number
  candidates?: number
  interviews?: number
  offers?: number
  hired?: number
  cost_per_hire?: number | null
}

export type AcquisitionMetrics = {
  responses?: number
  spend?: number
  leads?: number
  cpl?: number | null
  ctr?: number
}

export type AcquisitionNextAction = {
  kind?: string
  title?: string
  severity?: 'info' | 'warning' | 'error'
}

export type AcquisitionRecommendation = {
  kind?: string
  title?: string
  severity?: 'info' | 'warning' | 'error'
  activity_id?: string
}

export type AcquisitionAttentionItem = {
  id: string
  severity: 'error' | 'warning' | 'success' | string
  headline: string
  message: string
  kind?: string
  activity_id?: string
}

export type AcquisitionJournalEntry = {
  id: string
  at: string
  kind: string
  title: string
  activity_id?: string
}

export type AcquisitionActivityActions = {
  open_meta?: boolean
  update_bindings?: boolean
  pause?: boolean
  resume?: boolean
  duplicate?: boolean
  archive?: boolean
}

export type AcquisitionActivity = {
  id: string
  type: string
  channel_type?: string
  name: string
  lifecycle?: 'active' | 'paused' | 'archived' | string
  status: 'active' | 'needs_attention' | 'paused' | 'draft' | string
  status_label?: string
  search_ids?: string[]
  search_titles?: string[]
  meta_external_url?: string | null
  last_sync_at?: string | null
  actions?: AcquisitionActivityActions
  metrics?: {
    today?: AcquisitionMetrics
    period_7d?: AcquisitionMetrics
  }
  metrics_history?: AcquisitionMetricsHistoryRow[]
  funnel?: AcquisitionFunnel
  next_action?: AcquisitionNextAction | null
  public_url?: string
}

export type AcquisitionMetricsHistoryRow = {
  date: string
  spend?: number
  leads?: number
  candidates?: number
  hired?: number
  cpl?: number | null
  ctr?: number
}

export type AcquisitionAudience = {
  countries?: string[]
  age_min?: number | null
  age_max?: number | null
  experience?: string | null
  languages?: string[]
  gender?: string | null
  interests?: string[]
  notes?: string | null
}

export type AcquisitionSyncState = {
  last_sync_at?: string | null
  last_sync_ok_at?: string | null
  last_sync_error?: string | null
  sync_interval_minutes?: number
}

export type AcquisitionOverview = {
  spend_7d?: number
  leads_7d?: number
  cpl_7d?: number | null
  funnel?: AcquisitionFunnel
  recommendations?: AcquisitionRecommendation[]
}

export type AcquisitionReconciliation = {
  status: 'linked' | 'unresolved' | string
  linked_campaign_id?: string | null
  linked_campaign_name?: string | null
  linked_campaign_status?: string | null
  candidate_campaign_ids?: string[]
  reason?: string | null
}

export type AcquisitionSnapshot = {
  version: number
  synced_at?: string | null
  search_fill?: {
    headcount_target?: number | null
    hired?: number
    pct?: number | null
  }
  activities: AcquisitionActivity[]
  channels: AcquisitionActivity[]
  attention?: AcquisitionAttentionItem[]
  journal?: AcquisitionJournalEntry[]
  overview?: AcquisitionOverview
  audience?: AcquisitionAudience
  analytics?: { history?: AcquisitionMetricsHistoryRow[] }
  sync?: AcquisitionSyncState
  warnings?: string[]
  legacy_mode?: boolean
  reconciliation?: AcquisitionReconciliation | null
  marketing_setup_path?: string | null
}

export async function getSearchAcquisition(vacancyId: string): Promise<AcquisitionSnapshot> {
  const { data } = await api.get<AcquisitionSnapshot>(`/vacancies/${encodeURIComponent(vacancyId)}/acquisition`)
  return data
}

export async function syncSearchAcquisition(vacancyId: string): Promise<AcquisitionSnapshot> {
  const { data } = await api.post<AcquisitionSnapshot>(
    `/vacancies/${encodeURIComponent(vacancyId)}/acquisition/sync`,
  )
  return data
}

/** @deprecated C-2: always fails — use Marketing Campaign/Flight setup. */
export async function createAcquisitionActivity(
  _vacancyId: string,
  _payload: { type: string; name: string },
): Promise<AcquisitionActivity> {
  throw new Error(
    'legacy_launch_disabled: create acquisition launches via /app/marketing/new (Campaign → Flight)',
  )
}

/** @deprecated C-2 alias — same hard stop as createAcquisitionActivity. */
export const createAcquisitionChannel = createAcquisitionActivity

/** @deprecated C-7: audience writes disabled — Marketing owns targeting. */
export async function updateAcquisitionAudience(
  _vacancyId: string,
  _payload: AcquisitionAudience,
): Promise<AcquisitionAudience> {
  throw new Error(
    'legacy_launch_disabled: audience edits via /app/marketing (Campaign → Flight)',
  )
}

export async function performAcquisitionActivityAction(
  vacancyId: string,
  activityId: string,
  action: string,
  searchIds?: string[],
): Promise<AcquisitionSnapshot> {
  if (action === 'duplicate' || action === 'update_bindings') {
    throw new Error(
      'legacy_launch_disabled: legacy activity writes via /app/marketing (Campaign → Flight)',
    )
  }
  const { data } = await api.post<AcquisitionSnapshot>(
    `/vacancies/${encodeURIComponent(vacancyId)}/acquisition/activities/${encodeURIComponent(activityId)}/actions`,
    { action, search_ids: searchIds ?? [] },
  )
  return data
}
