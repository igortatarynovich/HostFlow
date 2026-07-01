import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { getOnboardingStatus, type OnboardingStatus } from '../../../api/client'
import {
  getTrialRetentionReport,
  recordTrialRetentionEvent,
  type TrialRetentionReport,
} from '../../../api/analytics'
import type { BillingGate } from '../../../api/billing'
import {
  BILLING_SUBSCRIPTION_UPDATED_EVENT,
  getBillingSubscriptionCached,
} from '../../../api/billingSubscriptionCache'
import { ACTIVATION_PATHS, getRetentionNextPath, getRetentionStepKey } from '../../../app/activationRoutes'
import type { TranslateFn } from '../../../i18n'
import { DAY_MS } from '../constants'
import type { TrialRetentionDay } from '../internal'

type TrialTone = 'normal' | 'warning' | 'critical'
type RetentionAction = 'impression' | 'cta_click' | 'dismiss'

export interface UseDashboardRetentionOptions {
  canManageBilling: boolean
  isTrialTenant: boolean
  tenant: { status?: string | null; created_at?: string | null } | null | undefined
  tenantId: string
  t: TranslateFn
}

export interface RetentionNudge {
  day: TrialRetentionDay
  dayKey: 'd1' | 'd2' | 'd3' | 'd7'
  activationDone: boolean
  href: (typeof ACTIVATION_PATHS)[keyof typeof ACTIVATION_PATHS] | string
  stepKey: ReturnType<typeof getRetentionStepKey>
}

export interface RetentionReportRow {
  key: 'd1' | 'd2' | 'd3' | 'd7'
  label: string
  impression: number
  ctaClick: number
  dismiss: number
  ctr: number
}

export interface TrialCenterClassMap {
  wrapper: string
  badge: string
  title: string
  subtitle: string
  legal: string
  urgency: string
}

export interface UseDashboardRetentionResult {
  trialEndsAt: string | null
  billingGate: BillingGate | null
  retentionStatus: OnboardingStatus | null
  retentionDismissed: boolean
  retentionReport: TrialRetentionReport | null
  retentionReportLoading: boolean
  trialDaysLeft: number | null
  trialTone: TrialTone
  showTrialPanel: boolean
  trialCenterClasses: TrialCenterClassMap
  retentionReportRows: RetentionReportRow[]
  trialAgeDays: number | null
  retentionDay: TrialRetentionDay | null
  retentionNextHref: string
  retentionStepKey: ReturnType<typeof getRetentionStepKey>
  retentionNudge: RetentionNudge | null
  dismissRetentionNudge: () => void
  trackRetentionEvent: (
    action: RetentionAction,
    payload?: { day?: TrialRetentionDay; stepKey?: string; href?: string; activationDone?: boolean },
  ) => void
}

/**
 * Trial-status + activation-retention cluster:
 * - Live billing subscription mirror (trial ends at, plan gate)
 * - Onboarding status fetch + day-bucket retention nudge
 * - 30-day retention KPI report (impressions / CTA / dismiss / CTR)
 * - Persistent dismiss state via localStorage
 * - Analytics event recording (dataLayer + backend perf metric)
 */
export function useDashboardRetention({
  canManageBilling,
  isTrialTenant,
  tenant,
  tenantId,
  t,
}: UseDashboardRetentionOptions): UseDashboardRetentionResult {
  const [trialEndsAt, setTrialEndsAt] = useState<string | null>(null)
  const [billingGate, setBillingGate] = useState<BillingGate | null>(null)
  const [retentionStatus, setRetentionStatus] = useState<OnboardingStatus | null>(null)
  const [retentionDismissed, setRetentionDismissed] = useState(false)
  const retentionImpressionRef = useRef<string | null>(null)
  const [retentionReport, setRetentionReport] = useState<TrialRetentionReport | null>(null)
  const [retentionReportLoading, setRetentionReportLoading] = useState(false)

  useEffect(() => {
    if (!canManageBilling) {
      setTrialEndsAt(null)
      setBillingGate(null)
      return
    }
    let cancelled = false
    const loadBillingSubscription = async () => {
      try {
        const subscription = await getBillingSubscriptionCached()
        if (!cancelled) {
          setTrialEndsAt(subscription?.trial_ends_at || null)
          setBillingGate(subscription?.gate ?? null)
        }
      } catch {
        if (!cancelled) {
          setTrialEndsAt(null)
          setBillingGate(null)
        }
      }
    }
    void loadBillingSubscription()
    const onBillingUpdated = () => {
      void loadBillingSubscription()
    }
    window.addEventListener(BILLING_SUBSCRIPTION_UPDATED_EVENT, onBillingUpdated)
    return () => {
      cancelled = true
      window.removeEventListener(BILLING_SUBSCRIPTION_UPDATED_EVENT, onBillingUpdated)
    }
  }, [canManageBilling])

  const trialDaysLeft = useMemo(() => {
    if (!trialEndsAt) return null
    const ends = new Date(trialEndsAt)
    if (Number.isNaN(ends.getTime())) return null
    const diffMs = ends.getTime() - Date.now()
    return Math.max(0, Math.ceil(diffMs / DAY_MS))
  }, [trialEndsAt])

  const trialTone = useMemo<TrialTone>(() => {
    if (billingGate?.trial_urgent) return 'critical'
    if (trialDaysLeft == null) return 'normal'
    if (trialDaysLeft <= 2) return 'critical'
    if (trialDaysLeft <= 7) return 'warning'
    return 'normal'
  }, [billingGate?.trial_urgent, trialDaysLeft])

  const showTrialPanel = useMemo(
    () =>
      Boolean(canManageBilling) &&
      (isTrialTenant ||
        Boolean(billingGate?.trial_active) ||
        Boolean(billingGate?.trial_grace_active)),
    [canManageBilling, isTrialTenant, billingGate?.trial_active, billingGate?.trial_grace_active],
  )

  const trialCenterClasses = useMemo<TrialCenterClassMap>(() => {
    if (trialTone === 'critical') {
      return {
        wrapper: 'rounded-xl border border-rose-300 bg-rose-50 p-4 shadow-sm',
        badge: 'text-xs font-semibold uppercase tracking-wide text-rose-800',
        title: 'text-sm font-semibold text-rose-950',
        subtitle: 'text-xs text-rose-900/90',
        legal: 'mt-2 text-xs text-rose-900/90',
        urgency:
          'inline-flex items-center rounded-md border border-rose-300 bg-rose-100 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-rose-800',
      }
    }
    if (trialTone === 'warning') {
      return {
        wrapper: 'rounded-xl border border-amber-300 bg-amber-50 p-4 shadow-sm',
        badge: 'text-xs font-semibold uppercase tracking-wide text-amber-800',
        title: 'text-sm font-semibold text-amber-950',
        subtitle: 'text-xs text-amber-900/90',
        legal: 'mt-2 text-xs text-amber-900/90',
        urgency:
          'inline-flex items-center rounded-md border border-amber-300 bg-amber-100 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-amber-800',
      }
    }
    return {
      wrapper: 'rounded-xl border border-emerald-300 bg-emerald-50 p-4 shadow-sm',
      badge: 'text-xs font-semibold uppercase tracking-wide text-emerald-800',
      title: 'text-sm font-semibold text-emerald-950',
      subtitle: 'text-xs text-emerald-900/90',
      legal: 'mt-2 text-xs text-emerald-900/90',
      urgency:
        'inline-flex items-center rounded-md border border-emerald-300 bg-emerald-100 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-800',
    }
  }, [trialTone])

  const retentionReportRows = useMemo<RetentionReportRow[]>(() => {
    const source = retentionReport?.buckets ?? []
    const order: Array<'d1' | 'd2' | 'd3' | 'd7'> = ['d1', 'd2', 'd3', 'd7']
    const labels: Record<string, string> = {
      d1: t('app.dashboard.trial_center.retention.day1'),
      d2: t('app.dashboard.trial_center.retention.day2'),
      d3: t('app.dashboard.trial_center.retention.day3'),
      d7: t('app.dashboard.trial_center.retention.day7'),
    }
    const map = new Map(source.map((row) => [row.day_bucket, row]))
    return order.map((key) => {
      const row = map.get(key)
      return {
        key,
        label: labels[key],
        impression: row?.impression ?? 0,
        ctaClick: row?.cta_click ?? 0,
        dismiss: row?.dismiss ?? 0,
        ctr: row?.ctr_percent ?? 0,
      }
    })
  }, [retentionReport?.buckets, t])

  useEffect(() => {
    if (!isTrialTenant) {
      setRetentionStatus(null)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const data = await getOnboardingStatus()
        if (!cancelled) {
          setRetentionStatus(data)
        }
      } catch {
        if (!cancelled) {
          setRetentionStatus(null)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [isTrialTenant])

  useEffect(() => {
    if (!isTrialTenant || !canManageBilling) {
      setRetentionReport(null)
      setRetentionReportLoading(false)
      return
    }
    let cancelled = false
    setRetentionReportLoading(true)
    ;(async () => {
      try {
        const data = await getTrialRetentionReport({ days: 30 })
        if (!cancelled) {
          setRetentionReport(data)
        }
      } catch {
        if (!cancelled) {
          setRetentionReport(null)
        }
      } finally {
        if (!cancelled) {
          setRetentionReportLoading(false)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [canManageBilling, isTrialTenant])

  const trialAgeDays = useMemo(() => {
    const createdAtRaw = String(tenant?.created_at || '').trim()
    if (!createdAtRaw) return null
    const createdAt = new Date(createdAtRaw)
    if (Number.isNaN(createdAt.getTime())) return null
    const diffMs = Date.now() - createdAt.getTime()
    return Math.max(0, Math.floor(diffMs / DAY_MS))
  }, [tenant?.created_at])

  const retentionDay = useMemo<TrialRetentionDay | null>(() => {
    if (trialAgeDays == null) return null
    if (trialAgeDays >= 7) return 7
    if (trialAgeDays >= 3) return 3
    if (trialAgeDays >= 2) return 2
    if (trialAgeDays >= 1) return 1
    return null
  }, [trialAgeDays])

  const retentionDismissKey = useMemo(() => {
    if (!tenantId || retentionDay == null) return null
    return `hf:trial-retention:${tenantId}:d${retentionDay}`
  }, [tenantId, retentionDay])

  useEffect(() => {
    if (!retentionDismissKey) {
      setRetentionDismissed(false)
      return
    }
    try {
      const raw = localStorage.getItem(retentionDismissKey)
      setRetentionDismissed(raw === '1')
    } catch {
      setRetentionDismissed(false)
    }
  }, [retentionDismissKey])

  const dismissRetentionNudge = useCallback(() => {
    if (!retentionDismissKey) return
    try {
      localStorage.setItem(retentionDismissKey, '1')
    } catch {
      /* ignore */
    }
    setRetentionDismissed(true)
  }, [retentionDismissKey])

  const retentionNextHref = useMemo(
    () => getRetentionNextPath(retentionStatus),
    [retentionStatus],
  )
  const retentionStepKey = useMemo(
    () => getRetentionStepKey(retentionStatus),
    [retentionStatus],
  )

  const retentionNudge = useMemo<RetentionNudge | null>(() => {
    if (!isTrialTenant || retentionDay == null || retentionDismissed) return null
    const activationDone = Boolean(
      retentionStatus &&
        !retentionStatus.onboarding_required &&
        !retentionStatus.activation_required,
    )
    const dayKey = `d${retentionDay}` as const
    return {
      day: retentionDay,
      dayKey,
      activationDone,
      href: retentionNextHref,
      stepKey: retentionStepKey,
    }
  }, [
    isTrialTenant,
    retentionDay,
    retentionDismissed,
    retentionStatus,
    retentionNextHref,
    retentionStepKey,
  ])

  const trackRetentionEvent = useCallback(
    (
      action: RetentionAction,
      payload?: {
        day?: TrialRetentionDay
        stepKey?: string
        href?: string
        activationDone?: boolean
      },
    ) => {
      const dayBucket =
        payload?.day != null ? (`d${payload.day}` as 'd1' | 'd2' | 'd3' | 'd7') : null
      if (typeof window !== 'undefined') {
        const dataLayer = (window as typeof window & { dataLayer?: unknown[] }).dataLayer
        if (Array.isArray(dataLayer)) {
          dataLayer.push({
            event: 'trial_retention_nudge',
            action,
            day: payload?.day ?? null,
            step_key: payload?.stepKey ?? null,
            target_href: payload?.href ?? null,
            activation_done: payload?.activationDone ?? null,
            tenant_id: tenantId,
          })
        }
      }
      if (dayBucket) {
        void recordTrialRetentionEvent({
          event: 'trial_retention_nudge',
          action,
          day_bucket: dayBucket,
          step_key: payload?.stepKey ?? null,
          target_href: payload?.href ?? null,
          activation_done: payload?.activationDone ?? null,
        }).catch(() => undefined)
      }
    },
    [tenantId],
  )

  useEffect(() => {
    if (!retentionNudge) {
      retentionImpressionRef.current = null
      return
    }
    const impressionKey = `${tenantId}:${retentionNudge.day}:${retentionNudge.stepKey}`
    if (retentionImpressionRef.current === impressionKey) return
    retentionImpressionRef.current = impressionKey
    trackRetentionEvent('impression', {
      day: retentionNudge.day,
      stepKey: retentionNudge.stepKey,
      href: retentionNudge.href,
      activationDone: retentionNudge.activationDone,
    })
  }, [retentionNudge, tenantId, trackRetentionEvent])

  return {
    trialEndsAt,
    billingGate,
    retentionStatus,
    retentionDismissed,
    retentionReport,
    retentionReportLoading,
    trialDaysLeft,
    trialTone,
    showTrialPanel,
    trialCenterClasses,
    retentionReportRows,
    trialAgeDays,
    retentionDay,
    retentionNextHref,
    retentionStepKey,
    retentionNudge,
    dismissRetentionNudge,
    trackRetentionEvent,
  }
}
