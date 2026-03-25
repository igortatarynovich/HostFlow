import { api, docsApi, listReminders } from './client'
import { listCommunicationThreads } from './communications'
import type { Candidate, Company, Document } from './types'
import { buildInboxThreadPath } from '../utils/inboxDeepLinks'

export type GlobalSearchResult = {
  type: 'candidate' | 'company' | 'document' | 'vacancy' | 'invoice' | 'service_order' | 'conversation' | 'task'
  id: string
  title: string
  subtitle?: string
  link: string
}

type VacancyRow = { id?: string; title?: string | null; company_name?: string | null; status?: string | null }

type InvoiceRow = {
  id?: string
  invoice_number?: string
  status?: string
  total_amount?: number | string
  currency?: string
}

type ServiceOrderRow = { id?: string; status?: string; total_amount?: number; currency?: string }

type TaskRow = {
  id?: string
  title?: string | null
  status?: string
  due_at?: string
  type?: string
}

function asArray<T = any>(value: any): T[] {
  if (!value) return []
  if (Array.isArray(value)) return value as T[]
  if (Array.isArray(value?.items)) return value.items as T[]
  if (Array.isArray(value?.data)) return value.data as T[]
  return []
}

const MIN_SEARCH_LENGTH = 2
const PER_TYPE = 4
const MAX_RESULTS = 24
/** Max hits of the same entity type in a row after relevance sort (diversity). */
const MAX_CONSECUTIVE_SAME_TYPE = 2

function normalizeForMatch(s: string): string {
  return s.trim().toLowerCase().replace(/\s+/g, ' ')
}

/**
 * Higher = stronger match on fields we show in the bar (title + subtitle).
 * APIs already filter by q; this re-ranks for display order + interleaving.
 */
function matchQualityScore(qNorm: string, title: string, subtitle?: string): number {
  if (!qNorm) return 0
  const t = normalizeForMatch(title)
  const sub = subtitle ? normalizeForMatch(subtitle) : ''
  const hay = sub ? `${t} ${sub}` : t
  if (t === qNorm) return 100
  if (hay === qNorm) return 95
  if (t.startsWith(qNorm)) return 85
  if (hay.startsWith(qNorm)) return 80
  const idx = hay.indexOf(qNorm)
  if (idx >= 0) {
    const atWord = idx === 0 || hay[idx - 1] === ' '
    return atWord ? 55 : 35
  }
  return 0
}

/**
 * Re-order by match quality, then limit consecutive same-type streaks so the list
 * is not a solid block of one module (cheap merged ranking — no unified API).
 */
function mergeSearchResultsHeuristic(results: GlobalSearchResult[], rawQuery: string, maxOut: number): GlobalSearchResult[] {
  if (results.length <= 1) return results.slice(0, maxOut)
  const qNorm = normalizeForMatch(rawQuery)

  const scored = results.map((r) => ({
    r,
    score: matchQualityScore(qNorm, r.title, r.subtitle),
  }))

  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score
    return a.r.title.localeCompare(b.r.title, undefined, { sensitivity: 'base' })
  })

  const sorted = scored.map((x) => x.r)
  const out: GlobalSearchResult[] = []
  const pool = [...sorted]
  let lastType: GlobalSearchResult['type'] | null = null
  let streak = 0

  while (out.length < maxOut && pool.length > 0) {
    let idx = pool.findIndex((item) => !(item.type === lastType && streak >= MAX_CONSECUTIVE_SAME_TYPE))
    if (idx < 0) idx = 0
    const next = pool.splice(idx, 1)[0]
    out.push(next)
    if (next.type === lastType) streak += 1
    else {
      lastType = next.type
      streak = 1
    }
  }

  return out
}

export type SearchGlobalOptions = {
  /** `team` = tenant-wide reminder list (manager/admin roles on API); default `mine`. */
  reminderAssigneeScope?: 'mine' | 'team'
}

export async function searchGlobal(
  query: string,
  signal?: AbortSignal,
  opts?: SearchGlobalOptions,
): Promise<GlobalSearchResult[]> {
  const q = query.trim()
  if (!q || q.length < MIN_SEARCH_LENGTH) return []
  const base = { q, limit: PER_TYPE, offset: 0 }
  const reminderScope = opts?.reminderAssigneeScope === 'team' ? 'team' : 'mine'

  const [
    candidates,
    companies,
    vacancies,
    documents,
    threads,
    tasks,
    invoices,
    serviceOrders,
  ] = await Promise.allSettled([
    api.get('/candidates/', { params: base, signal }),
    api.get('/companies/', { params: base, signal }),
    api.get('/vacancies/', { params: base, signal }),
    docsApi.get('/documents', { params: { q, limit: PER_TYPE }, signal }),
    listCommunicationThreads({ q, limit: PER_TYPE, offset: 0, signal }),
    listReminders({ q, limit: PER_TYPE, assigneeScope: reminderScope, signal }),
    api.get('/invoices', { params: { ...base, q }, signal }),
    api.get('/service-orders', { params: { q }, signal }),
  ])

  const results: GlobalSearchResult[] = []

  if (candidates.status === 'fulfilled') {
    asArray<Candidate>(candidates.value.data).forEach((item) => {
      if (!item?.id) return
      const title =
        `${item.first_name ?? ''} ${item.last_name ?? ''}`.trim() || item.email || item.short_id || 'Candidate'
      results.push({
        type: 'candidate',
        id: item.id,
        title,
        subtitle: item.stage || item.email || undefined,
        link: `/app/candidates/${item.id}`,
      })
    })
  }

  if (companies.status === 'fulfilled') {
    asArray<Company>(companies.value.data).forEach((item) => {
      if (!item?.id) return
      results.push({
        type: 'company',
        id: item.id,
        title: item.name || item.legal_name || 'Company',
        subtitle: item.city || item.country_code || undefined,
        link: `/app/clients/${item.id}`,
      })
    })
  }

  if (vacancies.status === 'fulfilled') {
    asArray<VacancyRow>(vacancies.value.data).forEach((item) => {
      if (!item?.id) return
      const subtitle = [item.company_name, item.status].filter(Boolean).join(' · ') || undefined
      results.push({
        type: 'vacancy',
        id: item.id,
        title: item.title || 'Vacancy',
        subtitle,
        link: `/app/vacancies/${item.id}`,
      })
    })
  }

  if (documents.status === 'fulfilled') {
    asArray<Document>(documents.value.data).forEach((doc) => {
      if (!doc?.id) return
      const ownerId = doc.candidate_id || doc.owner_id
      results.push({
        type: 'document',
        id: doc.id,
        title: doc.title || doc.custom_name || doc.doc_type || 'Document',
        subtitle: doc.status ? `Status: ${doc.status}` : undefined,
        link: ownerId ? `/app/candidates/${ownerId}/documents` : '/app/documents',
      })
    })
  }

  if (threads.status === 'fulfilled') {
    const items = threads.value.items || []
    items.forEach((t) => {
      if (!t?.id) return
      const title =
        (t.subject && String(t.subject).trim()) ||
        (t.last_message_preview && String(t.last_message_preview).trim().slice(0, 80)) ||
        t.id
      const ch = t.channel ? String(t.channel) : ''
      const preview = t.last_message_preview ? String(t.last_message_preview).trim().slice(0, 120) : ''
      const subtitle = [ch, preview || undefined].filter(Boolean).join(' · ') || undefined
      const cand = t.linked_candidate_id ? String(t.linked_candidate_id).trim() : ''
      const chLower = ch.trim().toLowerCase()
      const scopeChannel = chLower === 'email' ? ('email' as const) : ch ? ('messages' as const) : undefined
      results.push({
        type: 'conversation',
        id: t.id,
        title,
        subtitle,
        link: buildInboxThreadPath(t.id, {
          ...(cand ? { candidateId: cand } : {}),
          ...(scopeChannel ? { channel: scopeChannel } : {}),
        }),
      })
    })
  }

  if (tasks.status === 'fulfilled') {
    const raw = tasks.value as { items?: TaskRow[] } | undefined
    const items = Array.isArray(raw?.items) ? raw.items : []
    items.forEach((r) => {
      if (!r?.id) return
      const title =
        (r.title && String(r.title).trim()) || (r.type ? String(r.type) : 'Task')
      const due = r.due_at ? String(r.due_at).slice(0, 16).replace('T', ' ') : ''
      const subtitle = [r.status, due].filter(Boolean).join(' · ') || undefined
      const taskParams = new URLSearchParams()
      taskParams.set('t_q', q)
      taskParams.set('t_id', String(r.id))
      if (reminderScope === 'team') taskParams.set('t_assignee', 'team')
      results.push({
        type: 'task',
        id: String(r.id),
        title,
        subtitle,
        link: `/app/tasks?${taskParams.toString()}`,
      })
    })
  }

  if (invoices.status === 'fulfilled') {
    asArray<InvoiceRow>(invoices.value.data).forEach((inv) => {
      if (!inv?.id) return
      const amt = inv.total_amount != null ? String(inv.total_amount) : ''
      const cur = inv.currency || ''
      const money = amt && cur ? `${amt} ${cur}` : amt || undefined
      results.push({
        type: 'invoice',
        id: inv.id,
        title: inv.invoice_number || 'Invoice',
        subtitle: [inv.status, money].filter(Boolean).join(' · ') || undefined,
        link: `/app/invoices/${inv.id}`,
      })
    })
  }

  if (serviceOrders.status === 'fulfilled') {
    asArray<ServiceOrderRow>(serviceOrders.value.data).forEach((row) => {
      if (!row?.id) return
      const money =
        row.total_amount != null && row.currency
          ? `${row.total_amount} ${row.currency}`
          : row.total_amount != null
            ? String(row.total_amount)
            : undefined
      const sid = row.id
      const shortId = sid.length > 12 ? `${sid.slice(0, 8)}…` : sid
      results.push({
        type: 'service_order',
        id: sid,
        title: shortId,
        subtitle: [row.status, money].filter(Boolean).join(' · ') || undefined,
        link: `/app/orders?order_id=${encodeURIComponent(sid)}`,
      })
    })
  }

  return mergeSearchResultsHeuristic(results, q, MAX_RESULTS)
}
