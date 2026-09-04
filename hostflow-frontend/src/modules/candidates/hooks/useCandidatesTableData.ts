import { useCallback, useEffect, useRef, useState } from 'react'
import type { MutableRefObject } from 'react'
import { api, listCandidatesNoNextAction, withTenant } from '../../../api/client'
import { recordPerfMeasurement } from '../../../api/analytics'
import { isCandidateRecruiterIdCanonEnabled } from '../../../utils/featureFlags'
import type { CandidatesListInsights, DateRangeFilter, ListResp, UICandidate, CandidateListCacheEntry } from '../types'

function mapNoNextActionRowToUICandidate(row: Record<string, unknown>): UICandidate {
  const id = String(row.id ?? '')
  const iak = row.intake_application_kind
  const intake_application_kind: UICandidate['intake_application_kind'] =
    iak === 'client' || iak === 'candidate' ? iak : null
  return {
    id,
    first_name: String(row.first_name ?? '').trim() || '—',
    last_name: String(row.last_name ?? '').trim() || '',
    stage: row.stage != null ? String(row.stage) : null,
    manager: row.manager != null ? String(row.manager) : null,
    short_id: row.short_id != null ? String(row.short_id) : null,
    company_id: row.company_id != null ? (String(row.company_id) as UICandidate['company_id']) : null,
    vacancy_id: row.vacancy_id != null ? (String(row.vacancy_id) as UICandidate['vacancy_id']) : null,
    created_at: row.created_at != null ? String(row.created_at) : null,
    updated_at: row.updated_at != null ? String(row.updated_at) : null,
    intake_application_kind,
  }
}
import { getErrorInfo } from '../../../utils/errorHandling'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../../utils/friendlyError'
import { usePlanLimitModal } from '../../../contexts/PlanLimitModalContext'
import { CANDIDATE_CACHE_TTL_MS } from '../constants'

type TFn = (key: string, opts?: any) => string

async function getWithFallbacks<T = any>(
  path: string,
  params: Record<string, any>,
  tenantId?: string | null
) {
  const client = tenantId ? withTenant(tenantId) : api
  const limit = params.limit ?? 50
  const offset = params.offset ?? 0
  const baseParams = { ...params }

  const attempts = [
    { ...baseParams, limit, offset },
    { ...baseParams, limit, skip: offset },
    { ...baseParams, page: Math.floor(offset / limit) + 1, per_page: limit },
    { ...baseParams, limit },
    { ...baseParams },
  ]

  let lastErr: any = null
  for (const p of attempts) {
    try {
      const res = await client.get<T>(path, { params: p })
      return res
    } catch (e: any) {
      const status = e?.response?.status
      if (status && status !== 422) throw e
      lastErr = e
    }
  }
  throw lastErr
}

function normalizeListInsights(raw: unknown): CandidatesListInsights | null {
  if (!raw || typeof raw !== 'object') return null
  const o = raw as Record<string, unknown>
  return {
    total: Number(o.total) || 0,
    new_count: Number(o.new_count) || 0,
    docs_ready: Number(o.docs_ready) || 0,
    docs_attention: Number(o.docs_attention) || 0,
    docs_ordered: Number(o.docs_ordered) || 0,
    docs_incomplete: Number(o.docs_incomplete) || 0,
    ops_in_work: Number(o.ops_in_work) || 0,
    bottleneck_no_contact: Number(o.bottleneck_no_contact) || 0,
    bottleneck_docs_wait: Number(o.bottleneck_docs_wait) || 0,
    bottleneck_interview_pending: Number(o.bottleneck_interview_pending) || 0,
    unassigned_recruiter: Number(o.unassigned_recruiter) || 0,
  }
}

type UseCandidatesTableDataArgs = {
  candidateListCache: Map<string, CandidateListCacheEntry>
  cacheKey: string
  listStorageKey: string
  filtersHydrated: boolean
  limit: number
  t: TFn

  // query/filter state
  q: string
  stageFilter: string[]
  /** ``Candidate.status`` values (GET ``?statuses=``). */
  candidateRowStatusFilter: string[]
  statusReasonFilter: string[]
  tagsFilter: string[]
  vacancyFilter: string[]
  managerFilter: string[]
  docsOrderedFilter: string[]
  handoffStatusFilter: string | null
  contactAttemptsFilter: string | null
  processorFilter: string | null
  /** Hourly risk shadow bucket ISO (GET /candidates shadow_bucket_start) */
  shadowBucketFilter: string | null
  /** Band floor with shadow cohort (low|medium|high|critical); used only when shadowBucketFilter is set */
  shadowBucketMinBand: string | null
  createdRange: DateRangeFilter
  isFavoriteFilter: boolean | null
  /** GET /candidates intake_application_kind=client|candidate */
  intakeApplicationKindFilter: '' | 'client' | 'candidate'

  // tenant scope
  currentTenantId: string | number | null | undefined
  meTenantId: string | number | null | undefined

  // scroll integration
  restoredScrollRef: MutableRefObject<boolean>

  // When integrating incrementally, the page may still own `load()` retry logic.
  // Disable internal "apply from last success" + "retry empty batch" effects to avoid double-fetch.
  disableAutoRetryAndPrevLoadingEffects?: boolean

  /** §2.14: operational queue on main list (same shell as table/kanban entry). */
  operationalQueue?: 'no_next_action' | null
  /** GET /candidates recruiter_unassigned=true */
  recruiterUnassignedFilter?: boolean
}

export function useCandidatesTableData({
  candidateListCache,
  cacheKey,
  listStorageKey,
  filtersHydrated,
  limit,
  t,

  q,
  stageFilter,
  candidateRowStatusFilter,
  statusReasonFilter,
  tagsFilter,
  vacancyFilter,
  managerFilter,
  docsOrderedFilter,
  handoffStatusFilter,
  contactAttemptsFilter,
  processorFilter,
  shadowBucketFilter,
  shadowBucketMinBand,
  createdRange,
  isFavoriteFilter,
  intakeApplicationKindFilter,

  currentTenantId,
  meTenantId,

  restoredScrollRef,
  disableAutoRetryAndPrevLoadingEffects,
  operationalQueue = null,
  recruiterUnassignedFilter = false,
}: UseCandidatesTableDataArgs) {
  const planLimitModal = usePlanLimitModal()
  const [items, setItems] = useState<UICandidate[]>([])
  const [total, setTotal] = useState(0)
  const [listInsights, setListInsights] = useState<CandidatesListInsights | null>(null)
  const [loading, setLoading] = useState(false)
  const [errorText, setErrorText] = useState<FriendlyErrorInfo | null>(null)

  const retriedEmptyItemsRef = useRef(false)
  const loadIdRef = useRef(0)
  const loadInProgressRef = useRef(false)
  const lastSuccessfulListRef = useRef<{
    items: UICandidate[]
    total: number
    insights?: CandidatesListInsights
  } | null>(null)

  // Restore list cache on return / cold start.
  useEffect(() => {
    if (items.length > 0) return
    try {
      const raw = localStorage.getItem(listStorageKey)
      if (!raw) return
      const parsed = JSON.parse(raw)
      if (!parsed || typeof parsed !== 'object') return
      if (typeof parsed.total === 'number' && parsed.total === 0) return

      // Do not restore broken state: total>0 but items empty
      if (typeof parsed.total === 'number' && parsed.total > 0 && (!Array.isArray(parsed.items) || parsed.items.length === 0)) return

      const ts = typeof parsed.timestamp === 'number' ? parsed.timestamp : 0
      if (Date.now() - ts > CANDIDATE_CACHE_TTL_MS) return
      if (!Array.isArray(parsed.items)) return

      const cachedEntry: CandidateListCacheEntry = {
        items: parsed.items as UICandidate[],
        total: typeof parsed.total === 'number' ? parsed.total : parsed.items.length,
        timestamp: ts,
        insights: normalizeListInsights(parsed.insights) ?? undefined,
      }
      candidateListCache.set(cacheKey, cachedEntry)
      lastSuccessfulListRef.current = {
        items: cachedEntry.items,
        total: cachedEntry.total,
        ...(cachedEntry.insights ? { insights: cachedEntry.insights } : {}),
      }
      setItems(cachedEntry.items)
      setTotal(cachedEntry.total)
      setListInsights(cachedEntry.insights ?? null)
      setErrorText(null)
      setLoading(false)
    } catch {
      // ignore malformed storage
    }
  }, [cacheKey, listStorageKey, items.length, candidateListCache])

  const load = useCallback(
    async (options?: { force?: boolean; allowCache?: boolean }) => {
      if (!filtersHydrated) return

      // keep existing behavior: default forceReload=true (to ensure backend masking/scope are consistent)
      const allowCache = options?.allowCache ?? true
      const forceReload = options?.force ?? true

      const cached = allowCache ? candidateListCache.get(cacheKey) : undefined
      const cacheValid = cached && (cached.total === 0 || cached.items.length > 0)
      const cacheIsFresh = cacheValid
        ? Date.now() - cached.timestamp < CANDIDATE_CACHE_TTL_MS && cached.total !== 0
        : false

      const willRefetch = !cacheIsFresh || forceReload

      if (cacheValid && cached.total !== 0) {
        lastSuccessfulListRef.current = {
          items: cached.items,
          total: cached.total,
          ...(cached.insights ? { insights: cached.insights } : {}),
        }
        setItems(cached.items)
        setTotal(cached.total)
        setListInsights(cached.insights ?? null)
        setErrorText(null)
        setLoading(false)
        if (cacheIsFresh && !forceReload) return
      }

      if (loadInProgressRef.current) {
        // avoid parallel fetches
        return
      }

      loadInProgressRef.current = true
      loadIdRef.current += 1
      const myLoadId = loadIdRef.current

      setLoading(true)
      setErrorText(null)

      const perfT0 = typeof performance !== 'undefined' ? performance.now() : Date.now()
      let perfOk = true

      try {
        if (operationalQueue === 'no_next_action') {
          let nextOffset = 0
          let accumulated: UICandidate[] = []
          let totalCount: number | null = null
          const scopeTid = currentTenantId ?? meTenantId
          const scopeTenantIdStr = scopeTid != null ? String(scopeTid) : undefined

          while (true) {
            const res = await listCandidatesNoNextAction({
              limit,
              offset: nextOffset,
              stages: stageFilter.length > 0 ? stageFilter : undefined,
              managerId: managerFilter.length === 1 ? managerFilter[0] : undefined,
              scopeTenantId: scopeTenantIdStr,
              intakeApplicationKind:
                intakeApplicationKindFilter === 'client' || intakeApplicationKindFilter === 'candidate'
                  ? intakeApplicationKindFilter
                  : undefined,
            })
            const dataAny = res as Record<string, unknown>
            const batchRaw = Array.isArray(dataAny?.items) ? (dataAny.items as Record<string, unknown>[]) : []
            const batch = batchRaw.map((r) => mapNoNextActionRowToUICandidate(r))
            if (typeof dataAny?.total === 'number') totalCount = dataAny.total

            accumulated = accumulated.concat(batch)
            nextOffset += batch.length

            if (myLoadId === loadIdRef.current && accumulated.length > 0) {
              setItems(accumulated)
              setTotal(totalCount ?? accumulated.length)
            }

            const reachedEnd =
              batch.length < limit || (totalCount !== null && accumulated.length >= totalCount) || batch.length === 0
            if (reachedEnd) break
          }

          const finalTotal = totalCount ?? accumulated.length
          const persistOk = finalTotal === 0 || accumulated.length > 0

          if (persistOk) {
            const cachedEntry: CandidateListCacheEntry = {
              items: accumulated,
              total: finalTotal,
              timestamp: Date.now(),
            }
            candidateListCache.set(cacheKey, cachedEntry)
            try {
              localStorage.setItem(listStorageKey, JSON.stringify(cachedEntry))
            } catch {
              /* ignore storage errors */
            }
          }

          if (myLoadId === loadIdRef.current) {
            setTotal(finalTotal)
            setItems(accumulated)
            setListInsights(null)
          }

          if (accumulated.length > 0) {
            lastSuccessfulListRef.current = {
              items: accumulated,
              total: finalTotal,
            }
            const toApply = accumulated.slice()
            const tot = finalTotal
            queueMicrotask(() => {
              setItems(toApply)
              setTotal(tot)
              setListInsights(null)
            })
          }
        } else {
          let nextOffset = 0
          let accumulated: UICandidate[] = []
          let totalCount: number | null = null

          // Aggregates from server — only first page
          let normalizedInsights: CandidatesListInsights | null = null

          while (true) {
            const params: Record<string, any> = {
              limit,
              offset: nextOffset,
              order_by: 'created_at',
              desc: true,
              compact: true,
              include_risk: true,
              include_insights: nextOffset === 0,
              q: q || undefined,
              stage: stageFilter.length === 1 ? stageFilter[0] : undefined,
              stages: stageFilter.length > 0 ? stageFilter.join(',') : undefined,
              statuses: candidateRowStatusFilter.length > 0 ? candidateRowStatusFilter.join(',') : undefined,
              status_reason: statusReasonFilter.length > 0 ? statusReasonFilter : undefined,
              tags: tagsFilter.length > 0 ? tagsFilter : undefined,
              vacancy_id: vacancyFilter.length > 0 ? vacancyFilter[0] : undefined,
              vacancy: vacancyFilter.length > 0 ? vacancyFilter.join(',') : undefined,
              // Phase 2.6.G-5 Stage F — canonical filter param is
              // `recruiter_id`; keep `manager_id` as rollback alias
              // (backend accepts both for one release cycle).
              ...(managerFilter.length === 1
                ? isCandidateRecruiterIdCanonEnabled()
                  ? { recruiter_id: managerFilter[0] }
                  : { manager_id: managerFilter[0] }
                : {}),
              documents_ordered: docsOrderedFilter.length === 1 ? docsOrderedFilter[0] : undefined,
              handoff_status: handoffStatusFilter || undefined,
              contact_attempts: contactAttemptsFilter || undefined,
              processor_id: processorFilter || undefined,
            }
            if (shadowBucketFilter && String(shadowBucketFilter).trim()) {
              params.shadow_bucket_start = String(shadowBucketFilter).trim()
              const mb = String(shadowBucketMinBand || 'high').trim().toLowerCase()
              if (['low', 'medium', 'high', 'critical'].includes(mb)) {
                params.shadow_bucket_min_band = mb
              } else {
                params.shadow_bucket_min_band = 'high'
              }
            }
            if (createdRange.from) params.created_from = createdRange.from
            if (createdRange.to) params.created_to = createdRange.to
            if (isFavoriteFilter != null) params.is_favorite = isFavoriteFilter
            if (intakeApplicationKindFilter === 'client' || intakeApplicationKindFilter === 'candidate') {
              params.intake_application_kind = intakeApplicationKindFilter
            }
            if (recruiterUnassignedFilter) {
              params.recruiter_unassigned = true
            }

            const scopeTid = currentTenantId ?? meTenantId
            if (scopeTid) params.scope_tenant_id = typeof scopeTid === 'string' ? scopeTid : String(scopeTid)
            const scopeTidStr = scopeTid != null ? String(scopeTid) : undefined

            const { data } = await getWithFallbacks<ListResp>('/candidates', params, scopeTidStr ?? undefined)

            const dataAny = data as any
            let batch: UICandidate[] =
              Array.isArray(dataAny?.items)
                ? dataAny.items
                : Array.isArray(dataAny?.data)
                  ? dataAny.data
                  : Array.isArray((dataAny?.data as any)?.items)
                    ? (dataAny.data as { items: UICandidate[] }).items
                    : Array.isArray(dataAny?.results)
                      ? dataAny.results
                      : Array.isArray(dataAny)
                        ? dataAny
                        : []

            if (batch.length === 0 && typeof dataAny?.total === 'number' && dataAny.total > 0 && typeof dataAny?.items === 'string') {
              try {
                const parsed = JSON.parse(dataAny.items as string) as UICandidate[]
                if (Array.isArray(parsed)) batch = parsed
              } catch {
                /* ignore */
              }
            }

            const effectiveBatch =
              limit > 1 && typeof dataAny?.total === 'number' && dataAny.total > 1 && batch.length === 1
                ? []
                : batch

            if (nextOffset === 0) {
              normalizedInsights = normalizeListInsights(dataAny?.insights)
            }

            accumulated = accumulated.concat(effectiveBatch)
            if (typeof dataAny?.total === 'number') {
              totalCount = dataAny.total
            }

            // advance offset
            nextOffset += effectiveBatch.length === 0 && batch.length === 1 ? limit : effectiveBatch.length

            // Keep behavior: apply intermediate progress while loading.
            if (myLoadId === loadIdRef.current && accumulated.length > 0) {
              setItems(accumulated)
              setTotal(totalCount ?? accumulated.length)
            }

            // stop condition
            const ignoredOneItem = effectiveBatch.length === 0 && batch.length === 1
            const reachedEnd = ignoredOneItem
              ? false
              : effectiveBatch.length < limit ||
                (totalCount !== null && accumulated.length >= totalCount) ||
                effectiveBatch.length === 0

            if (reachedEnd) break
          }

          const finalTotal = totalCount ?? accumulated.length
          const persistOk = finalTotal === 0 || accumulated.length > 0

          if (persistOk) {
            const cachedEntry: CandidateListCacheEntry = {
              items: accumulated,
              total: finalTotal,
              timestamp: Date.now(),
              ...(normalizedInsights ? { insights: normalizedInsights } : {}),
            }
            candidateListCache.set(cacheKey, cachedEntry)
            try {
              localStorage.setItem(listStorageKey, JSON.stringify(cachedEntry))
            } catch {
              /* ignore storage errors */
            }
          }

          if (myLoadId === loadIdRef.current) {
            setTotal(finalTotal)
            setItems(accumulated)
            setListInsights(normalizedInsights)
          }

          if (accumulated.length > 0) {
            lastSuccessfulListRef.current = {
              items: accumulated,
              total: finalTotal,
              ...(normalizedInsights ? { insights: normalizedInsights } : {}),
            }

            // keep existing behavior: if later state becomes empty, apply from ref.
            const toApply = accumulated.slice()
            const tot = finalTotal
            const ins = normalizedInsights
            queueMicrotask(() => {
              setItems(toApply)
              setTotal(tot)
              setListInsights(ins)
            })
          }
        }
      } catch (e: any) {
        perfOk = false
        const errorInfo = getErrorInfo(e)
        console.error('[Candidates] Load error:', errorInfo)
        // Keep the last successful list on screen. Clearing to [] on timeout
        // produced a 0 → N → 0 flicker while shell pollers were also failing.
        if (myLoadId === loadIdRef.current) {
          const loadFailedTitle =
            t('app.candidates.messages.load_failed') || 'Не удалось загрузить список кандидатов'
          if (planLimitModal?.showPlanLimitIfNeeded(e, loadFailedTitle)) {
            setErrorText(null)
          } else {
            setErrorText(getFriendlyErrorInfo(e, loadFailedTitle, t))
          }
          const fallback = lastSuccessfulListRef.current
          if (fallback && fallback.items.length > 0) {
            setItems(fallback.items)
            setTotal(fallback.total)
            if (fallback.insights) setListInsights(fallback.insights)
          }
        }
      } finally {
        const durationMs = (typeof performance !== 'undefined' ? performance.now() : Date.now()) - perfT0
        const shadowCohort = Boolean(shadowBucketFilter && String(shadowBucketFilter).trim())
        if (willRefetch) {
          void recordPerfMeasurement({
            metricKey: 'candidates.list.load',
            durationMs,
            route: typeof window !== 'undefined' ? `${window.location.pathname}${window.location.search}` : undefined,
            meta: {
              ok: perfOk,
              limit,
              cache: !willRefetch ? 'fresh' : 'refetch',
              include_risk: operationalQueue !== 'no_next_action',
              shadow_cohort: shadowCohort,
              shadow_min_band: shadowCohort ? String(shadowBucketMinBand || 'high').toLowerCase() : undefined,
              operational_queue: operationalQueue ?? undefined,
            },
          }).catch(() => {})
        }

        loadInProgressRef.current = false
        if (myLoadId === loadIdRef.current) setLoading(false)
        if (willRefetch) restoredScrollRef.current = false
      }
    },
    [
      filtersHydrated,
      candidateListCache,
      cacheKey,
      listStorageKey,
      limit,
      t,
      q,
      stageFilter,
      candidateRowStatusFilter,
      statusReasonFilter,
      tagsFilter,
      vacancyFilter,
      managerFilter,
      docsOrderedFilter,
      handoffStatusFilter,
      contactAttemptsFilter,
      processorFilter,
      shadowBucketFilter,
      shadowBucketMinBand,
      createdRange,
      isFavoriteFilter,
      intakeApplicationKindFilter,
      currentTenantId,
      meTenantId,
      planLimitModal,
      restoredScrollRef,
      operationalQueue,
      recruiterUnassignedFilter,
    ],
  )

  // After load: if state empty but last successful response had data — apply it.
  const prevLoadingRef = useRef(loading)
  useEffect(() => {
    if (disableAutoRetryAndPrevLoadingEffects) return
    const wasLoading = prevLoadingRef.current
    prevLoadingRef.current = loading
    if (wasLoading && !loading) {
      const pending = lastSuccessfulListRef.current
      if (pending && pending.items.length > 0 && items.length === 0) {
        setItems(pending.items)
        setTotal(pending.total)
        if (pending.insights) setListInsights(pending.insights)
      }
    }
  }, [loading, items.length, total, disableAutoRetryAndPrevLoadingEffects])

  // Retry once when API returns total>0 but items batch stayed empty.
  useEffect(() => {
    if (disableAutoRetryAndPrevLoadingEffects) return
    if (loading || items.length > 0 || total <= 0 || retriedEmptyItemsRef.current) return
    retriedEmptyItemsRef.current = true
    const tmr = window.setTimeout(() => {
      void load({ force: true, allowCache: false })
    }, 500)
    return () => clearTimeout(tmr)
  }, [total, items.length, loading, load, disableAutoRetryAndPrevLoadingEffects])

  return {
    items,
    setItems,
    total,
    setTotal,
    listInsights,
    setListInsights,
    loading,
    setLoading,
    errorText,
    setErrorText,
    load,
  }
}

