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
import { Modal } from '../../components/Modal'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import {
  cancelBillingSubscription,
  changeBillingPlan,
  createAddonPackCheckout,
  createBillingCheckoutSession,
  createBillingPortalLink,
  createPortalCandidatesPackCheckout,
  getBillingSummary,
  reactivateBillingSubscription,
  simulateBillingCheckoutResolution,
  updateBillingCompanySlots,
  type BillingCheckoutSession,
  type BillingHistoryItem,
  type BillingInvoice,
  type BillingPlan,
  type BillingSubscription,
  type BillingSummary,
} from '../../api/billing'
import {
  dispatchBillingSubscriptionUpdated,
  primeBillingSubscriptionCache,
} from '../../api/billingSubscriptionCache'
import { ACTIVATION_PATHS } from '../../app/activationRoutes'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
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

function coerceIntervalForPlan(
  iv: 'month' | 'year',
  ap: BillingPlan | undefined,
  stripeMode: boolean,
): 'month' | 'year' {
  if (!stripeMode || !ap) return iv
  const hasM = Boolean(ap.stripe_month_configured)
  const hasY = Boolean(ap.stripe_year_configured)
  if (!hasM && hasY) return 'year'
  if (hasM && !hasY) return 'month'
  if (iv === 'year' && !hasY && hasM) return 'month'
  if (iv === 'month' && !hasM && hasY) return 'year'
  return iv
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

/** Backend convention: cap 0 means unlimited (display as ∞). */
function formatBillingUsageCap(limit: number | null | undefined) {
  const n = limit ?? 0
  return n === 0 ? '∞' : n
}

function stripeInvoiceStatusLabel(
  status: string,
  translate: (key: string, options?: { values?: Record<string, string | number> }) => string
) {
  const key = `app.settings.billing.invoices.stripe_status.${status}`
  const rendered = translate(key)
  return rendered === key ? status : rendered
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
      label: t('app.settings.billing.status.cancel_at_period_end.label'),
      tone: 'warning',
      description: subscription.current_period_end
        ? t('app.settings.billing.status.cancel_at_period_end.description_with_date', {
            values: { date: formatDate(subscription.current_period_end, fallback) },
          })
        : t('app.settings.billing.status.cancel_at_period_end.description'),
    }
  }
  switch (normalized) {
    case 'active':
      return {
        label: t('app.settings.billing.status.active.label'),
        tone: 'success',
        description: t('app.settings.billing.status.active.description'),
      }
    case 'trial':
      return {
        label: t('app.settings.billing.status.trial.label'),
        tone: 'info',
        description: t('app.settings.billing.status.trial.description'),
      }
    case 'past_due':
      return {
        label: t('app.settings.billing.status.past_due.label'),
        tone: 'danger',
        description: t('app.settings.billing.status.past_due.description'),
      }
    case 'incomplete':
      return {
        label: t('app.settings.billing.status.incomplete.label'),
        tone: 'warning',
        description: t('app.settings.billing.status.incomplete.description'),
      }
    case 'canceled':
      return {
        label: t('app.settings.billing.status.canceled.label'),
        tone: 'danger',
        description: t('app.settings.billing.status.canceled.description'),
      }
    default:
      return {
        label: normalized || t('app.settings.billing.status.unknown.label'),
        tone: 'info',
        description: t('app.settings.billing.status.unknown.description'),
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

function openCheckoutTab(title: string, bodyText: string) {
  if (typeof window === 'undefined') return null
  const popup = window.open('about:blank', '_blank')
  if (!popup) return null
  try {
    popup.opener = null
    popup.document.title = title
    popup.document.body.innerHTML =
      `<div style="font-family: sans-serif; padding: 24px; color: #0f172a;">${bodyText}</div>`
  } catch {
    // Cross-window writes can fail in some browsers; navigation is still enough.
  }
  return popup
}

export default function BillingWorkspacePage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const [subscription, setSubscription] = useState<BillingSubscription | null>(null)
  const [summary, setSummary] = useState<BillingSummary | null>(null)
  const [lastCheckout, setLastCheckout] = useState<BillingCheckoutSession | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isCheckoutLoading, setIsCheckoutLoading] = useState(false)
  const [isPortalLoading, setIsPortalLoading] = useState(false)
  const [isPortalPackLoading, setIsPortalPackLoading] = useState(false)
  const [isMutationLoading, setIsMutationLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [checkoutState, setCheckoutState] = useState<CheckoutState>('idle')
  const [actionNotice, setActionNotice] = useState<ActionNotice>(null)
  const [isVerifyingCheckout, setIsVerifyingCheckout] = useState(false)
  const [isVerifyingPortalPack, setIsVerifyingPortalPack] = useState(false)
  const [isVerifyingAddonPack, setIsVerifyingAddonPack] = useState(false)
  const [addonCheckoutSku, setAddonCheckoutSku] = useState<string | null>(null)
  const [operatingCompanyCount, setOperatingCompanyCount] = useState(0)
  const [companySlotsInput, setCompanySlotsInput] = useState('0')
  const [recommendedFromQuery, setRecommendedFromQuery] = useState<number>(0)
  const [companySlotsRecoveryFocus, setCompanySlotsRecoveryFocus] = useState(false)
  const [planIntervalByCode, setPlanIntervalByCode] = useState<Record<PlanCode, 'month' | 'year'>>({
    starter: 'month',
    team: 'month',
    pro: 'month',
  })

  const broadcastSubscription = useCallback((sub: BillingSubscription) => {
    primeBillingSubscriptionCache(sub)
    dispatchBillingSubscriptionUpdated()
  }, [])

  const reloadSummary = useCallback(async () => {
    const data = await getBillingSummary()
    setSummary(data)
    setSubscription(data.subscription)
    setCheckoutState(normalizeSubscriptionState(data.subscription))
    broadcastSubscription(data.subscription)
    return data
  }, [broadcastSubscription])

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
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.settings.billing.load_error'))) return
        setError(
          getFriendlyErrorInfo(err, t('app.settings.billing.load_error'), t),
        )
      } finally {
        if (mounted) setIsLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
  }, [planLimitModal, reloadSummary, t])

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
          title: t('app.settings.billing.action_notice.company_slots_recommended_title'),
          text: t('app.settings.billing.action_notice.company_slots_recommended_text', { values: { count: recommended },
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
  const notAvailableLabel = t('app.settings.billing.not_available')
  const statusMeta = getStatusMeta(subscription, t, notAvailableLabel)

  useEffect(() => {
    if (!subscription?.billing_interval) return
    const ac = getPlanCode(subscription.plan_code)
    const iv = subscription.billing_interval === 'year' ? 'year' : 'month'
    setPlanIntervalByCode((prev) => ({ ...prev, [ac]: iv }))
  }, [subscription?.plan_code, subscription?.billing_interval])

  useEffect(() => {
    if (!summary?.available_plans) return
    setPlanIntervalByCode((prev) => {
      const next = { ...prev }
      for (const p of summary.available_plans) {
        const c = p.code as PlanCode
        const coerced = coerceIntervalForPlan(prev[c] ?? 'month', p, isStripe)
        next[c] = coerced
      }
      return next
    })
  }, [summary?.available_plans, isStripe])
  const trialDaysLeft = useMemo(() => {
    if (!subscription?.trial_ends_at) return null
    const dt = new Date(subscription.trial_ends_at)
    if (Number.isNaN(dt.getTime())) return null
    return Math.max(0, Math.ceil((dt.getTime() - Date.now()) / DAY_MS))
  }, [subscription?.trial_ends_at])

  const plans = useMemo<PlanDef[]>(() => {
    const codes: PlanCode[] = ['starter', 'team', 'pro']
    const apiMap = new Map<string, BillingPlan>(
      (summary?.available_plans ?? []).map((p) => [p.code, p]),
    )
    return codes.map((code) => {
      const ap = apiMap.get(code)
      const iv = coerceIntervalForPlan(planIntervalByCode[code] ?? 'month', ap, isStripe)
      const name = (ap?.name || '').trim() || t(`app.settings.billing.plans.${code}.name`)
      let price: string
      if (ap && typeof ap.monthly_price_usd === 'number') {
        if (iv === 'year' && ap.yearly_equivalent_monthly_eur != null) {
          price = t('app.settings.billing.plan_price_from_api.year', {
            values: { amount: ap.yearly_equivalent_monthly_eur },
          })
        } else if (iv === 'year') {
          price = t(`app.settings.billing.plans.${code}.price_year`)
        } else {
          price = t('app.settings.billing.plan_price_from_api.month', {
            values: { amount: ap.monthly_price_usd },
          })
        }
      } else {
        price =
          iv === 'year'
            ? t(`app.settings.billing.plans.${code}.price_year`)
            : t(`app.settings.billing.plans.${code}.price_month`)
      }
      return {
        code,
        name,
        price,
        seatsLabel: t(`app.settings.billing.plans.${code}.seats`),
        featureLabel: t(`app.settings.billing.plans.${code}.feature`),
      }
    })
  }, [planIntervalByCode, summary?.available_plans, t, isStripe])

  const addonOffersForUi = useMemo(
    () =>
      (summary?.addon_checkout_offers ?? []).filter(
        (o) => o.sku !== 'pack_portal_candidates' && o.sku !== 'pack_lead_forms_5',
      ),
    [summary?.addon_checkout_offers],
  )

  const leadFormsPackOffer = useMemo(
    () => summary?.addon_checkout_offers?.find((o) => o.sku === 'pack_lead_forms_5'),
    [summary?.addon_checkout_offers],
  )

  const addonOfferDisplayTitle = useCallback(
    (offer: { sku: string; label: string }) => {
      const key = `app.settings.billing.addon_offers.sku.${offer.sku}`
      const localized = t(key)
      return localized === key ? offer.label : localized
    },
    [t],
  )

  const [checkoutConfirmPlan, setCheckoutConfirmPlan] = useState<PlanCode | null>(null)

  const startCheckout = async (plan: PlanCode) => {
    const checkoutWindow = openCheckoutTab(
      t('app.settings.billing.checkout.popup_title'),
      t('app.settings.billing.checkout.popup_opening'),
    )
    setIsCheckoutLoading(true)
    setError(null)
    setActionNotice(null)
    try {
      const origin = typeof window !== 'undefined' ? window.location.origin : ''
      const successUrl = `${origin}${CRM_APP_PATHS.settingsBilling}?checkout=success`
      const cancelUrl = `${origin}${CRM_APP_PATHS.settingsBilling}?checkout=cancel`
      const iv = coerceIntervalForPlan(planIntervalByCode[plan] ?? 'month', summary?.available_plans?.find((p) => p.code === plan), isStripe)
      const session = await createBillingCheckoutSession({
        plan_code: plan,
        billing_interval: iv,
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
            title: t('app.settings.billing.popup_blocked_title'),
            hint: t('app.settings.billing.popup_blocked_hint'),
          })
        }
      }
    } catch (err: any) {
      if (checkoutWindow && !checkoutWindow.closed) checkoutWindow.close()
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.settings.billing.checkout_error'))) return
      setError(
        getFriendlyErrorInfo(err, t('app.settings.billing.checkout_error'), t),
      )
    } finally {
      setIsCheckoutLoading(false)
    }
  }

  const simulateOutcome = async (outcome: 'success' | 'cancel' | 'error') => {
    const sessionId = lastCheckout?.session_id || subscription?.checkout_session_id
    if (!sessionId) {
      setError({
        title: t('app.settings.billing.no_checkout_session'),
        hint: t('app.settings.billing.checkout_sim.session_required_hint'),
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
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.settings.billing.simulation_error'))) return
      setError(
        getFriendlyErrorInfo(err, t('app.settings.billing.simulation_error'), t),
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
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.settings.billing.portal_error'))) return
      setError(
        getFriendlyErrorInfo(err, t('app.settings.billing.portal_error'), t),
      )
    } finally {
      setIsPortalLoading(false)
    }
  }

  const buyPortalPack = async () => {
    const checkoutWindow = openCheckoutTab(
      t('app.settings.billing.checkout.popup_title'),
      t('app.settings.billing.checkout.popup_opening'),
    )
    setIsPortalPackLoading(true)
    setError(null)
    setActionNotice(null)
    try {
      const origin = typeof window !== 'undefined' ? window.location.origin : ''
      const successUrl = `${origin}${CRM_APP_PATHS.settingsBilling}?portal_pack=success`
      const cancelUrl = `${origin}${CRM_APP_PATHS.settingsBilling}?portal_pack=cancel`
      const session = await createPortalCandidatesPackCheckout({
        success_url: successUrl,
        cancel_url: cancelUrl,
      })
      await reloadSummary()
      if (session.provider === 'stripe' && session.checkout_url) {
        if (checkoutWindow) {
          checkoutWindow.location.replace(session.checkout_url)
        } else {
          setError({
            title: t('app.settings.billing.popup_blocked_title'),
            hint: t('app.settings.billing.popup_blocked_hint'),
          })
        }
      } else if (session.checkout_url) {
        if (checkoutWindow && !checkoutWindow.closed) checkoutWindow.close()
        window.location.assign(session.checkout_url)
      }
    } catch (err: any) {
      if (checkoutWindow && !checkoutWindow.closed) checkoutWindow.close()
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.settings.billing.portal_pack_error'))) return
      setError(getFriendlyErrorInfo(err, t('app.settings.billing.portal_pack_error'), t))
    } finally {
      setIsPortalPackLoading(false)
    }
  }

  const buyAddonPack = async (sku: string) => {
    const checkoutWindow = openCheckoutTab(
      t('app.settings.billing.checkout.popup_title'),
      t('app.settings.billing.checkout.popup_opening'),
    )
    setAddonCheckoutSku(sku)
    setError(null)
    setActionNotice(null)
    try {
      const origin = typeof window !== 'undefined' ? window.location.origin : ''
      const successUrl = `${origin}${CRM_APP_PATHS.settingsBilling}?billing_addon=success&sku=${encodeURIComponent(sku)}`
      const cancelUrl = `${origin}${CRM_APP_PATHS.settingsBilling}?billing_addon=cancel`
      const session = await createAddonPackCheckout({
        sku,
        success_url: successUrl,
        cancel_url: cancelUrl,
      })
      await reloadSummary()
      if (session.provider === 'stripe' && session.checkout_url) {
        if (checkoutWindow) {
          checkoutWindow.location.replace(session.checkout_url)
        } else {
          setError({
            title: t('app.settings.billing.popup_blocked_title'),
            hint: t('app.settings.billing.popup_blocked_hint'),
          })
        }
      } else if (session.checkout_url) {
        if (checkoutWindow && !checkoutWindow.closed) checkoutWindow.close()
        window.location.assign(session.checkout_url)
      }
    } catch (err: any) {
      if (checkoutWindow && !checkoutWindow.closed) checkoutWindow.close()
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.settings.billing.addon_pack_error'))) return
      setError(getFriendlyErrorInfo(err, t('app.settings.billing.addon_pack_error'), t))
    } finally {
      setAddonCheckoutSku(null)
    }
  }

  const handlePlanAction = async (plan: PlanCode) => {
    if (isTrial || !subscription?.subscription_id || subscription?.status === 'incomplete') {
      setCheckoutConfirmPlan(plan)
      return
    }
    const checkoutWindow = openCheckoutTab(
      t('app.settings.billing.checkout.popup_title'),
      t('app.settings.billing.checkout.popup_opening'),
    )
    setIsMutationLoading(true)
    setError(null)
    setActionNotice(null)
    try {
      const origin = typeof window !== 'undefined' ? window.location.origin : ''
      const ap = summary?.available_plans?.find((p) => p.code === plan)
      const iv = coerceIntervalForPlan(planIntervalByCode[plan] ?? 'month', ap, isStripe)
      const data = await changeBillingPlan({
        plan_code: plan,
        billing_interval: iv,
        success_url: `${origin}${CRM_APP_PATHS.settingsBilling}?checkout=success`,
        cancel_url: `${origin}${CRM_APP_PATHS.settingsBilling}?checkout=cancel`,
      })
      setSummary(data)
      setSubscription(data.subscription)
      setCheckoutState(normalizeSubscriptionState(data.subscription))
      broadcastSubscription(data.subscription)
      if (data.subscription.pending_update && data.subscription.pending_plan_code === plan) {
        setActionNotice({
          tone: 'warning',
          title: t('app.settings.billing.action_notice.plan_change_pending_title'),
          text: t('app.settings.billing.action_notice.plan_change_pending_text', { values: { plan: plan.toUpperCase() },
          }),
        })
        if (data.subscription.pending_invoice_url) {
          if (checkoutWindow) {
            checkoutWindow.location.replace(data.subscription.pending_invoice_url)
          } else {
            setError({
              title: t('app.settings.billing.popup_blocked_title'),
              hint: t('app.settings.billing.popup_blocked_hint'),
            })
          }
        }
      } else {
        if (checkoutWindow && !checkoutWindow.closed) checkoutWindow.close()
        setActionNotice({
          tone: 'success',
          title: t('app.settings.billing.action_notice.plan_change_title'),
          text: t('app.settings.billing.action_notice.plan_change_text', { values: { plan: plan.toUpperCase() },
          }),
        })
      }
    } catch (err: any) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.settings.billing.change_plan_error'))) {
        if (checkoutWindow && !checkoutWindow.closed) checkoutWindow.close()
        return
      }
      setError(
        getFriendlyErrorInfo(err, t('app.settings.billing.change_plan_error'), t),
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
      broadcastSubscription(data.subscription)
      setActionNotice({
        tone: 'warning',
        title: t('app.settings.billing.action_notice.cancel_title'),
        text: t('app.settings.billing.action_notice.cancel_text', { values: { date: formatDate(data.subscription.current_period_end, notAvailableLabel) },
        }),
      })
    } catch (err: any) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.settings.billing.cancel_error'))) return
      setError(
        getFriendlyErrorInfo(err, t('app.settings.billing.cancel_error'), t),
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
      broadcastSubscription(data.subscription)
      setActionNotice({
        tone: 'success',
        title: t('app.settings.billing.action_notice.resume_title'),
        text: t('app.settings.billing.action_notice.resume_text'),
      })
    } catch (err: any) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.settings.billing.reactivate_error'))) return
      setError(
        getFriendlyErrorInfo(err, t('app.settings.billing.reactivate_error'), t),
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
      broadcastSubscription(data.subscription)
      setCompanySlotsInput(String(data.company_slots?.extra_slots ?? desired))
      const used = Number(data.company_slots?.used ?? 0)
      const effective = Number(data.company_slots?.effective_limit ?? 0)
      const overflow = effective > 0 && used > effective
      if (overflow) {
        const missing = Math.max(1, used - effective)
        setActionNotice({
          tone: 'warning',
          title: t('app.settings.billing.action_notice.company_slots_overflow_title'),
          text: t('app.settings.billing.action_notice.company_slots_overflow_text', { values: { count: missing },
          }),
        })
      } else {
        setActionNotice({
          tone: 'success',
          title: t('app.settings.billing.action_notice.company_slots_title'),
          text: t('app.settings.billing.action_notice.company_slots_text', { values: { count: String(data.company_slots?.extra_slots ?? desired) },
          }),
        })
      }
    } catch (err: any) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.settings.billing.company_slots_error'))) return
      setError(
        getFriendlyErrorInfo(err, t('app.settings.billing.company_slots_error'), t),
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
        title: t('app.settings.billing.notice.success_title'),
        text: t('app.settings.billing.notice.success_text'),
      }
    }
    if (checkoutState === 'cancel') {
      return {
        tone: 'border-amber-200 bg-amber-50 text-amber-800',
        title: t('app.settings.billing.notice.cancel_title'),
        text: t('app.settings.billing.notice.cancel_text'),
      }
    }
    if (checkoutState === 'error') {
      return {
        tone: 'border-rose-200 bg-rose-50 text-rose-800',
        title: t('app.settings.billing.notice.error_title'),
        text: t('app.settings.billing.notice.error_text'),
      }
    }
    if (checkoutState === 'incomplete') {
      return {
        tone: 'border-amber-200 bg-amber-50 text-amber-800',
        title: t('app.settings.billing.notice.incomplete_title'),
        text: t('app.settings.billing.notice.incomplete_text'),
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

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    if (params.get('portal_pack') !== 'cancel') return
    params.delete('portal_pack')
    const next = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ''}`
    window.history.replaceState({}, '', next)
    setActionNotice({
      tone: 'warning',
      title: t('app.settings.billing.action_notice.portal_pack_cancel_title'),
      text: t('app.settings.billing.action_notice.portal_pack_cancel_text'),
    })
  }, [t])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    if (params.get('portal_pack') !== 'success') return
    let cancelled = false
    setIsVerifyingPortalPack(true)
    let startAddon: number | null = null
    const stripPortalPackParam = () => {
      params.delete('portal_pack')
      const next = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ''}`
      window.history.replaceState({}, '', next)
    }
    const showPortalPackSuccess = () => {
      stripPortalPackParam()
      setIsVerifyingPortalPack(false)
      setActionNotice({
        tone: 'success',
        title: t('app.settings.billing.action_notice.portal_pack_success_title'),
        text: t('app.settings.billing.action_notice.portal_pack_success_text'),
      })
    }
    const run = async () => {
      for (let attempt = 0; attempt < 5; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, attempt === 0 ? 0 : 2000))
        if (cancelled) return
        try {
          const data = await reloadSummary()
          if (cancelled) return
          const addon = data.portal_candidates?.pack_addon ?? 0
          if (startAddon === null) startAddon = addon
          const increased = addon > (startAddon ?? 0)
          if (increased || attempt === 4) {
            showPortalPackSuccess()
            return
          }
        } catch {
          // keep retrying
        }
      }
      if (!cancelled) showPortalPackSuccess()
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [reloadSummary, t])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    if (params.get('billing_addon') !== 'cancel') return
    params.delete('billing_addon')
    params.delete('sku')
    const next = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ''}`
    window.history.replaceState({}, '', next)
    setActionNotice({
      tone: 'warning',
      title: t('app.settings.billing.action_notice.billing_addon_cancel_title'),
      text: t('app.settings.billing.action_notice.billing_addon_cancel_text'),
    })
  }, [t])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    if (params.get('billing_addon') !== 'success') return
    let cancelled = false
    setIsVerifyingAddonPack(true)
    const stripParams = () => {
      params.delete('billing_addon')
      params.delete('sku')
      const next = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ''}`
      window.history.replaceState({}, '', next)
    }
    const finishSuccess = () => {
      stripParams()
      setIsVerifyingAddonPack(false)
      setActionNotice({
        tone: 'success',
        title: t('app.settings.billing.action_notice.billing_addon_success_title'),
        text: t('app.settings.billing.action_notice.billing_addon_success_text'),
      })
    }
    const run = async () => {
      for (let attempt = 0; attempt < 5; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, attempt === 0 ? 0 : 2000))
        if (cancelled) return
        try {
          await reloadSummary()
          if (cancelled) return
        } catch {
          // keep retrying
        }
      }
      if (!cancelled) finishSuccess()
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [reloadSummary, t])

  return (
    <div className="space-y-4">
      <header className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
          <IconCreditCard size={18} stroke={1.9} />
          {t('app.settings.billing.badge')}
        </div>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <h1 className="text-2xl font-semibold text-slate-900">
              {t('app.settings.billing.title')}
            </h1>
            <p className="max-w-3xl text-sm text-slate-600">
              {t('app.settings.billing.subtitle')}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={() => void reloadSummary()} disabled={isLoading}>
              <IconRefresh size={15} stroke={1.9} />
              <span>{t('common.actions.refresh')}</span>
            </button>
            <button type="button" className="btn-secondary" onClick={openPortal} disabled={isPortalLoading}>
              <IconExternalLink size={15} stroke={1.9} />
              <span>{t('app.settings.billing.portal')}</span>
            </button>
          </div>
        </div>
      </header>

      {!isTrial && subscription?.status === 'past_due' ? (
        <section className="rounded-xl border border-rose-300 bg-rose-50 p-4 shadow-sm text-rose-950">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex gap-3">
              <IconAlertTriangle size={22} stroke={1.9} className="shrink-0 text-rose-700" />
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wide text-rose-800">
                  {t('app.settings.billing.past_due.badge')}
                </p>
                <h2 className="text-sm font-semibold text-rose-950">
                  {t('app.settings.billing.past_due.title')}
                </h2>
                <p className="text-sm text-rose-900/90">
                  {t('app.settings.billing.past_due.subtitle')}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button type="button" className="btn-primary" onClick={() => void openPortal()} disabled={isPortalLoading}>
                {t('app.settings.billing.past_due.cta')}
              </button>
              <button type="button" className="btn-secondary" onClick={() => void reloadSummary()} disabled={isLoading}>
                {t('app.settings.billing.refresh_status')}
              </button>
            </div>
          </div>
        </section>
      ) : null}

      {isTrial && (
        <section className="rounded-xl border border-amber-300 bg-amber-50 p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
                {t('app.settings.billing.trial.badge')}
              </p>
              <h2 className="text-sm font-semibold text-amber-950">
                {trialDaysLeft != null
                  ? t('app.settings.billing.trial.title_with_days', { values: { days: trialDaysLeft },
                    })
                  : t('app.settings.billing.trial.title')}
              </h2>
              <p className="text-xs text-amber-950/90">
                {t('app.settings.billing.trial.subtitle')}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="btn-primary"
                onClick={() => setCheckoutConfirmPlan(activePlan)}
                disabled={isCheckoutLoading}
              >
                {t('app.settings.billing.trial.cta')}
              </button>
              <Link to={ACTIVATION_PATHS.overview} className="btn-secondary">
                {t('app.settings.billing.trial.secondary_cta')}
              </Link>
            </div>
          </div>
        </section>
      )}

      {error && (
        <ErrorRecoveryBanner
          info={error}
          onRetry={() => void reloadSummary()}
          retryLabel={t('common.actions.refresh')}
          {...friendlyErrorBannerSecondary(error, CRM_APP_PATHS.settingsBilling, t('app.settings.billing.badge'))}
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

      {isVerifyingCheckout || isVerifyingPortalPack || isVerifyingAddonPack ? (
        <section className="rounded-xl border border-brand-200 bg-brand-50 p-4 shadow-sm text-brand-900">
          <div className="flex items-start gap-2">
            <IconRefresh size={18} stroke={1.9} />
            <div>
              <p className="text-sm font-semibold">
                {isVerifyingPortalPack && !isVerifyingCheckout
                  ? t('app.settings.billing.verification.portal_pack_title')
                  : isVerifyingAddonPack && !isVerifyingCheckout && !isVerifyingPortalPack
                    ? t('app.settings.billing.verification.billing_addon_title')
                    : t('app.settings.billing.verification.title')}
              </p>
              <p className="mt-1 text-sm">
                {isVerifyingPortalPack && !isVerifyingCheckout
                  ? t('app.settings.billing.verification.portal_pack_text')
                  : isVerifyingAddonPack && !isVerifyingCheckout && !isVerifyingPortalPack
                    ? t('app.settings.billing.verification.billing_addon_text')
                    : t('app.settings.billing.verification.text')}
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
                {t('app.settings.billing.pending_upgrade.title')}
              </p>
              <p className="mt-1 text-sm">
                {t('app.settings.billing.pending_upgrade.text', { values: {
                    currentPlan: String(subscription.plan_code || '').toUpperCase(),
                    nextPlan: String(subscription.pending_plan_code || '').toUpperCase(),
                  },
                })}
              </p>
            </div>
            <button type="button" className="btn-secondary" onClick={() => void reloadSummary()}>
              {t('app.settings.billing.refresh_status')}
            </button>
          </div>
        </section>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.settings.billing.labels.current_plan')}
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
                {t('app.settings.billing.labels.paid_plan')}
              </dt>
              <dd className="mt-1 text-sm font-medium text-slate-900">{plans.find((plan) => plan.code === activePlan)?.price || '-'}</dd>
            </div>
            <div className="rounded-lg border border-slate-200 p-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.settings.billing.labels.subscription_started')}
              </dt>
              <dd className="mt-1 text-sm font-medium text-slate-900">
                {formatDate(subscription?.activated_at || subscription?.current_period_start, notAvailableLabel)}
              </dd>
            </div>
            <div className="rounded-lg border border-slate-200 p-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {subscription?.cancel_at_period_end
                  ? t('app.settings.billing.labels.access_ends')
                  : t('app.settings.billing.labels.current_period_ends')}
              </dt>
              <dd className="mt-1 text-sm font-medium text-slate-900">
                {formatDate(subscription?.current_period_end, notAvailableLabel)}
              </dd>
            </div>
            <div className="rounded-lg border border-slate-200 p-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.settings.billing.labels.last_billing_update')}
              </dt>
              <dd className="mt-1 text-sm font-medium text-slate-900">
                {formatDateTime(subscription?.updated_at, notAvailableLabel)}
              </dd>
            </div>
          </dl>

          <div className="mt-5 flex flex-wrap gap-2">
            {subscription?.cancel_at_period_end ? (
              <button type="button" className="btn-primary" onClick={handleReactivate} disabled={isMutationLoading}>
                {t('app.settings.billing.reactivate')}
              </button>
            ) : (
              <button
                type="button"
                className="btn-primary"
                onClick={() =>
                  void (isTrial || subscription?.status === 'incomplete'
                    ? setCheckoutConfirmPlan(activePlan)
                    : openPortal())
                }
                disabled={isCheckoutLoading || isPortalLoading}
              >
                {isTrial || subscription?.status === 'incomplete'
                  ? t('app.settings.billing.subscribe')
                  : subscription?.status === 'past_due'
                    ? t('app.settings.billing.past_due.cta')
                    : t('app.settings.billing.manage_in_stripe')}
              </button>
            )}
            {!subscription?.cancel_at_period_end && subscription?.status !== 'canceled' ? (
              <button type="button" className="btn-danger" onClick={handleCancel} disabled={isMutationLoading}>
                {t('app.settings.billing.cancel')}
              </button>
            ) : null}
            {(subscription?.status === 'incomplete' || subscription?.status === 'past_due') && !isVerifyingCheckout ? (
              <button type="button" className="btn-secondary" onClick={() => void reloadSummary()} disabled={isLoading}>
                {t('app.settings.billing.refresh_status')}
              </button>
            ) : null}
          </div>

          <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
            <p className="font-medium text-slate-900">
              {t('app.settings.billing.communication.title')}
            </p>
            <p className="mt-1">
              {t('app.settings.billing.communication.description')}
            </p>
          </div>
        </article>

        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">
            {t('app.settings.billing.manage_title')}
          </h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-600">
            <li>{t('app.settings.billing.actions_help.subscribe')}</li>
            <li>
              {t('app.settings.billing.actions_help.manage')}
            </li>
            <li>
              {t('app.settings.billing.actions_help.past_due')}
            </li>
            <li>{t('app.settings.billing.actions_help.cancel')}</li>
            <li>{t('app.settings.billing.actions_help.resume')}</li>
          </ul>
          <div className="mt-5 rounded-lg border border-slate-200 p-3 text-sm">
            <p className="font-medium text-slate-900">
              {t('app.settings.billing.references.title')}
            </p>
            <p className="mt-2 text-slate-600">
              {t('app.settings.billing.references.customer_id', { values: { value: subscription?.customer_id || t('app.settings.billing.not_available_yet') },
              })}
            </p>
            <p className="mt-1 text-slate-600">
              {t('app.settings.billing.references.subscription_id', { values: { value: subscription?.subscription_id || t('app.settings.billing.not_available_yet') },
              })}
            </p>
          </div>
          <div className="mt-4 rounded-lg border border-slate-200 p-3 text-sm">
            <p className="font-medium text-slate-900">{t('app.settings.billing.legal.title')}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer" className="btn-secondary btn-sm">
                {t('app.settings.billing.trial.legal_terms')}
              </a>
              <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="btn-secondary btn-sm">
                {t('app.settings.billing.trial.legal_privacy')}
              </a>
              <a href="/legal/cookies.html" target="_blank" rel="noopener noreferrer" className="btn-secondary btn-sm">
                {t('app.settings.billing.trial.legal_cookies')}
              </a>
            </div>
          </div>
        </article>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {plans.map((plan) => {
          const isActive = plan.code === activePlan
          const ap = (summary?.available_plans ?? []).find((p) => p.code === plan.code)
          const iv = coerceIntervalForPlan(planIntervalByCode[plan.code] ?? 'month', ap, isStripe)
          const monthOk = !isStripe || Boolean(ap?.stripe_month_configured)
          const yearOk = !isStripe || Boolean(ap?.stripe_year_configured)
          const selectedIntervalOk = iv === 'month' ? monthOk : yearOk
          const subIv: 'month' | 'year' =
            subscription?.billing_interval === 'year' ? 'year' : 'month'
          const canApplyIntervalOnly =
            isActive &&
            Boolean(subscription?.subscription_id) &&
            iv !== subIv &&
            selectedIntervalOk
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
                    {t('app.settings.billing.active_plan')}
                  </span>
                ) : null}
              </div>
              <p className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                {t('app.settings.billing.billing_cycle.label')}
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <button
                  type="button"
                  className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                    iv === 'month'
                      ? 'border-brand-500 bg-brand-50 text-brand-900'
                      : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                  } ${!monthOk ? 'cursor-not-allowed opacity-50' : ''}`}
                  disabled={!monthOk}
                  title={!monthOk ? t('app.settings.billing.billing_cycle.not_configured_month') : undefined}
                  onClick={() =>
                    setPlanIntervalByCode((prev) => ({
                      ...prev,
                      [plan.code]: 'month',
                    }))
                  }
                >
                  {t('app.settings.billing.billing_cycle.monthly')}
                </button>
                <button
                  type="button"
                  className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                    iv === 'year'
                      ? 'border-brand-500 bg-brand-50 text-brand-900'
                      : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                  } ${!yearOk ? 'cursor-not-allowed opacity-50' : ''}`}
                  disabled={!yearOk}
                  title={!yearOk ? t('app.settings.billing.billing_cycle.not_configured_year') : undefined}
                  onClick={() =>
                    setPlanIntervalByCode((prev) => ({
                      ...prev,
                      [plan.code]: 'year',
                    }))
                  }
                >
                  {t('app.settings.billing.billing_cycle.yearly')}
                </button>
              </div>
              <p className="mt-2 text-xl font-semibold text-slate-900">{plan.price}</p>
              <ul className="mt-3 space-y-1 text-sm text-slate-600">
                <li>{plan.seatsLabel}</li>
                <li>{plan.featureLabel}</li>
              </ul>
              <button
                type="button"
                className="btn-secondary mt-4 w-full justify-center"
                disabled={
                  (isActive && !canApplyIntervalOnly) ||
                  isCheckoutLoading ||
                  isMutationLoading ||
                  isPortalLoading ||
                  (isStripe && !selectedIntervalOk)
                }
                onClick={() => void handlePlanAction(plan.code)}
              >
                {canApplyIntervalOnly
                  ? t('app.settings.billing.apply_billing_interval')
                  : isActive
                    ? t('app.settings.billing.current_plan')
                    : isTrial || !subscription?.subscription_id || subscription?.status === 'incomplete'
                        ? t('app.settings.billing.subscribe_plan')
                        : t('app.settings.billing.choose_plan')}
              </button>
            </article>
          )
        })}
      </section>

      <p className="text-xs text-slate-500">{t('app.settings.billing.pricing_catalog_hint')}</p>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">
          {t('app.settings.billing.usage_title')}
        </h3>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div id="company-slots-usage-card" className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.recruiters', { values: { used: summary?.usage.recruiter_count ?? 0, limit: summary?.license?.max_recruiters ?? 0 },
            })}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.supervisors', { values: { used: summary?.usage.supervisor_count ?? 0, limit: summary?.license?.max_supervisors ?? 0 },
            })}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.client_managers', { values: { used: summary?.usage.client_manager_count ?? 0, limit: summary?.license?.max_client_managers ?? 0 },
            })}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.viewers', { values: { used: summary?.usage.viewer_count ?? 0, limit: summary?.license?.max_viewers ?? 0 },
            })}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.leads_month', {
              values: {
                used: summary?.usage.leads_created_this_month ?? 0,
                limit: formatBillingUsageCap(summary?.usage_caps?.max_leads_created_per_month),
              },
            })}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.candidates', {
              values: {
                used: summary?.usage.candidates_active_count ?? 0,
                limit: formatBillingUsageCap(summary?.usage_caps?.max_candidates_active),
              },
            })}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.documents', {
              values: {
                used: summary?.usage.documents_count ?? 0,
                limit: formatBillingUsageCap(summary?.usage_caps?.max_documents),
              },
            })}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.vacancies_open', {
              values: {
                used: summary?.usage.vacancies_open_count ?? 0,
                limit: formatBillingUsageCap(summary?.usage_caps?.max_vacancies_active),
              },
            })}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.portal_links', {
              values: {
                used: summary?.usage.portal_links_active_count ?? 0,
                limit: formatBillingUsageCap(summary?.usage_caps?.max_public_portal_links),
              },
            })}
          </div>
          {summary?.portal_candidates ? (
            <div
              className={`rounded-lg border p-3 text-sm ${
                summary.portal_candidates.warning_level === 'warn_100'
                  ? 'border-amber-300 bg-amber-50 text-amber-950'
                  : summary.portal_candidates.warning_level === 'warn_80'
                    ? 'border-yellow-200 bg-yellow-50 text-yellow-950'
                    : 'border-slate-200'
              }`}
            >
              <div>
                {t('app.settings.billing.usage.portal_candidates_month', {
                  values: {
                    used: summary.portal_candidates.used_this_month_utc,
                    cap: summary.portal_candidates.cap,
                  },
                })}
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {t('app.settings.billing.usage.portal_candidates_policy')}
              </div>
              {summary.portal_candidates.warning_level === 'warn_80' ? (
                <div className="mt-1 text-xs font-medium">{t('app.settings.billing.usage.portal_candidates_warn_80')}</div>
              ) : null}
              {summary.portal_candidates.warning_level === 'warn_100' ? (
                <div className="mt-1 text-xs font-medium">{t('app.settings.billing.usage.portal_candidates_warn_100')}</div>
              ) : null}
              {(summary.portal_candidates.pack_addon ?? 0) > 0 ? (
                <div className="mt-1 text-xs text-slate-500">
                  {t('app.settings.billing.usage.portal_candidates_pack_note', {
                    values: {
                      base: summary.portal_candidates.base_cap ?? summary.portal_candidates.cap,
                      addon: summary.portal_candidates.pack_addon ?? 0,
                      cap: summary.portal_candidates.cap,
                    },
                  })}
                </div>
              ) : null}
              <div className="mt-2">
                <button
                  type="button"
                  className="btn-secondary btn-xs"
                  disabled={isPortalPackLoading || isMutationLoading}
                  onClick={() => void buyPortalPack()}
                >
                  {isPortalPackLoading
                    ? t('app.settings.billing.usage.portal_candidates_pack_loading')
                    : t('app.settings.billing.usage.portal_candidates_pack_buy', {
                        values: {
                          increment: summary.portal_candidates.pack_increment_offer ?? 500,
                        },
                      })}
                </button>
              </div>
            </div>
          ) : null}
          {summary?.lead_forms ? (
            <div
              className={`rounded-lg border p-3 text-sm ${
                summary.lead_forms.active_count >= summary.lead_forms.cap
                  ? 'border-amber-300 bg-amber-50 text-amber-950'
                  : 'border-slate-200'
              }`}
            >
              <div>
                {t('app.settings.billing.usage.lead_forms_active', {
                  values: {
                    used: summary.lead_forms.active_count,
                    cap: summary.lead_forms.cap,
                  },
                })}
              </div>
              <div className="mt-1 text-xs text-slate-500">{t('app.settings.billing.usage.lead_forms_policy')}</div>
              {summary.lead_forms.active_count >= summary.lead_forms.cap ? (
                <div className="mt-1 text-xs font-medium">{t('app.settings.billing.usage.lead_forms_warn_100')}</div>
              ) : null}
              {(summary.lead_forms.pack_addon ?? 0) > 0 ? (
                <div className="mt-1 text-xs text-slate-500">
                  {t('app.settings.billing.usage.lead_forms_pack_note', {
                    values: {
                      base: summary.lead_forms.base_cap ?? summary.lead_forms.cap,
                      addon: summary.lead_forms.pack_addon ?? 0,
                      cap: summary.lead_forms.cap,
                    },
                  })}
                </div>
              ) : null}
              {(() => {
                const offer = leadFormsPackOffer
                const purchaseAllowed =
                  offer != null &&
                  (typeof offer.purchase_allowed === 'boolean'
                    ? offer.purchase_allowed
                    : Boolean(offer.checkout_ready && offer.configured))
                if (!offer) return null
                return (
                  <div className="mt-2">
                    <button
                      type="button"
                      className="btn-secondary btn-xs"
                      disabled={!purchaseAllowed || addonCheckoutSku !== null || isMutationLoading}
                      onClick={() => void buyAddonPack('pack_lead_forms_5')}
                    >
                      {addonCheckoutSku === 'pack_lead_forms_5'
                        ? t('app.settings.billing.usage.lead_forms_pack_loading')
                        : t('app.settings.billing.usage.lead_forms_pack_buy', {
                            values: {
                              increment: offer.pack_increment ?? summary.lead_forms.pack_increment_offer ?? 5,
                            },
                          })}
                    </button>
                  </div>
                )
              })()}
            </div>
          ) : null}
          {summary?.founder_program?.tenant_enrolled && !summary.founder_program.tenant_revoked ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-950">
              {t('app.settings.billing.usage.founder_program_active')}
            </div>
          ) : null}
          {summary?.founder_program?.tenant_revoked ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
              {t('app.settings.billing.usage.founder_program_revoked')}
            </div>
          ) : null}
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.storage', { values: { used: Math.round(summary?.usage.storage_used_gb ?? 0), limit: summary?.license?.max_storage_gb ?? 0 },
            })}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {t('app.settings.billing.usage.companies', { values: {
                used: summary?.company_slots?.used ?? operatingCompanyCount,
                limit: summary?.company_slots?.unlimited
                  ? '∞'
                  : (summary?.company_slots?.effective_limit ?? summary?.license?.max_companies ?? 0),
              },
            })}
            {(summary?.company_slots?.extra_slots ?? 0) > 0 ? (
              <div className="mt-1 text-xs text-slate-500">
                {t('app.settings.billing.usage.companies_addon', { values: {
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
                aria-label={t('app.settings.billing.usage.extra_company_slots')}
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
                {t('common.actions.save')}
              </button>
            </div>
            <div className="mt-1 text-xs text-slate-500">
              {t('app.settings.billing.usage.extra_company_slots_hint')}
            </div>
            {recommendedFromQuery > 0 ? (
              <div className="mt-1 text-xs text-amber-700">
                {t('app.settings.billing.usage.extra_company_slots_recommended', { values: { count: recommendedFromQuery },
                })}
              </div>
            ) : null}
            {operatingSlotsOverflow ? (
              <div className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-900">
                {t('app.settings.billing.usage.companies_overflow', { values: { count: operatingSlotsMissing },
                })}
              </div>
            ) : null}
            {companySlotsRecoveryFocus ? (
              <div className="mt-2">
                {hasOperatingSlotCapacity ? (
                  <Link to={CRM_APP_PATHS.onboardingCompany} className="btn-primary btn-xs">
                    {t('app.settings.billing.usage.back_to_onboarding')}
                  </Link>
                ) : (
                  <div className="text-xs text-slate-500">
                    {t('app.settings.billing.usage.back_to_onboarding_hint')}
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      </section>

      {addonOffersForUi.length > 0 ? (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">{t('app.settings.billing.addon_offers.title')}</h3>
          <p className="mt-1 text-sm text-slate-600">{t('app.settings.billing.addon_offers.hint')}</p>
          <ul className="mt-4 space-y-3">
            {addonOffersForUi.map((offer) => {
              const purchaseAllowed =
                typeof offer.purchase_allowed === 'boolean'
                  ? offer.purchase_allowed
                  : Boolean(offer.checkout_ready && offer.configured)
              const blockReason = offer.purchase_block_reason ?? null
              const blockKey =
                blockReason != null && blockReason.length > 0
                  ? (`app.settings.billing.addon_offers.block.${blockReason}` as const)
                  : null
              const blockText =
                blockKey != null
                  ? (() => {
                      const tr = t(blockKey)
                      return tr === blockKey ? null : tr
                    })()
                  : null
              return (
                <li
                  key={offer.sku}
                  className="flex flex-col gap-2 rounded-lg border border-slate-200 p-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <div className="text-sm font-medium text-slate-900">{addonOfferDisplayTitle(offer)}</div>
                    <div className="mt-0.5 font-mono text-xs text-slate-500">{offer.sku}</div>
                    {!purchaseAllowed && blockText ? (
                      <div className="mt-1 text-xs text-amber-800">{blockText}</div>
                    ) : !purchaseAllowed ? (
                      <div className="mt-1 text-xs text-slate-500">{t('app.settings.billing.addon_offers.unavailable')}</div>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <button
                      type="button"
                      className="btn-secondary btn-xs"
                      disabled={!purchaseAllowed || addonCheckoutSku !== null || isMutationLoading}
                      onClick={() => void buyAddonPack(offer.sku)}
                    >
                      {addonCheckoutSku === offer.sku
                        ? t('app.settings.billing.addon_offers.buying')
                        : purchaseAllowed
                          ? t('app.settings.billing.addon_offers.buy', {
                              values: { increment: offer.pack_increment ?? 0 },
                            })
                          : t('app.settings.billing.addon_offers.buy_disabled')}
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        </section>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2">
            <IconHistory size={18} stroke={1.9} />
            <h3 className="text-base font-semibold text-slate-900">
              {t('app.settings.billing.history.title')}
            </h3>
          </div>
          {history.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">
              {t('app.settings.billing.history.empty')}
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
                          {t('app.settings.billing.history.view_invoice')}
                        </a>
                      ) : null}
                      {item.invoice_pdf_url ? (
                        <a href={item.invoice_pdf_url} target="_blank" rel="noopener noreferrer" className="btn-secondary btn-sm">
                          {t('app.settings.billing.history.download_pdf')}
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
              {t('app.settings.billing.invoices.title')}
            </h3>
          </div>
          {invoices.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">
              {t('app.settings.billing.invoices.empty')}
            </p>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t('app.settings.billing.invoices.columns.invoice')}</th>
                    <th>{t('app.settings.billing.invoices.columns.status')}</th>
                    <th>{t('app.settings.billing.invoices.columns.amount')}</th>
                    <th>{t('app.settings.billing.invoices.columns.period')}</th>
                    <th>{t('app.settings.billing.invoices.columns.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((invoice: BillingInvoice) => (
                    <tr key={invoice.id}>
                      <td>
                        <div className="font-medium text-slate-900">{invoice.number || invoice.id}</div>
                        <div className="text-xs text-slate-500">{formatDate(invoice.created_at, notAvailableLabel)}</div>
                      </td>
                      <td>{stripeInvoiceStatusLabel(invoice.status, t)}</td>
                      <td>{formatAmount(invoice.amount_paid_minor ?? invoice.total_minor, invoice.currency)}</td>
                      <td>
                        {formatDate(invoice.period_start, notAvailableLabel)} - {formatDate(invoice.period_end, notAvailableLabel)}
                      </td>
                      <td>
                        <div className="flex flex-wrap gap-2">
                          {invoice.hosted_invoice_url ? (
                            <a href={invoice.hosted_invoice_url} target="_blank" rel="noopener noreferrer" className="btn-secondary btn-xs">
                              {t('app.settings.billing.invoices.open')}
                            </a>
                          ) : null}
                          {invoice.invoice_pdf_url ? (
                            <a href={invoice.invoice_pdf_url} target="_blank" rel="noopener noreferrer" className="btn-secondary btn-xs">
                              {t('app.settings.billing.invoices.pdf')}
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
            {t('app.settings.billing.checkout_sim.title')}
          </h3>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.settings.billing.checkout_sim.subtitle')}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" className="btn-primary" onClick={() => void simulateOutcome('success')} disabled={isCheckoutLoading}>
              {t('app.settings.billing.checkout_sim.success')}
            </button>
            <button type="button" className="btn-secondary" onClick={() => void simulateOutcome('cancel')} disabled={isCheckoutLoading}>
              {t('app.settings.billing.checkout_sim.cancel')}
            </button>
            <button type="button" className="btn-danger" onClick={() => void simulateOutcome('error')} disabled={isCheckoutLoading}>
              {t('app.settings.billing.checkout_sim.error')}
            </button>
            <button type="button" className="btn-secondary" onClick={() => void clearCheckoutState()} disabled={isCheckoutLoading}>
              <IconRefresh size={15} stroke={1.9} />
              <span>{t('common.reset')}</span>
            </button>
          </div>
        </section>
      ) : null}

      <Modal
        open={checkoutConfirmPlan != null}
        onClose={() => setCheckoutConfirmPlan(null)}
        title={t('app.settings.billing.checkout_summary.title')}
        size="md"
      >
        {checkoutConfirmPlan ? (
          <div className="space-y-4 text-sm text-slate-700">
            <p>{t('app.settings.billing.checkout_summary.lead')}</p>
            <dl className="rounded-lg border border-slate-200 bg-slate-50/80 p-3 space-y-2">
              <div className="flex justify-between gap-3">
                <dt className="text-slate-500">{t('app.settings.billing.checkout_summary.plan_label')}</dt>
                <dd className="font-medium text-slate-900 text-right">
                  {plans.find((p) => p.code === checkoutConfirmPlan)?.name ?? checkoutConfirmPlan}
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-slate-500">{t('app.settings.billing.checkout_summary.billing_interval')}</dt>
                <dd className="font-medium text-slate-900 text-right">
                  {coerceIntervalForPlan(
                    planIntervalByCode[checkoutConfirmPlan] ?? 'month',
                    summary?.available_plans?.find((p) => p.code === checkoutConfirmPlan),
                    isStripe,
                  ) === 'year'
                    ? t('app.settings.billing.billing_cycle.yearly')
                    : t('app.settings.billing.billing_cycle.monthly')}
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-slate-500">{t('app.settings.billing.checkout_summary.price_label')}</dt>
                <dd className="font-medium text-slate-900 text-right">
                  {plans.find((p) => p.code === checkoutConfirmPlan)?.price ?? '—'}
                </dd>
              </div>
            </dl>
            <p className="text-xs text-slate-500">{t('app.settings.billing.checkout_summary.tax_note')}</p>
            <div className="flex flex-wrap justify-end gap-2 pt-2">
              <button type="button" className="btn-secondary" onClick={() => setCheckoutConfirmPlan(null)}>
                {t('common.actions.cancel')}
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={isCheckoutLoading}
                onClick={() => {
                  const plan = checkoutConfirmPlan
                  setCheckoutConfirmPlan(null)
                  if (plan) void startCheckout(plan)
                }}
              >
                {t('app.settings.billing.checkout_summary.proceed')}
              </button>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  )
}
