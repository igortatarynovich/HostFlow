import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from 'react'
import api, { createBulkReminders, createReminder } from '../../../api/client'
import {
  ackRiskIntelligenceManagerDigest,
  getRiskIntelligence,
  getRiskIntelligenceManagerDigestQueue,
  getRiskIntelligenceShadowSnapshot,
  getRiskIntelligenceTrends,
  getRiskIntelligenceValidation,
  recordPerfMeasurement,
  type RiskIntelDigestQueueResponse,
  type RiskIntelShadowSnapshotItem,
  type RiskIntelShadowSnapshotResponse,
  type RiskIntelTrendsResponse,
  type RiskIntelValidationResponse,
  type RiskIntelligenceResponse,
} from '../../../api/analytics'
import type { DigestBulkResultReport } from '../internal'
import { formatDigestBulkError } from '../internal'
import type { TranslateFn } from '../../../i18n'

type RiskBand = 'low' | 'medium' | 'high' | 'critical'

export interface UseDashboardRiskOpsOptions {
  canViewRiskOpsUi: boolean
  myUserId: string
  t: TranslateFn
}

export interface UseDashboardRiskOpsResult {
  // Risk intel state
  riskIntel: RiskIntelligenceResponse | null
  riskTrends: RiskIntelTrendsResponse | null
  riskValidation: RiskIntelValidationResponse | null
  riskShadowSnapshot: RiskIntelShadowSnapshotResponse | null
  riskDigestQueue: RiskIntelDigestQueueResponse | null
  riskDigestMinBand: RiskBand
  setRiskDigestMinBand: Dispatch<SetStateAction<RiskBand>>
  riskDigestQueueReadFilter: 'all' | 'unread' | 'read'
  setRiskDigestQueueReadFilter: Dispatch<SetStateAction<'all' | 'unread' | 'read'>>
  riskShadowBucketStart: string | null
  setRiskShadowBucketStart: Dispatch<SetStateAction<string | null>>
  riskIntelLoading: boolean
  riskIntelShadowLoading: boolean

  // Digest state
  digestAckLoading: boolean
  digestHandoffBusyId: string | null
  digestReminderAssigneePick: Record<string, string>
  setDigestReminderAssigneePick: Dispatch<SetStateAction<Record<string, string>>>
  digestBulkSelected: Set<string>
  digestBulkReminderAssignee: string
  setDigestBulkReminderAssignee: Dispatch<SetStateAction<string>>
  digestBulkBusy: boolean
  digestBulkResultReport: DigestBulkResultReport | null
  digestBulkHeadRef: React.RefObject<HTMLInputElement | null>
  digestBulkRowIds: string[]

  // Derived
  filteredDigestBuckets: RiskIntelDigestQueueResponse['buckets']
  latestDigestBucketStart: string | null

  // Actions
  loadRiskOpsCore: () => Promise<void>
  loadRiskShadow: () => Promise<void>
  refreshRiskOpsIntel: () => void
  onManagerDigestAck: () => Promise<void>
  onManagerDigestAckLatest: () => Promise<void>
  onShadowDigestReminder: (
    row: RiskIntelShadowSnapshotItem,
    assigneeChoice?: string | null,
  ) => Promise<void>
  onShadowDigestClaim: (row: RiskIntelShadowSnapshotItem) => Promise<void>
  toggleDigestBulkRow: (id: string) => void
  toggleDigestBulkAll: () => void
  onShadowDigestBulkRemind: () => Promise<void>
  onShadowDigestBulkClaim: () => Promise<void>
}

/**
 * All risk-intelligence + manager-digest state, loaders, and bulk actions
 * from `pages/Dashboard.tsx`. Keeping it together is intentional: the loaders,
 * digest-bucket state, per-row reminder picks, and bulk-actions all share the
 * same `riskShadowSnapshot` / `riskDigestQueue` data source and rely on each
 * other's state (e.g. bulk remind clears selection only on success, bulk claim
 * triggers a `loadRiskShadow` refresh, etc.).
 */
export function useDashboardRiskOps({
  canViewRiskOpsUi,
  myUserId,
  t,
}: UseDashboardRiskOpsOptions): UseDashboardRiskOpsResult {
  const [riskIntel, setRiskIntel] = useState<RiskIntelligenceResponse | null>(null)
  const [riskTrends, setRiskTrends] = useState<RiskIntelTrendsResponse | null>(null)
  const [riskValidation, setRiskValidation] = useState<RiskIntelValidationResponse | null>(null)
  const [riskShadowSnapshot, setRiskShadowSnapshot] =
    useState<RiskIntelShadowSnapshotResponse | null>(null)
  const [riskDigestQueue, setRiskDigestQueue] =
    useState<RiskIntelDigestQueueResponse | null>(null)
  const [riskDigestMinBand, setRiskDigestMinBand] = useState<RiskBand>('high')
  const [riskDigestQueueReadFilter, setRiskDigestQueueReadFilter] =
    useState<'all' | 'unread' | 'read'>('all')
  const [riskShadowBucketStart, setRiskShadowBucketStart] = useState<string | null>(null)
  const [riskIntelLoading, setRiskIntelLoading] = useState(false)
  const [riskIntelShadowLoading, setRiskIntelShadowLoading] = useState(false)
  const [digestAckLoading, setDigestAckLoading] = useState(false)
  const [digestHandoffBusyId, setDigestHandoffBusyId] = useState<string | null>(null)
  const [digestReminderAssigneePick, setDigestReminderAssigneePick] = useState<
    Record<string, string>
  >({})
  const [digestBulkSelected, setDigestBulkSelected] = useState<Set<string>>(() => new Set())
  const [digestBulkReminderAssignee, setDigestBulkReminderAssignee] = useState('')
  const [digestBulkBusy, setDigestBulkBusy] = useState(false)
  const [digestBulkResultReport, setDigestBulkResultReport] =
    useState<DigestBulkResultReport | null>(null)
  const digestBulkHeadRef = useRef<HTMLInputElement>(null)

  const loadRiskOpsCore = useCallback(async () => {
    if (!canViewRiskOpsUi) {
      setRiskIntel(null)
      setRiskTrends(null)
      setRiskValidation(null)
      setRiskDigestQueue(null)
      setRiskShadowSnapshot(null)
      setRiskShadowBucketStart(null)
      return
    }
    const perfT0 = typeof performance !== 'undefined' ? performance.now() : Date.now()
    setRiskIntelLoading(true)
    let settledMeta: {
      baseline: string
      trends: string
      validation: string
      digest_queue: string
    } | null = null
    try {
      const [br, trr, vr, dq] = await Promise.allSettled([
        getRiskIntelligence({ limit: 5000 }),
        getRiskIntelligenceTrends({ days: 30 }),
        getRiskIntelligenceValidation({ cohort_days: 14, lag_days: 7 }),
        getRiskIntelligenceManagerDigestQueue({
          min_band: riskDigestMinBand,
          limit_buckets: 21,
        }),
      ])
      settledMeta = {
        baseline: br.status,
        trends: trr.status,
        validation: vr.status,
        digest_queue: dq.status,
      }
      setRiskIntel(br.status === 'fulfilled' ? br.value : null)
      setRiskTrends(trr.status === 'fulfilled' ? trr.value : null)
      setRiskValidation(vr.status === 'fulfilled' ? vr.value : null)
      setRiskDigestQueue(dq.status === 'fulfilled' ? dq.value : null)
    } finally {
      setRiskIntelLoading(false)
      if (settledMeta) {
        const durationMs =
          (typeof performance !== 'undefined' ? performance.now() : Date.now()) - perfT0
        void recordPerfMeasurement({
          metricKey: 'dashboard.risk_intel.core.load',
          durationMs,
          route:
            typeof window !== 'undefined'
              ? `${window.location.pathname}${window.location.search}`
              : undefined,
          meta: { min_band: riskDigestMinBand, ...settledMeta },
        }).catch(() => {})
      }
    }
  }, [canViewRiskOpsUi, riskDigestMinBand])

  const loadRiskShadow = useCallback(async () => {
    if (!canViewRiskOpsUi) {
      setRiskShadowSnapshot(null)
      return
    }
    const perfT0 = typeof performance !== 'undefined' ? performance.now() : Date.now()
    setRiskIntelShadowLoading(true)
    let ok = false
    try {
      const snap = await getRiskIntelligenceShadowSnapshot({
        limit: 50,
        min_band: riskDigestMinBand,
        bucket_start: riskShadowBucketStart ?? undefined,
      })
      setRiskShadowSnapshot(snap)
      ok = true
    } catch {
      setRiskShadowSnapshot(null)
    } finally {
      const durationMs =
        (typeof performance !== 'undefined' ? performance.now() : Date.now()) - perfT0
      void recordPerfMeasurement({
        metricKey: 'dashboard.risk_intel.shadow_snapshot.load',
        durationMs,
        route:
          typeof window !== 'undefined'
            ? `${window.location.pathname}${window.location.search}`
            : undefined,
        meta: {
          ok,
          min_band: riskDigestMinBand,
          bucket_pinned: Boolean(riskShadowBucketStart),
        },
      }).catch(() => {})
      setRiskIntelShadowLoading(false)
    }
  }, [canViewRiskOpsUi, riskShadowBucketStart, riskDigestMinBand])

  useEffect(() => {
    setRiskShadowBucketStart(null)
    setRiskDigestQueueReadFilter('all')
  }, [riskDigestMinBand])

  const filteredDigestBuckets = useMemo(() => {
    const all = riskDigestQueue?.buckets ?? []
    if (riskDigestQueueReadFilter === 'unread') return all.filter((b) => b.unread)
    if (riskDigestQueueReadFilter === 'read') return all.filter((b) => !b.unread)
    return all
  }, [riskDigestQueue, riskDigestQueueReadFilter])

  useEffect(() => {
    if (!riskDigestQueue || riskShadowBucketStart === null) return
    const visible = filteredDigestBuckets.some((b) => b.bucket_start === riskShadowBucketStart)
    if (!visible) setRiskShadowBucketStart(null)
  }, [filteredDigestBuckets, riskDigestQueue, riskShadowBucketStart])

  const latestDigestBucketStart = riskDigestQueue?.buckets[0]?.bucket_start ?? null

  const onManagerDigestAck = useCallback(async () => {
    const bs = riskShadowSnapshot?.bucket_start
    if (!bs || digestAckLoading) return
    setDigestAckLoading(true)
    try {
      await ackRiskIntelligenceManagerDigest({ bucket_start: bs })
      await loadRiskOpsCore()
    } catch (e) {
      console.error('manager digest ack failed', e)
    } finally {
      setDigestAckLoading(false)
    }
  }, [riskShadowSnapshot?.bucket_start, digestAckLoading, loadRiskOpsCore])

  const onManagerDigestAckLatest = useCallback(async () => {
    const latest = riskDigestQueue?.buckets[0]?.bucket_start
    if (!latest || digestAckLoading) return
    setDigestAckLoading(true)
    try {
      await ackRiskIntelligenceManagerDigest({ bucket_start: latest })
      await loadRiskOpsCore()
    } catch (e) {
      console.error('manager digest ack latest failed', e)
    } finally {
      setDigestAckLoading(false)
    }
  }, [riskDigestQueue?.buckets, digestAckLoading, loadRiskOpsCore])

  const refreshRiskOpsIntel = useCallback(() => {
    void Promise.all([loadRiskOpsCore(), loadRiskShadow()])
  }, [loadRiskOpsCore, loadRiskShadow])

  const onShadowDigestReminder = useCallback(
    async (row: RiskIntelShadowSnapshotItem, assigneeChoice?: string | null) => {
      if (!myUserId || digestHandoffBusyId) return
      const label =
        row.display_name?.trim() ||
        (row.short_id ? `#${row.short_id}` : row.entity_id.slice(0, 8))
      setDigestHandoffBusyId(row.entity_id)
      try {
        const due = new Date(Date.now() + 24 * 60 * 60 * 1000)
        const explicit = assigneeChoice?.trim()
        const recruiter = row.recruiter_id?.trim()
        const assignee_id = explicit || recruiter || undefined
        await createReminder({
          title: t('app.dashboard.risk_intel.shadow_handoff_reminder_title', {
            values: { name: label },
          }),
          description:
            row.drivers?.length
              ? row.drivers.slice(0, 5).join('; ')
              : t('app.dashboard.risk_intel.shadow_handoff_reminder_fallback'),
          type: 'custom',
          entity_type: 'candidate',
          entity_id: row.entity_id,
          due_at: due.toISOString(),
          source: 'risk_intel.shadow_digest',
          ...(assignee_id ? { assignee_id } : {}),
          payload: {
            risk_intel_digest: {
              band: row.band,
              score: row.score,
              bucket_start: riskShadowSnapshot?.bucket_start ?? null,
              assignee_choice: explicit || null,
            },
          },
        })
        setDigestReminderAssigneePick((p) => {
          const next = { ...p }
          delete next[row.entity_id]
          return next
        })
      } catch (e) {
        console.error('shadow digest reminder failed', e)
      } finally {
        setDigestHandoffBusyId(null)
      }
    },
    [myUserId, digestHandoffBusyId, t, riskShadowSnapshot?.bucket_start],
  )

  const onShadowDigestClaim = useCallback(
    async (row: RiskIntelShadowSnapshotItem) => {
      if (!myUserId || digestHandoffBusyId) return
      setDigestHandoffBusyId(row.entity_id)
      try {
        await api.patch(`/candidates/${row.entity_id}`, { recruiter_id: myUserId })
        await loadRiskShadow()
      } catch (e) {
        console.error('shadow digest claim failed', e)
      } finally {
        setDigestHandoffBusyId(null)
      }
    },
    [myUserId, digestHandoffBusyId, loadRiskShadow],
  )

  const digestBulkRowIds = useMemo(
    () => (riskShadowSnapshot?.items ?? []).map((r) => r.entity_id),
    [riskShadowSnapshot?.items],
  )

  useEffect(() => {
    setDigestBulkSelected(new Set())
    setDigestBulkResultReport(null)
  }, [riskShadowSnapshot?.bucket_start])

  useEffect(() => {
    const el = digestBulkHeadRef.current
    if (!el) return
    const n = digestBulkRowIds.length
    const c = digestBulkSelected.size
    el.indeterminate = n > 0 && c > 0 && c < n
  }, [digestBulkRowIds.length, digestBulkSelected.size])

  const toggleDigestBulkRow = useCallback((id: string) => {
    setDigestBulkSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const toggleDigestBulkAll = useCallback(() => {
    setDigestBulkSelected((prev) => {
      if (digestBulkRowIds.length === 0) return new Set()
      const allOn = digestBulkRowIds.every((id) => prev.has(id))
      if (allOn) return new Set()
      return new Set(digestBulkRowIds)
    })
  }, [digestBulkRowIds])

  const onShadowDigestBulkRemind = useCallback(async () => {
    if (!myUserId || digestBulkBusy || !riskShadowSnapshot) return
    const ids = Array.from(digestBulkSelected)
    if (ids.length === 0) return
    const rowById = new Map(riskShadowSnapshot.items.map((r) => [r.entity_id, r]))
    setDigestBulkBusy(true)
    setDigestBulkResultReport(null)
    try {
      const due = new Date(Date.now() + 24 * 60 * 60 * 1000)
      const bulkPick = digestBulkReminderAssignee.trim()
      const sharedPayload = {
        risk_intel_digest: {
          bulk: true,
          bucket_start: riskShadowSnapshot.bucket_start ?? null,
          min_band: riskShadowSnapshot.min_band,
          assignee_choice: bulkPick || null,
        },
      }
      if (bulkPick) {
        const data = await createBulkReminders({
          title: t('app.dashboard.risk_intel.shadow_bulk_reminder_title', {
            values: { n: ids.length },
          }),
          description: t('app.dashboard.risk_intel.shadow_bulk_reminder_desc'),
          type: 'custom',
          entity_type: 'candidate',
          entity_ids: ids,
          due_at: due.toISOString(),
          source: 'risk_intel.shadow_digest',
          assignee_id: bulkPick,
          payload: sharedPayload,
        })
        const results = data?.results ?? []
        const ok = results.filter((r) => r.ok).length
        const fail =
          results.length > 0 ? results.length - ok : ids.length > 0 ? ids.length : 0
        const errors =
          results.length === 0 && ids.length > 0
            ? [t('app.dashboard.risk_intel.shadow_bulk_empty_response')]
            : results
                .filter((r) => !r.ok)
                .map((r) => String(r.error || r.entity_id || 'Unknown').slice(0, 220))
                .slice(0, 5)
        setDigestBulkResultReport({ kind: 'remind', ok, fail, errors })
        if (fail === 0) {
          setDigestBulkSelected(new Set())
          setDigestBulkReminderAssignee('')
        }
      } else {
        const settled = await Promise.allSettled(
          ids.map((id) => {
            const row = rowById.get(id)
            if (!row) return Promise.reject(new Error(`Missing row ${id}`))
            const label =
              row.display_name?.trim() ||
              (row.short_id ? `#${row.short_id}` : row.entity_id.slice(0, 8))
            const recruiter = row.recruiter_id?.trim()
            return createReminder({
              title: t('app.dashboard.risk_intel.shadow_handoff_reminder_title', {
                values: { name: label },
              }),
              description:
                row.drivers?.length
                  ? row.drivers.slice(0, 5).join('; ')
                  : t('app.dashboard.risk_intel.shadow_handoff_reminder_fallback'),
              type: 'custom',
              entity_type: 'candidate',
              entity_id: id,
              due_at: due.toISOString(),
              source: 'risk_intel.shadow_digest',
              ...(recruiter ? { assignee_id: recruiter } : {}),
              payload: {
                risk_intel_digest: {
                  band: row.band,
                  score: row.score,
                  bucket_start: riskShadowSnapshot.bucket_start ?? null,
                  bulk: true,
                },
              },
            })
          }),
        )
        let ok = 0
        let fail = 0
        const errors: string[] = []
        for (const s of settled) {
          if (s.status === 'fulfilled') ok += 1
          else {
            fail += 1
            if (errors.length < 5) errors.push(formatDigestBulkError(s.reason))
          }
        }
        setDigestBulkResultReport({ kind: 'remind', ok, fail, errors })
        if (fail === 0) {
          setDigestBulkSelected(new Set())
          setDigestBulkReminderAssignee('')
        }
      }
    } catch (e) {
      console.error('shadow digest bulk remind failed', e)
      setDigestBulkResultReport({
        kind: 'remind',
        ok: 0,
        fail: ids.length,
        errors: [formatDigestBulkError(e)],
      })
    } finally {
      setDigestBulkBusy(false)
    }
  }, [
    myUserId,
    digestBulkBusy,
    digestBulkSelected,
    digestBulkReminderAssignee,
    t,
    riskShadowSnapshot,
  ])

  const onShadowDigestBulkClaim = useCallback(async () => {
    if (!myUserId || digestBulkBusy) return
    const ids = Array.from(digestBulkSelected)
    if (ids.length === 0) return
    setDigestBulkBusy(true)
    setDigestBulkResultReport(null)
    try {
      const settled = await Promise.allSettled(
        ids.map((id) => api.patch(`/candidates/${id}`, { recruiter_id: myUserId })),
      )
      let ok = 0
      let fail = 0
      const errors: string[] = []
      for (const s of settled) {
        if (s.status === 'fulfilled') ok += 1
        else {
          fail += 1
          if (errors.length < 5) errors.push(formatDigestBulkError(s.reason))
        }
      }
      setDigestBulkResultReport({ kind: 'claim', ok, fail, errors })
      if (ok > 0) await loadRiskShadow()
      if (fail === 0) setDigestBulkSelected(new Set())
    } catch (e) {
      console.error('shadow digest bulk claim failed', e)
      setDigestBulkResultReport({
        kind: 'claim',
        ok: 0,
        fail: ids.length,
        errors: [formatDigestBulkError(e)],
      })
    } finally {
      setDigestBulkBusy(false)
    }
  }, [myUserId, digestBulkBusy, digestBulkSelected, loadRiskShadow])

  return {
    riskIntel,
    riskTrends,
    riskValidation,
    riskShadowSnapshot,
    riskDigestQueue,
    riskDigestMinBand,
    setRiskDigestMinBand,
    riskDigestQueueReadFilter,
    setRiskDigestQueueReadFilter,
    riskShadowBucketStart,
    setRiskShadowBucketStart,
    riskIntelLoading,
    riskIntelShadowLoading,
    digestAckLoading,
    digestHandoffBusyId,
    digestReminderAssigneePick,
    setDigestReminderAssigneePick,
    digestBulkSelected,
    digestBulkReminderAssignee,
    setDigestBulkReminderAssignee,
    digestBulkBusy,
    digestBulkResultReport,
    digestBulkHeadRef,
    digestBulkRowIds,
    filteredDigestBuckets,
    latestDigestBucketStart,
    loadRiskOpsCore,
    loadRiskShadow,
    refreshRiskOpsIntel,
    onManagerDigestAck,
    onManagerDigestAckLatest,
    onShadowDigestReminder,
    onShadowDigestClaim,
    toggleDigestBulkRow,
    toggleDigestBulkAll,
    onShadowDigestBulkRemind,
    onShadowDigestBulkClaim,
  }
}
