import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { api } from './client'

export interface NextActionQuery {
  status?: string | null
  stage?: string | null
  next_action?: string | null
  tab?: string | null
  t_status?: string | null
  t_entity?: string | null
  t_due_bucket?: string | null
}

export interface NextActionGroup {
  id: string
  entity: 'lead' | 'candidate'
  reason: string
  title: string
  count: number
  priority: number
  query: NextActionQuery
  path: string
  locked?: boolean
  required_plan?: string | null
}

export interface LeadNextActionsResponse {
  generated_at: string
  own_company_id?: string | null
  plan_code?: string
  nba_tier?: 'solo' | 'team'
  groups: NextActionGroup[]
}

export async function fetchLeadNextActions(): Promise<LeadNextActionsResponse> {
  const { data } = await api.get<LeadNextActionsResponse>('/next-actions')
  return data
}

/** Build SPA href from NBA `path` + `query` (leads, candidates quick view, tasks inbox). */
export function nbaGroupHref(g: Pick<NextActionGroup, 'path' | 'query'>): string {
  const defaultLeads = CRM_APP_PATHS.leads
  const base = (g.path || defaultLeads).replace(/\/+$/, '') || defaultLeads
  const q = g.query || {}
  const p = new URLSearchParams()
  const pairs: [string, string | null | undefined][] = [
    ['status', q.status],
    ['stage', q.stage],
    ['next_action', q.next_action],
    ['tab', q.tab],
    ['t_status', q.t_status],
    ['t_entity', q.t_entity],
    ['t_due_bucket', q.t_due_bucket],
  ]
  for (const [k, v] of pairs) {
    const s = v != null ? String(v).trim() : ''
    if (s) p.set(k, s)
  }
  const s = p.toString()
  return s ? `${base}?${s}` : base
}

/** SPA path for Leads with the same query keys as GET /leads. */
export function leadsNextActionHref(q: NextActionQuery): string {
  return nbaGroupHref({ path: CRM_APP_PATHS.leads, query: q })
}
