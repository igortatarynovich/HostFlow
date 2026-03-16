import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  IconAlertTriangle,
  IconCheck,
  IconCreditCard,
  IconExternalLink,
  IconHistory,
  IconMail,
  IconRefresh,
} from '@tabler/icons-react'
import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import {
  cancelBillingSubscription,
  changeBillingPlan,
  createBillingCheckoutSession,
  createBillingPortalLink,
  getBillingSummary,
  reactivateBillingSubscription,
  simulateBillingCheckoutResolution,
  updateBillingCompanySlots,
  type BillingCheckoutSession,
  type BillingHistoryItem,
  type BillingInvoice,
  type BillingSubscription,
  type BillingSummary,
} from '../../api/billing'
import { listCompanies } from '../../api/client'
import { recordTtvStepCompleted } from '../../api/analytics'

type PlanCode = 'starter' | 'team' | 'pro'
type CheckoutState = 'idle' | 'success' | 'cancel' | 'error' | 'incomplete'

type PlanDef = {
  code: PlanCode
  name: string
  price: string
  seatsLabel: string
  featureLabel: string
}

type ActionNotice = {
  tone: 'success' | 'warning'
  title: string
  text: string
} | null

const DAY_MS = 24 * 60 * 60 * 1000

function getPlanCode(value: string | null | undefined): PlanCode {
  const plan = (value || '').trim().toLowerCase()
  if (plan === 'team' || plan === 'pro') return plan
  return 'starter'
}

function formatDate(value: string | null | undefined, fallback: string) {
  if (!value) return fallback
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return fallback
  return dt.toLocaleDateString()
}

function formatDateTime(value: string | null | undefined, fallback: string) {
  if (!value) return fallback
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return fallback
  return dt.toLocaleString()
}

function formatAmount(minor: number | null | undefined, currency: string | null | undefined) {
  if (minor == null) return 'Not available'
  const amount = minor / 100
  const code = (currency || 'EUR').toUpperCase()
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: code,
      currencyDisplay: 'symbol',
    }).format(amount)
  } catch {
    return `${amount.toFixed(2)} ${code}`
  }
}

function normalizeSubscriptionState(subscription: BillingSubscription | null): CheckoutState {
  const normalized = (subscription?.status || '').toLowerCase()
  if (normalized === 'active') return 'success'
  if (normalized === 'canceled') return 'cancel'
  if (normalized === 'past_due') return 'error'
  if (normalized === 'incomplete') return 'incomplete'
  return 'idle'
}

function getStatusMeta(subscription: BillingSubscription | null, t: (key: string, options?: any) => string, fallback: string) {
  const normalized = (subscription?.status || '').trim().toLowerCase()
  if (subscription?.cancel_at_period_end) {
    return {
      label: t('app.settings.billing.status.cancel_at_period_end.label', { defaultValue: 'Cancels at period end' }),
      tone: 'warning',
      description: subscription.current_period_end
        ? t('app.settings.billing.status.cancel_at_period_end.description_with_date', {
            defaultValue: 'Access remains active until {date}.',
            values: { date: formatDate(subscription.current_period_end, fallback) },
          })
        : t('app.settings.billing.status.cancel_at_period_end.description', {
            defaultValue: 'Access remains active until the current billing period ends.',
          }),
    }
  }
  switch (normalized) {
    case 'active':
      return {
        label: t('app.settings.billing.status.active.label', { defaultValue: 'Active' }),
        tone: 'success',
        description: t('app.settings.billing.status.active.description', {
          defaultValue: 'Subscription is paid and active.',
        }),
      }
    case 'trial':
      return {
        label: t('app.settings.billing.status.trial.label', { defaultValue: 'Trial' }),
        tone: 'info',
        description: t('app.settings.billing.status.trial.description', {
          defaultValue: 'Trial is active. Upgrade before it ends.',
        }),
      }
    case 'past_due':
      return {
        label: t('app.settings.billing.status.past_due.label', { defaultValue: 'Payment required' }),
        tone: 'danger',
        description: t('app.settings.billing.status.past_due.description', {
          defaultValue: 'A payment issue needs attention.',
        }),
      }
    case 'incomplete':
      return {
        label: t('app.settings.billing.status.incomplete.label', { defaultValue: 'Payment pending' }),
        tone: 'warning',
        description: t('app.settings.billing.status.incomplete.description', {
          defaultValue: 'Checkout started but payment is not completed yet.',
        }),
      }
    case 'canceled':
      return {
        label: t('app.settings.billing.status.canceled.label', { defaultValue: 'Canceled' }),
        tone: 'danger',
        description: t('app.settings.billing.status.canceled.description', {
          defaultValue: 'Subscription is canceled.',
        }),
      }
    default:
      return {
        label: normalized || t('app.settings.billing.status.unknown.label', { defaultValue: 'Unknown' }),
        tone: 'info',
        description: t('app.settings.billing.status.unknown.description', {
          defaultValue: 'Billing state is available below.',
        }),
      }
  }
}

function getHistoryToneClasses(status: string) {
  const normalized = (status || '').toLowerCase()
  if (normalized === 'success') return 'border-emerald-200 bg-emerald-50 text-emerald-800'
  if (normalized === 'warning') return 'border-amber-200 bg-amber-50 text-amber-800'
  if (normalized === 'error') return 'border-rose-200 bg-rose-50 text-rose-800'
  return 'border-slate-200 bg-slate-50 text-slate-700'
}

function openCheckoutTab() {
  if (typeof window === 'undefined') return null
  const popup = window.open('about:blank', '_blank')
  if (!popup) return null
  try {
    popup.opener = null
    popup.document.title = 'HostFlow Billing'
    popup.document.body.innerHTML =
      '<div style="font-family: sans-serif; padding: 24px; color: #0f172a;">Opening Stripe checkout...</div>'
  } catch {
    // Cross-window writes can fail in some browsers; navigation is still enough.
  }
  return popup
}

export default function BillingWorkspacePage() {
  const { t } = useI18n()
  const [subscription, setSubscription] = useState<BillingSubscription | null>(null)
  const [summary, setSummary] = useState<BillingSummary | null>(null)
  const [lastCheckout, setLastCheckout] = useState<BillingCheckoutSession | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isCheckoutLoading, setIsCheckoutLoading] = useState(false)
  const [isPortalLoading, setIsPortalLoading] = useState(false)
  const [isMutationLoading, setIsMutationLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [checkoutState, setCheckoutState] = useState<CheckoutState>('idle')
  const [actionNotice, setActionNotice] = useState<ActionNotice>(null)
  const [isVerifyingCheckout, setIsVerifyingCheckout] = useState(false)
  const [operatingCompanyCount, setOperatingCompanyCount] = useState(0)
  const [companySlotsInput, setCompanySlotsInput] = useState('0')
  const [recommendedFromQuery, setRecommendedFromQuery] = useState<number>(0)
  const [companySlotsRecoveryFocus, setCompanySlotsRecoveryFocus] = useState(false)

  const reloadSummary = useCallback(async () => {
    const data = await getBillingSummary()
    setSummary(data)
    setSubscription(data.subscription)
    setCheckoutState(normalizeSubscriptionState(data.subscription))
    return data
  }, [])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      setIsLoading(true)
      setError(null)
      try {
        const data = await reloadSummary()
        if (!mounted) return
        const urlState = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('checkout') : null
        setCheckoutState(urlState === 'cancel' ? 'cancel' : normalizeSubscriptionState(data.subscription))
      } catch (err: any) {
        if (!mounted) return
        setError(
          getFriendlyErrorInfo(
            err,
            t('app.settings.billing.load_error', { defaultValue: 'Failed to load billing subscription.' }),
          ),
        )
      } finally {
        if (mounted) setIsLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
  }, [reloadSummary, t])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const companies = await listCompanies({ limit: 500 })
        if (!mounted) return
        const count = (Array.isArray(companies) ? companies : []).filter((company: any) => {
          const role = String(company?.extra?.company_role || '').trim().toLowerCase()
          return role === 'operating'
        }).length
        setOperatingCompanyCount(count)
      } catch {
        if (mounted) setOperatingCompanyCount(0)
      }
    })()
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    const next = String(summary?.company_slots?.extra_slots ?? 0)
    setCompanySlotsInput(next)
  }, [summary?.company_slots?.extra_slots])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    const focus = String(params.get('focus') || '').trim().toLowerCase()
    const raw = String(params.get('recommended_extra_slots') || params.get('extra_slots') || '').trim()
    const parsed = Number.parseInt(raw, 10)
    const recommended = Number.isFinite(parsed) ? Math.min(1000, Math.max(0, parsed)) : 0
    let consumedRecoveryParams = false
    if (recommended > 0) {
      setRecommendedFromQuery(recommended)
      setCompanySlotsInput((prev) => {
        const current = Number.parseInt(prev, 10)
        const normalized = Number.isFinite(current) ? Math.min(1000, Math.max(0, current)) : 0
        return String(Math.max(normalized, recommended))
      })
      setActionNotice((prev) =>
        prev ?? {
          tone: 'warning',
          title: t('app.settings.billing.action_notice.company_slots_recommended_title', {
            defaultValue: 'Recommended extra slots applied',
          }),
          text: t('app.settings.billing.action_notice.company_slots_recommended_text', {
            defaultValue: 'We prefilled {count} extra operating slot(s) based on your previous action.',
            values: { count: recommended },
          }),
        },
      )
      consumedRecoveryParams = true
    }
    if (focus === 'company-slots') {
      setCompanySlotsRecoveryFocus(true)
      window.setTimeout(() => {
        const node = document.getElementById('company-slots-usage-card')
        if (node) node.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }, 80)
      consumedRecoveryParams = true
    }
    if (consumedRecoveryParams) {
      params.delete('focus')
      params.delete('recommended_extra_slots')
      params.delete('extra_slots')
      const nextSearch = params.toString()
      const nextUrl = `${window.location.pathname}${nextSearch ? `?${nextSearch}` : ''}`
      window.history.replaceState({}, '', nextUrl)
    }
  }, [t])

  const activePlan = getPlanCode(subscription?.plan_code)
  const isTrial = (subscription?.status || '').trim().toLowerCase() === 'trial'
  const isStripe = subscription?.provider === 'stripe'
  const notAvailableLabel = t('app.settings.billing.not_available', { defaultValue: 'Not available' })
  const statusMeta = getStatusMeta(subscription, t, notAvailableLabel)
  const trialDaysLeft = useMemo(() => {
    if (!subscription?.trial_ends_at) return null
    const dt = new Date(subscription.trial_ends_at)
    if (Number.isNaN(dt.getTime())) return null
    return Math.max(0, Math.ceil((dt.getTime() - Date.now()) / DAY_MS))
  }, [subscription?.trial_ends_at])

  const plans = useMemo<PlanDef[]>(
    () => [
      {
        code: 'starter',
        name: t('app.settings.billing.plans.starter.name', { defaultValue: 'Starter' }),
        price: t('app.settings.billing.plans.starter.price', { defaultValue: 'EUR 39/mo' }),
        seatsLabel: t('app.settings.billing.plans.starter.seats', { defaultValue: '1 user' }),
        featureLabel: t('app.settings.billing.plans.starter.feature', { defaultValue: 'Core CRM' }),
      },
      {
        code: 'team',
        name: t('app.settings.billing.plans.team.name', { defaultValue: 'Team' }),
        price: t('app.settings.billing.plans.team.price', { defaultValue: 'EUR 99/mo' }),
        seatsLabel: t('app.settings.billing.plans.team.seats', { defaultValue: 'Up to 5 users' }),
        featureLabel: t('app.settings.billing.plans.team.feature', { defaultValue: 'Team collaboration' }),
      },
      {
        code: 'pro',
        name: t('app.settings.billing.plans.pro.name', { defaultValue: 'Pro' }),
        price: t('app.settings.billing.plans.pro.price', { defaultValue: 'EUR 199/mo' }),
        seatsLabel: t('app.settings.billing.plans.pro.seats', { defaultValue: '15+ users' }),
        featureLabel: t('app.settings.billing.plans.pro.feature', { defaultValue: 'Advanced automations' }),
      },
    ],
    [t],
  )

  const startCheckout = async (plan: PlanCode) => {
    const checkoutWindow = openCheckoutTab()
    setIsCheckoutLoading(true)
    setError(null)
    setActionNotice(null)
    try {
      const origin = typeof window !== 'undefined' ? window.location.origin : ''
      const successUrl = `${origin}/app/settings/billing?checkout=success`
      const cancelUrl = `${origin}/app/settings/billing?checkout=cancel`
      const session = await createBillingCheckoutSession({
        plan_code: plan,
        success_url: successUrl,
        cancel_url: cancelUrl,
      })
      setLastCheckout(session)
      setCheckoutState('incomplete')
      await reloadSummary()
      // Фиксируем TTV-шаг: пользователь выбрал план и запустил checkout.
      void recordTtvStepCompleted({ event: 'ttv_step', action: 'completed', step_key: 'plan_selected' })
      if (session.provider === 'stripe' && session.checkout_url) {
        if (checkoutWindow) {
          checkoutWindow.location.replace(session.checkout_url)
        } else {
          setError({
            title: t('app.settings.billing.popup_blocked_title', { defaultValue: 'Allow pop-ups to continue' }),
            hint: t('app.settings.billing.popup_blocked_hint', {
              defaultValue: 'Stripe checkout was created, but the browser blocked the payment tab. Allow pop-ups and try again.',
            }),
          })
        }
      }
    } catch (err: any) {
      if (checkoutWindow && !checkoutWindow.closed) checkoutWindow.close()
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.settings.billing.checkout_error', { defaultValue: 'Failed to start checkout.' }),
        ),
      )
    } finally {
      setIsCheckoutLoading(false)
    }
  }

  const simulateOutcome = async (outcome: 'success' | 'cancel' | 'error') => {
    const sessionId = lastCheckout?.session_id || subscription?.checkout_session_id
    if (!sessionId) {
      setError({
        title: t('app.settings.billing.no_checkout_session', { defaultValue: 'Start checkout first to simulate outcome.' }),
        hint: t('app.settings.billing.checkout_sim.title', { defaultValue: 'Start checkout, then run simulation action.' }),
      })
      return
    }
    setIsCheckoutLoading(true)
    setError(null)
    setActionNotice(null)
    try {
      const next = await simulateBillingCheckoutResolution(sessionId, outcome)
      setSubscription(next)
      setCheckoutState(outcome)
      await reloadSummary()
    } catch (err: any) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.settings.billing.simulation_error', { defaultValue: 'Failed to simulate checkout outcome.' }),
        ),
      )
    } finally {
      setIsCheckoutLoading(false)
    }
  }

  const openPortal = async () => {
    setIsPortalLoading(true)
    setError(null)
    setActionNotice(null)
    try {
      const portal = await createBillingPortalLink()
      if (portal.url) window.open(portal.url, '_blank', 'noopener,noreferrer')
    } catch (err: any) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.settings.billing.portal_error', { defaultValue: 'Failed to open customer portal.' }),
        ),
      )
    } finally {
      setIsPortalLoading(false)
    }
  }

  const handlePlanAction = async (plan: PlanCode) => {
    if (isTrial || !subscription?.subscription_id || subscription?.status === 'incomplete') {
      await startCheckout(plan)
      return
    }
    const checkoutWindow = openCheckoutTab()
    setIsMutationLoading(true)
    setError(null)
    setActionNotice(null)
    try {
      const origin = typeof window !== 'undefined' ? window.location.origin : ''
      const data = await changeBillingPlan({
        plan_code: plan,
        success_url: `${origin}/app/settings/billing?checkout=success`,
        cancel_url: `${origin}/app/settings/billing?checkout=cancel`,
      })
      setSummary(data)
      setSubscription(data.subscription)
      setCheckoutState(normalizeSubscriptionState(data.subscription))
      if (data.subscription.pending_update && data.subscription.pending_plan_code === plan) {
        setActionNotice({
          tone: 'warning',
          title: t('app.settings.billing.action_notice.plan_change_pending_title', {
            defaultValue: 'Complete payment to switch plans',
          }),
          text: t('app.settings.billing.action_notice.plan_change_pending_text', {
            defaultValue: 'We opened Stripe payment for the {plan} plan. Your current plan stays active until payment is completed.',
            values: { plan: plan.toUpperCase() },
          }),
        })
        if (data.subscription.pending_invoice_url) {
          if (checkoutWindow) {
            checkoutWindow.location.replace(data.subscription.pending_invoice_url)
          } else {
            setError({
              title: t('app.settings.billing.popup_blocked_title', { defaultValue: 'Allow pop-ups to continue' }),
              hint: t('app.settings.billing.popup_blocked_hint', {
                defaultValue: 'Stripe checkout was created, but the browser blocked the payment tab. Allow pop-ups and try again.',
              }),
            })
          }
        }
      } else {
        if (checkoutWindow && !checkoutWindow.closed) checkoutWindow.close()
        setActionNotice({
          tone: 'success',
          title: t('app.settings.billing.action_notice.plan_change_title', { defaultValue: 'Plan updated' }),
          text: t('app.settings.billing.action_notice.plan_change_text', {
            defaultValue: 'Your subscription was switched to {plan}.',
            values: { plan: plan.toUpperCase() },
          }),
        })
      }
    } catch (err: any) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.settings.billing.change_plan_error', { defaultValue: 'Failed to change plan.' }),
        ),
      )
      if (checkoutWindow && !checkoutWindow.closed) checkoutWindow.close()
    } finally {
      setIsMutationLoading(false)
    }
  }

  const handleCancel = async () => {
    setIsMutationLoading(true)
    setError(null)
    setActionNotice(null)
    try {
      const data = await cancelBillingSubscription(false)
      setSummary(data)
      setSubscription(data.subscription)
      setCheckoutState(normalizeSubscriptionState(data.subscription))
      setActionNotice({
        tone: 'warning',
        title: t('app.settings.billing.action_notice.cancel_title', { defaultValue: 'Cancellation scheduled' }),
        text: t('app.settings.billing.action_notice.cancel_text', {
          defaultValue: 'Your subscription stays active until {date}. Auto-renew is turned off.',
          values: { date: formatDate(data.subscription.current_period_end, notAvailableLabel) },
        }),
      })
    } catch (err: any) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.settings.billing.cancel_error', { defaultValue: 'Failed to cancel subscription.' }),
        ),
      )
    } finally {
      setIsMutationLoading(false)
    }
  }

  const handleReactivate = async () => {
    setIsMutationLoading(true)
    setError(null)
    setActionNotice(null)
    try {
      const data = await reactivateBillingSubscription()
      setSummary(data)
      setSubscription(data.subscription)
      setCheckoutState(normalizeSubscriptionState(data.subscription))
      setActionNotice({
        tone: 'success',
        title: t('app.settings.billing.action_notice.resume_title', { defaultValue: 'Subscription resumed' }),
        text: t('app.settings.billing.action_notice.resume_text', {
          defaultValue: 'Auto-renew is active again. Your plan will continue without interruption.',
        }),
      })
    } catch (err: any) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.settings.billing.reactivate_error', { defaultValue: 'Failed to reactivate subscription.' }),
        ),
      )
    } finally {
      setIsMutationLoading(false)
    }
  }

  const handleUpdateCompanySlots = async () => {
    const parsed = Number.parseInt(companySlotsInput, 10)
    const desired = Number.isFinite(parsed) ? Math.min(1000, Math.max(0, parsed)) : 0
    setIsMutationLoading(true)
    setError(null)
    setActionNotice(null)
    try {
      const data = await updateBillingCompanySlots({ extra_slots: desired })
      setSummary(data)
      setSubscription(data.subscription)
      setCompanySlotsInput(String(data.company_slots?.extra_slots ?? desired))
      const used = Number(data.company_slots?.used ?? 0)
      const effective = Number(data.company_slots?.effective_limit ?? 0)
      const overflow = effective > 0 && used > effective
      if (overflow) {
        const missing = Math.max(1, used - effective)
        setActionNotice({
          tone: 'warning',
          title: t('app.settings.billing.action_notice.company_slots_overflow_title', {
            defaultValue: 'Slots updated, but you are over the limit',
          }),
          text: t('app.settings.billing.action_notice.company_slots_overflow_text', {
            defaultValue:
              'Existing operating companies were kept. Creation of new operating companies is blocked until you add at least {count} slot(s).',
            values: { count: missing },
          }),
        })
      } else {
        setActionNotice({
          tone: 'success',
          title: t('app.settings.billing.action_notice.company_slots_title', { defaultValue: 'Company slots updated' }),
          text: t('app.settings.billing.action_notice.company_slots_text', {
            defaultValue: 'Add-on operating company slots were set to {count}.',
            values: { count: String(data.company_slots?.extra_slots ?? desired) },
          }),
        })
      }
    } catch (err: any) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.settings.billing.company_slots_error', { defaultValue: 'Failed to update operating company slots.' }),
        ),
      )
    } finally {
      setIsMutationLoading(false)
    }
  }

  const clearCheckoutState = async () => {
    setCheckoutState('idle')
    setLastCheckout(null)
    await reloadSummary()
  }

  const checkoutNotice = useMemo(() => {
    if (checkoutState === 'success') {
      return {
        tone: 'border-emerald-200 bg-emerald-50 text-emerald-800',
        title: t('app.settings.billing.notice.success_title', { defaultValue: 'Payment confirmed' }),
        text: t('app.settings.billing.notice.success_text', {
          defaultValue: 'Subscription is active. Billing period, plan and payment history are shown below.',
        }),
      }
    }
    if (checkoutState === 'cancel') {
      return {
        tone: 'border-amber-200 bg-amber-50 text-amber-800',
        title: t('app.settings.billing.notice.cancel_title', { defaultValue: 'Checkout canceled' }),
        text: t('app.settings.billing.notice.cancel_text', {
          defaultValue: 'No charge was completed. You can restart checkout when you are ready.',
        }),
      }
    }
    if (checkoutState === 'error') {
      return {
        tone: 'border-rose-200 bg-rose-50 text-rose-800',
        title: t('app.settings.billing.notice.error_title', { defaultValue: 'Payment requires attention' }),
        text: t('app.settings.billing.notice.error_text', {
          defaultValue: 'The subscription is not fully paid. Retry payment or open payment settings.',
        }),
      }
    }
    if (checkoutState === 'incomplete') {
      return {
        tone: 'border-amber-200 bg-amber-50 text-amber-800',
        title: t('app.settings.billing.notice.incomplete_title', { defaultValue: 'Payment pending' }),
        text: t('app.settings.billing.notice.incomplete_text', {
          defaultValue: 'Checkout is created but not completed yet.',
        }),
      }
    }
    return null
  }, [checkoutState, t])

  const history = summary?.history || []
  const invoices = summary?.invoices || []
  const parsedCompanySlotsInput = Number.parseInt(companySlotsInput, 10)
  const normalizedCompanySlotsInput = Number.isFinite(parsedCompanySlotsInput)
    ? Math.min(1000, Math.max(0, parsedCompanySlotsInput))
    : 0
  const currentExtraSlots = summary?.company_slots?.extra_slots ?? 0
  const canSaveCompanySlots = normalizedCompanySlotsInput !== currentExtraSlots && !isMutationLoading
  const hasOperatingSlotCapacity =
    Boolean(summary?.company_slots?.unlimited) || Number(summary?.company_slots?.available ?? 0) > 0
  const usedOperatingSlots = Number(summary?.company_slots?.used ?? operatingCompanyCount)
  const effectiveOperatingSlots = Number(summary?.company_slots?.effective_limit ?? summary?.license?.max_companies ?? 0)
  const operatingSlotsOverflow = effectiveOperatingSlots > 0 && usedOperatingSlots > effectiveOperatingSlots
  const operatingSlotsMissing = operatingSlotsOverflow ? Math.max(1, usedOperatingSlots - effectiveOperatingSlots) : 0

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    const checkoutFlag = params.get('checkout')
    if (checkoutFlag !== 'success') return
    let cancelled = false
    setIsVerifyingCheckout(true)
    const run = async () => {
      for (let attempt = 0; attempt < 5; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, attempt === 0 ? 0 : 2000))
        if (cancelled) return
        try {
          const data = await reloadSummary()
          if (cancelled) return
          const nextState = normalizeSubscriptionState(data.subscription)
          if (nextState === 'success') {
            params.delete('checkout')
            const next = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ''}`
            window.history.replaceState({}, '', next)
            setIsVerifyingCheckout(false)
            return
          }
        } catch {
          // keep retrying; main error banner already handles hard failures
        }
      }
      if (!cancelled) setIsVerifyingCheckout(false)
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [reloadSummary])

  return (
    <div className="space-y-4">
      <header className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
          <IconCreditCard size={18} stroke={1.9} />
          {t('app.settings.billing.badge', { defaultValue: 'Subscription & payments' })}
        </div>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <h1 className="text-2xl font-semibold text-slate-900">
              {t('app.settings.billing.title', { defaultValue: 'Manage subscription' })}
            </h1>
            <p className="max-w-3xl text-sm text-slate-600">
              {t('app.settings.billing.subtitle', {
                defaultValue:
                  'See whether your plan is paid, which plan is active, when the current period ends, and what you can do next.',
              })}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={() => void reloadSummary()} disabled={isLoading}>
              <IconRefresh size={15} stroke={1.9} />
              <span>{t('common.actions.refresh', { defaultValue: 'Refresh' })}</span>
            </button>
            <button type="button" className="btn-secondary" onClick={openPortal} disabled={isPortalLoading}>
              <IconExternalLink size={15} stroke={1.9} />
              <span>{t('app.settings.billing.portal', { defaultValue: 'Open payment settings' })}</span>
            </button>
          </div>
        </div>
      </header>

      {isTrial && (
        <section className="rounded-xl border border-amber-300 bg-amber-50 p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
                {t('app.settings.billing.trial.badge', { defaultValue: 'Trial status' })}
              </p>
              <h2 className="text-sm font-semibold text-amber-950">
                {trialDaysLeft != null
                  ? t('app.settings.billing.trial.title_with_days', {
                      defaultValue: 'Trial active: {days} day(s) left',
                      values: { days: trialDaysLeft },
                    })
                  : t('app.settings.billing.trial.title', { defaultValue: 'Trial active' })}
              </h2>
              <p className="text-xs text-amber-950/90">
                {t('app.settings.billing.trial.subtitle', {
                  defaultValue: 'Choose a paid plan before trial ends to keep uninterrupted access.',
                })}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button type="button" className="btn-primary" onClick={() => void startCheckout(activePlan)} disabled={isCheckoutLoading}>
                {t('app.settings.billing.trial.cta', { defaultValue: 'Subscribe now' })}
              </button>
              <Link to="/app/overview" className="btn-secondary">
                {t('app.settings.billing.trial.secondary_cta', { defaultValue: 'Continue setup' })}
              </Link>
            </div>
          </div>
        </section>
      )}

      {error && (
        <ErrorRecoveryBanner
          info={error}
          onRetry={() => void reloadSummary()}
          retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
          secondaryTo="/app/settings/billing"
          secondaryLabel={t('app.settings.billing.badge', { defaultValue: 'Subscription & payments' })}
        />
      )}

      {isLoading ? (
        <section className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
          {t('common.loading')}
        </section>
      ) : null}

      {checkoutNotice ? (
        <section className={`rounded-xl border p-4 shadow-sm ${checkoutNotice.tone}`}>
          <div className="flex items-start gap-2">
            <IconAlertTriangle size={18} stroke={1.9} />
            <div>
              <p className="text-sm font-semibold">{checkoutNotice.title}</p>
              <p className="mt-1 text-sm">{checkoutNotice.text}</p>
            </div>
          </div>
        </section>
      ) : null}

      {isVerifyingCheckout ? (
        <section className="rounded-xl border border-brand-200 bg-brand-50 p-4 shadow-sm text-brand-900">
          <div className="flex items-start gap-2">
            <IconRefresh size={18} stroke={1.9} />
            <div>
              <p className="text-sm font-semibold">
                {t('app.settings.billing.verification.title', { defaultValue: 'Checking payment status' })}
              </p>
              <p className="mt-1 text-sm">
                {t('app.settings.billing.verification.text', {
                  defaultValue: 'We are waiting for payment confirmation. This usually takes a few seconds.',
                })}
              </p>
            </div>
          </div>
        </section>
      ) : null}

      {actionNotice ? (
        <section
          className={`rounded-xl border p-4 shadow-sm ${
            actionNotice.tone === 'success'
              ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
              : 'border-amber-200 bg-amber-50 text-amber-800'
          }`}
        >
          <div className="flex items-start gap-2">
            <IconAlertTriangle size={18} stroke={1.9} />
            <div>
              <p className="text-sm font-semibold">{actionNotice.title}</p>
              <p className="mt-1 text-sm">{actionNotice.text}</p>
            </div>
          </div>
        </section>
      ) : null}

      {subscription?.pending_update && subscription.pending_plan_code ? (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 shadow-sm text-amber-900">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold">
                {t('app.settings.billing.pending_upgrade.title', {
                  defaultValue: 'Plan change is waiting for payment confirmation',
                })}
              </p>
              <p className="mt-1 text-sm">
                {t('app.settings.billing.pending_upgrade.text', {
                  defaultValue:
                    'Your current plan remains {currentPlan}. The {nextPlan} plan will activate only after Stripe confirms payment.',
                  values: {
                    currentPlan: String(subscription.plan_code || '').toUpperCase(),
                    nextPlan: String(subscription.pending_plan_code || '').toUpperCase(),
                  },
                })}
              </p>
            </div>
            <button type="button" className="btn-secondary" onClick={() => void reloadSummary()}>
              {t('app.settings.billing.refresh_status', { defaultValue: 'Refresh payment status' })}
            </button>
          </div>
        </section>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.settings.billing.labels.current_plan', { defaultValue: 'Current plan' })}
              </p>
              <h2 className="mt-1 text-2xl font-semibold text-slate-900">{activePlan.toUpperCase()}</h2>
              <p className="mt-1 text-sm text-slate-600">{statusMeta.description}</p>
            </div>
            <span
              className={`rounded-md px-3 py-1 text-xs font-semibold ${
                statusMeta.tone === 'success'
                  ? 'bg-emerald-100 text-emerald-800'
                  : statusMeta.tone === 'warning'
                    ? 'bg-amber-100 text-amber-800'
                    : statusMeta.tone === 'danger'
                      ? 'bg-rose-100 text-rose-800'
                      : 'bg-slate-100 text-slate-700'
              }`}
            >
              {statusMeta.label}
            </span>
          </div>

          <dl className="mt-5 grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-slate-200 p-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.settings.billing.labels.paid_plan', { defaultValue: 'Paid plan' })}
              </dt>
              <dd className="mt-1 text-sm font-medium text-slate-900">{plans.find((plan) => plan.code === activePlan)?.price || '-'}</dd>
            </div>
            <div className="rounded-lg border border-slate-200 p-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.settings.billing.labels.subscription_started', { defaultValue: 'Subscription started' })}
              </dt>
              <dd className="mt-1 text-sm font-medium text-slate-900">
                {formatDate(subscription?.activated_at || subscription?.current_period_start, notAvailableLabel)}
              </dd>
            </div>
            <div className="rounded-lg border border-slate-200 p-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {subscription?.cancel_at_period_end
                  ? t('app.settings.billing.labels.access_ends', { defaultValue: 'Access ends' })
                  : t('app.settings.billing.labels.current_period_ends', { defaultValue: 'Current period ends' })}
              </dt>
              <dd className="mt-1 text-sm font-medium text-slate-900">
                {formatDate(subscription?.current_period_end, notAvailableLabel)}
              </dd>
            </div>
            <div className="rounded-lg border border-slate-200 p-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.settings.billing.labels.last_billing_update', { defaultValue: 'Last billing update' })}
              </dt>
              <dd className="mt-1 text-sm font-medium text-slate-900">
                {formatDateTime(subscription?.updated_at, notAvailableLabel)}
              </dd>
            </div>
          </dl>

          <div className="mt-5 flex flex-wrap gap-2">
            {subscription?.cancel_at_period_end ? (
              <button type="button" className="btn-primary" onClick={handleReactivate} disabled={isMutationLoading}>
                {t('app.settings.billing.reactivate', { defaultValue: 'Resume subscription' })}
              </button>
            ) : (
              <button
                type="button"
                className="btn-primary"
                onClick={() =>
                  void (
                    isTrial || subscription?.status === 'incomplete' || subscription?.status === 'past_due'
                      ? startCheckout(activePlan)
                      : openPortal()
                  )
                }
                disabled={isCheckoutLoading || isPortalLoading}
              >
                {isTrial || subscription?.status === 'incomplete'
                  ? t('app.settings.billing.subscribe', { defaultValue: 'Subscribe' })
                  : subscription?.status === 'past_due'
                    ? t('app.settings.billing.pay_now', { defaultValue: 'Pay now' })
                    : t('app.settings.billing.manage_in_stripe', { defaultValue: 'Manage payment settings' })}
              </button>
            )}
            {!subscription?.cancel_at_period_end && subscription?.status !== 'canceled' ? (
              <button type="button" className="btn-danger" onClick={handleCancel} disabled={isMutationLoading}>
                {t('app.settings.billing.cancel', { defaultValue: 'Cancel at period end' })}
              </button>
            ) : null}
            {(subscription?.status === 'incomplete' || subscription?.status === 'past_due') && !isVerifyingCheckout ? (
              <button type="button" className="btn-secondary" onClick={() => void reloadSummary()} disabled={isLoading}>
                {t('app.settings.billing.refresh_status', { defaultValue: 'Refresh payment status' })}
              </button>
            ) : null}
          </div>

          <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
            <p className="font-medium text-slate-900">
              {t('app.settings.billing.communication.title', { defaultValue: 'Email updates' })}
            </p>
            <p className="mt-1">
              {t('app.settings.billing.communication.description', {
                defaultValue:
                  'We send confirmation emails when payment is completed, when a plan changes, and when cancellation or renewal status changes.',
              })}
            </p>
          </div>
        </article>

        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">
            {t('app.settings.billing.manage_title', { defaultValue: 'What you can do here' })}
          </h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-600">
            <li>{t('app.settings.billing.actions_help.subscribe', { defaultValue: 'Subscribe starts Stripe checkout for the selected plan.' })}</li>
            <li>{t('app.settings.billing.actions_help.manage', { defaultValue: 'Manage payment settings to change plan, payment method and invoice details.' })}</li>
            <li>{t('app.settings.billing.actions_help.cancel', { defaultValue: 'Cancel subscription schedules cancellation at the period end.' })}</li>
            <li>{t('app.settings.billing.actions_help.resume', { defaultValue: 'Resume subscription removes scheduled cancellation.' })}</li>
          </ul>
          <div className="mt-5 rounded-lg border border-slate-200 p-3 text-sm">
            <p className="font-medium text-slate-900">
              {t('app.settings.billing.references.title', { defaultValue: 'Support details' })}
            </p>
            <p className="mt-2 text-slate-600">
              {t('app.settings.billing.references.customer_id', {
                defaultValue: 'Billing customer ID: {value}',
                values: { value: subscription?.customer_id || t('app.settings.billing.not_available_yet', { defaultValue: 'Not available yet' }) },
              })}
            </p>
            <p className="mt-1 text-slate-600">
              {t('app.settings.billing.references.subscription_id', {
                defaultValue: 'Subscription ID: {value}',
                values: { value: subscription?.subscription_id || t('app.settings.billing.not_available_yet', { defaultValue: 'Not available yet' }) },
              })}
            </p>
          </div>
          <div className="mt-4 rounded-lg border border-slate-200 p-3 text-sm">
            <p className="font-medium text-slate-900">{t('app.settings.billing.legal.title', { defaultValue: 'Legal' })}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer" className="btn-secondary btn-sm">
                {t('app.settings.billing.trial.legal_terms', { defaultValue: 'Terms' })}
              </a>
              <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="btn-secondary btn-sm">
                {t('app.settings.billing.trial.legal_privacy', { defaultValue: 'Privacy' })}
              </a>
              <a href="/legal/cookies.html" target="_blank" rel="noopener noreferrer" className="btn-secondary btn-sm">
                {t('app.settings.billing.trial.legal_cookies', { defaultValue: 'Cookies' })}
              </a>
            </div>
          </div>
        </article>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {plans.map((plan) => {
          const isActive = plan.code === activePlan
          return (
            <article
              key={plan.code}
              className={`rounded-xl border p-5 shadow-sm ${
                isActive ? 'border-emerald-300 bg-emerald-50/40' : 'border-slate-200 bg-white'
              }`}
            >
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">{plan.name}</h2>
                {isActive ? (
                  <span className="inline-flex items-center gap-1 rounded-md bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700">
                    <IconCheck size={14} stroke={2} />
                    {t('app.settings.billing.active_plan', { defaultValue: 'Active' })}
                  </span>
                ) : null}
              </div>
              <p className="mt-2 text-xl font-semibold text-slate-900">{plan.price}</p>
              <ul className="mt-3 space-y-1 text-sm text-slate-600">
                <li>{plan.seatsLabel}</li>
                <li>{plan.featureLabel}</li>
              </ul>
              <button
                type="button"
                className="btn-secondary mt-4 w-full justify-center"
                disabled={isActive || isCheckoutLoading || isMutationLoading || isPortalLoading}
                onClick={() => void handlePlanAction(plan.code)}
              >
                {isActive
                  ? t('app.settings.billing.current_plan', { defaultValue: 'Current plan' })
                  : isTrial || !subscription?.subscription_id || subscription?.status === 'incomplete'
                      ? t('app.settings.billing.subscribe_plan', { defaultValue: 'Subscribe to this plan' })
                      : t('app.settings.billing.choose_plan', { defaultValue: 'Change to this plan' })}
              </button>
            </article>
          )
        })}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">
          {t('app.settings.billing.usage_title', { defaultValue: 'Included limits' })}
        </h3>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div id="company-slots-usage-card" className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.recruiters', {
              defaultValue: 'Recruiters: {used} / {limit}',
              values: { used: summary?.usage.recruiter_count ?? 0, limit: summary?.license?.max_recruiters ?? 0 },
            })}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.supervisors', {
              defaultValue: 'Supervisors: {used} / {limit}',
              values: { used: summary?.usage.supervisor_count ?? 0, limit: summary?.license?.max_supervisors ?? 0 },
            })}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.client_managers', {
              defaultValue: 'Client managers: {used} / {limit}',
              values: { used: summary?.usage.client_manager_count ?? 0, limit: summary?.license?.max_client_managers ?? 0 },
            })}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.viewers', {
              defaultValue: 'Viewers: {used} / {limit}',
              values: { used: summary?.usage.viewer_count ?? 0, limit: summary?.license?.max_viewers ?? 0 },
            })}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.storage', {
              defaultValue: 'Storage: {used}GB / {limit}GB',
              values: { used: Math.round(summary?.usage.storage_used_gb ?? 0), limit: summary?.license?.max_storage_gb ?? 0 },
            })}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.companies', {
              defaultValue: 'Operating companies: {used} / {limit}',
              values: {
                used: summary?.company_slots?.used ?? operatingCompanyCount,
                limit: summary?.company_slots?.unlimited
                  ? '∞'
                  : (summary?.company_slots?.effective_limit ?? summary?.license?.max_companies ?? 0),
              },
            })}
            {(summary?.company_slots?.extra_slots ?? 0) > 0 ? (
              <div className="mt-1 text-xs text-slate-500">
                {t('app.settings.billing.usage.companies_addon', {
                  defaultValue: 'Includes {included} plan slots + {addon} add-on slots',
                  values: {
                    included: summary?.company_slots?.included_limit ?? summary?.license?.max_companies ?? 0,
                    addon: summary?.company_slots?.extra_slots ?? 0,
                  },
                })}
              </div>
            ) : null}
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="btn-secondary btn-xs"
                onClick={() => setCompanySlotsInput(String(Math.max(0, normalizedCompanySlotsInput - 1)))}
                disabled={isMutationLoading}
              >
                -
              </button>
              <input
                type="number"
                min={0}
                max={1000}
                step={1}
                value={companySlotsInput}
                onChange={(event) => setCompanySlotsInput(event.target.value)}
                className="input h-8 w-24"
                aria-label={t('app.settings.billing.usage.extra_company_slots', { defaultValue: 'Extra operating company slots' })}
              />
              <button
                type="button"
                className="btn-secondary btn-xs"
                onClick={() => setCompanySlotsInput(String(Math.min(1000, normalizedCompanySlotsInput + 1)))}
                disabled={isMutationLoading}
              >
                +
              </button>
              <button type="button" className="btn-secondary btn-xs" onClick={() => void handleUpdateCompanySlots()} disabled={!canSaveCompanySlots}>
                {t('common.actions.save', { defaultValue: 'Save' })}
              </button>
            </div>
            <div className="mt-1 text-xs text-slate-500">
              {t('app.settings.billing.usage.extra_company_slots_hint', {
                defaultValue: 'Add-on slots extend your plan limit for operating companies.',
              })}
            </div>
            {recommendedFromQuery > 0 ? (
              <div className="mt-1 text-xs text-amber-700">
                {t('app.settings.billing.usage.extra_company_slots_recommended', {
                  defaultValue: 'Recommended by recovery flow: +{count} slot(s).',
                  values: { count: recommendedFromQuery },
                })}
              </div>
            ) : null}
            {operatingSlotsOverflow ? (
              <div className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-900">
                {t('app.settings.billing.usage.companies_overflow', {
                  defaultValue:
                    'You currently have more operating companies than your active limit. Existing data is preserved, but creating new operating companies is blocked until you add at least {count} slot(s).',
                  values: { count: operatingSlotsMissing },
                })}
              </div>
            ) : null}
            {companySlotsRecoveryFocus ? (
              <div className="mt-2">
                {hasOperatingSlotCapacity ? (
                  <Link to="/app/onboarding/company" className="btn-primary btn-xs">
                    {t('app.settings.billing.usage.back_to_onboarding', { defaultValue: 'Create operating company now' })}
                  </Link>
                ) : (
                  <div className="text-xs text-slate-500">
                    {t('app.settings.billing.usage.back_to_onboarding_hint', {
                      defaultValue: 'Save add-on slots first, then return to company onboarding.',
                    })}
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2">
            <IconHistory size={18} stroke={1.9} />
            <h3 className="text-base font-semibold text-slate-900">
              {t('app.settings.billing.history.title', { defaultValue: 'Payment history' })}
            </h3>
          </div>
          {history.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">
              {t('app.settings.billing.history.empty', { defaultValue: 'No billing events yet.' })}
            </p>
          ) : (
            <div className="mt-4 space-y-3">
              {history.map((item: BillingHistoryItem) => (
                <article key={item.id} className={`rounded-lg border p-4 ${getHistoryToneClasses(item.status)}`}>
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold">{item.title}</p>
                      <p className="mt-1 text-xs opacity-80">{formatDateTime(item.occurred_at, notAvailableLabel)}</p>
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs">
                      {item.plan_code ? <span className="rounded-md bg-white/70 px-2 py-1">{item.plan_code.toUpperCase()}</span> : null}
                      {item.amount_minor != null ? (
                        <span className="rounded-md bg-white/70 px-2 py-1">{formatAmount(item.amount_minor, item.currency)}</span>
                      ) : null}
                    </div>
                  </div>
                  {item.description ? <p className="mt-2 text-sm">{item.description}</p> : null}
                  {(item.invoice_pdf_url || item.hosted_invoice_url) ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {item.hosted_invoice_url ? (
                          <a href={item.hosted_invoice_url} target="_blank" rel="noopener noreferrer" className="btn-secondary btn-sm">
                          {t('app.settings.billing.history.view_invoice', { defaultValue: 'View invoice' })}
                        </a>
                      ) : null}
                      {item.invoice_pdf_url ? (
                        <a href={item.invoice_pdf_url} target="_blank" rel="noopener noreferrer" className="btn-secondary btn-sm">
                          {t('app.settings.billing.history.download_pdf', { defaultValue: 'Download PDF' })}
                        </a>
                      ) : null}
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </article>

        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2">
            <IconMail size={18} stroke={1.9} />
            <h3 className="text-base font-semibold text-slate-900">
              {t('app.settings.billing.invoices.title', { defaultValue: 'Invoices' })}
            </h3>
          </div>
          {invoices.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">
              {t('app.settings.billing.invoices.empty', { defaultValue: 'No Stripe invoices are available yet.' })}
            </p>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t('app.settings.billing.invoices.columns.invoice', { defaultValue: 'Invoice' })}</th>
                    <th>{t('app.settings.billing.invoices.columns.status', { defaultValue: 'Status' })}</th>
                    <th>{t('app.settings.billing.invoices.columns.amount', { defaultValue: 'Amount' })}</th>
                    <th>{t('app.settings.billing.invoices.columns.period', { defaultValue: 'Period' })}</th>
                    <th>{t('app.settings.billing.invoices.columns.actions', { defaultValue: 'Actions' })}</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((invoice: BillingInvoice) => (
                    <tr key={invoice.id}>
                      <td>
                        <div className="font-medium text-slate-900">{invoice.number || invoice.id}</div>
                        <div className="text-xs text-slate-500">{formatDate(invoice.created_at, notAvailableLabel)}</div>
                      </td>
                      <td>{t(`app.invoices.status.${invoice.status}`, { defaultValue: invoice.status })}</td>
                      <td>{formatAmount(invoice.amount_paid_minor ?? invoice.total_minor, invoice.currency)}</td>
                      <td>
                        {formatDate(invoice.period_start, notAvailableLabel)} - {formatDate(invoice.period_end, notAvailableLabel)}
                      </td>
                      <td>
                        <div className="flex flex-wrap gap-2">
                          {invoice.hosted_invoice_url ? (
                            <a href={invoice.hosted_invoice_url} target="_blank" rel="noopener noreferrer" className="btn-secondary btn-xs">
                              {t('app.settings.billing.invoices.open', { defaultValue: 'Open' })}
                            </a>
                          ) : null}
                          {invoice.invoice_pdf_url ? (
                            <a href={invoice.invoice_pdf_url} target="_blank" rel="noopener noreferrer" className="btn-secondary btn-xs">
                              {t('app.settings.billing.invoices.pdf', { defaultValue: 'PDF' })}
                            </a>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      </section>

      {!isStripe ? (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">
            {t('app.settings.billing.checkout_sim.title', { defaultValue: 'Local billing simulation' })}
          </h3>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.settings.billing.checkout_sim.subtitle', {
              defaultValue: 'These controls are only shown when Stripe is not active for the current tenant.',
            })}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" className="btn-primary" onClick={() => void simulateOutcome('success')} disabled={isCheckoutLoading}>
              {t('app.settings.billing.checkout_sim.success', { defaultValue: 'Simulate success' })}
            </button>
            <button type="button" className="btn-secondary" onClick={() => void simulateOutcome('cancel')} disabled={isCheckoutLoading}>
              {t('app.settings.billing.checkout_sim.cancel', { defaultValue: 'Simulate cancel' })}
            </button>
            <button type="button" className="btn-danger" onClick={() => void simulateOutcome('error')} disabled={isCheckoutLoading}>
              {t('app.settings.billing.checkout_sim.error', { defaultValue: 'Simulate card error' })}
            </button>
            <button type="button" className="btn-secondary" onClick={() => void clearCheckoutState()} disabled={isCheckoutLoading}>
              <IconRefresh size={15} stroke={1.9} />
              <span>{t('common.reset', { defaultValue: 'Reset' })}</span>
            </button>
          </div>
        </section>
      ) : null}
    </div>
  )
}
