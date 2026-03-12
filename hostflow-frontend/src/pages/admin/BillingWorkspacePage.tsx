import { useCallback, useEffect, useMemo, useState } from 'react'
import { IconAlertTriangle, IconCheck, IconCreditCard, IconRefresh } from '@tabler/icons-react'
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
  type BillingCheckoutSession,
  type BillingSummary,
  type BillingSubscription,
} from '../../api/billing'

type PlanCode = 'starter' | 'team' | 'pro'
type CheckoutState = 'idle' | 'success' | 'cancel' | 'error' | 'incomplete'

type PlanDef = {
  code: PlanCode
  name: string
  price: string
  seatsLabel: string
  featureLabel: string
}

const DAY_MS = 24 * 60 * 60 * 1000

function getPlanCode(value: string | null | undefined): PlanCode {
  const plan = (value || '').trim().toLowerCase()
  if (plan === 'team' || plan === 'pro') return plan
  return 'starter'
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

  const syncCheckoutState = (data: BillingSubscription) => {
    const normalized = (data.status || '').toLowerCase()
    if (normalized === 'active') setCheckoutState('success')
    else if (normalized === 'canceled') setCheckoutState('cancel')
    else if (normalized === 'past_due') setCheckoutState('error')
    else if (normalized === 'incomplete') setCheckoutState('incomplete')
    else setCheckoutState('idle')
  }

  useEffect(() => {
    let mounted = true
    ;(async () => {
      setIsLoading(true)
      setError(null)
      try {
        const data = await getBillingSummary()
        if (!mounted) return
        setSummary(data)
        setSubscription(data.subscription)
        syncCheckoutState(data.subscription)
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
  }, [])

  const reloadSummary = useCallback(async () => {
    const data = await getBillingSummary()
    setSummary(data)
    setSubscription(data.subscription)
    syncCheckoutState(data.subscription)
  }, [])

  const activePlan = getPlanCode(subscription?.plan_code)
  const isTrial = (subscription?.status || '').trim().toLowerCase() === 'trial'
  const trialDaysLeft = useMemo(() => {
    if (!subscription?.trial_ends_at) return null
    const dt = new Date(subscription.trial_ends_at)
    if (Number.isNaN(dt.getTime())) return null
    return Math.max(0, Math.ceil((dt.getTime() - Date.now()) / DAY_MS))
  }, [subscription?.trial_ends_at])
  const trialTone = useMemo<'normal' | 'warning' | 'critical'>(() => {
    if (trialDaysLeft == null) return 'normal'
    if (trialDaysLeft <= 2) return 'critical'
    if (trialDaysLeft <= 7) return 'warning'
    return 'normal'
  }, [trialDaysLeft])

  const startCheckout = async (plan: PlanCode) => {
    setIsCheckoutLoading(true)
    setError(null)
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
      if (session.provider === 'stripe' && session.checkout_url) {
        window.location.assign(session.checkout_url)
      }
    } catch (err: any) {
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

  const plans = useMemo<PlanDef[]>(
    () => [
      {
        code: 'starter',
        name: 'Starter',
        price: '$29/mo',
        seatsLabel: '1 user',
        featureLabel: 'Core CRM',
      },
      {
        code: 'team',
        name: 'Team',
        price: '$99/mo',
        seatsLabel: 'Up to 5 users',
        featureLabel: 'Team collaboration',
      },
      {
        code: 'pro',
        name: 'Pro',
        price: '$249/mo',
        seatsLabel: '15+ users',
        featureLabel: 'Advanced automations',
      },
    ],
    [],
  )

  const handleChangePlan = async (plan: PlanCode) => {
    setIsMutationLoading(true)
    setError(null)
    try {
      const data = await changeBillingPlan(plan)
      setSummary(data)
      setSubscription(data.subscription)
      syncCheckoutState(data.subscription)
    } catch (err: any) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.settings.billing.change_plan_error', { defaultValue: 'Failed to change plan.' }),
        ),
      )
    } finally {
      setIsMutationLoading(false)
    }
  }

  const handleCancel = async () => {
    setIsMutationLoading(true)
    setError(null)
    try {
      const data = await cancelBillingSubscription(false)
      setSummary(data)
      setSubscription(data.subscription)
      syncCheckoutState(data.subscription)
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
    try {
      const data = await reactivateBillingSubscription()
      setSummary(data)
      setSubscription(data.subscription)
      syncCheckoutState(data.subscription)
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

  const clearCheckoutState = async () => {
    setCheckoutState('idle')
    setLastCheckout(null)
    await reloadSummary()
  }

  return (
    <div className="space-y-4">
      <header className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
          <IconCreditCard size={18} stroke={1.9} />
          {t('app.settings.billing.badge', { defaultValue: 'Billing & Subscription' })}
        </div>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">
          {t('app.settings.billing.title', { defaultValue: 'Manage subscription' })}
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          {t('app.settings.billing.subtitle', {
            defaultValue:
              'Stripe is not connected yet. This screen simulates the checkout flow and validates conversion-critical UX.',
          })}
        </p>
      </header>

      {isTrial && (
        <section
          className={`rounded-xl border p-4 shadow-sm ${
            trialTone === 'critical'
              ? 'border-rose-300 bg-rose-50'
              : trialTone === 'warning'
                ? 'border-amber-300 bg-amber-50'
                : 'border-emerald-300 bg-emerald-50'
          }`}
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <p
                className={`text-xs font-semibold uppercase tracking-wide ${
                  trialTone === 'critical'
                    ? 'text-rose-800'
                    : trialTone === 'warning'
                      ? 'text-amber-800'
                      : 'text-emerald-800'
                }`}
              >
                {t('app.settings.billing.trial.badge', { defaultValue: 'Trial status' })}
              </p>
              <h2
                className={`text-sm font-semibold ${
                  trialTone === 'critical'
                    ? 'text-rose-950'
                    : trialTone === 'warning'
                      ? 'text-amber-950'
                      : 'text-emerald-950'
                }`}
              >
                {trialDaysLeft != null
                  ? t('app.settings.billing.trial.title_with_days', {
                      defaultValue: 'Trial active: {days} day(s) left',
                      values: { days: trialDaysLeft },
                    })
                  : t('app.settings.billing.trial.title', { defaultValue: 'Trial active' })}
              </h2>
              <p
                className={`text-xs ${
                  trialTone === 'critical'
                    ? 'text-rose-900/90'
                    : trialTone === 'warning'
                      ? 'text-amber-900/90'
                      : 'text-emerald-900/90'
                }`}
              >
                {t('app.settings.billing.trial.subtitle', {
                  defaultValue: 'Choose a paid plan before trial ends to keep uninterrupted access.',
                })}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="btn-primary"
                onClick={() => startCheckout(activePlan)}
                disabled={isCheckoutLoading}
              >
                {t('app.settings.billing.trial.cta', { defaultValue: 'Upgrade now' })}
              </button>
              <Link to="/app/overview" className="btn-secondary">
                {t('app.settings.billing.trial.secondary_cta', { defaultValue: 'Continue setup' })}
              </Link>
            </div>
          </div>
          <p
            className={`mt-2 text-xs ${
              trialTone === 'critical'
                ? 'text-rose-900/90'
                : trialTone === 'warning'
                  ? 'text-amber-900/90'
                  : 'text-emerald-900/90'
            }`}
          >
            {t('app.settings.billing.trial.legal_prefix', { defaultValue: 'Legal:' })}{' '}
            <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
              {t('app.settings.billing.trial.legal_terms', { defaultValue: 'Terms' })}
            </a>
            {', '}
            <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
              {t('app.settings.billing.trial.legal_privacy', { defaultValue: 'Privacy' })}
            </a>
            {', '}
            <a href="/legal/cookies.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
              {t('app.settings.billing.trial.legal_cookies', { defaultValue: 'Cookies' })}
            </a>
            .
          </p>
        </section>
      )}

      {error && (
        <ErrorRecoveryBanner
          info={error}
          onRetry={() => void reloadSummary()}
          retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
          secondaryTo="/app/settings/billing"
          secondaryLabel={t('app.settings.billing.badge', { defaultValue: 'Billing & Subscription' })}
        />
      )}

      {isLoading ? (
        <section className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
          {t('common.loading')}
        </section>
      ) : null}

      <section className="grid gap-4 md:grid-cols-3">
        <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Status</h3>
          <p className="mt-1 text-lg font-semibold text-slate-900">{subscription?.status || '-'}</p>
        </article>
        <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Renewal</h3>
          <p className="mt-1 text-lg font-semibold text-slate-900">
            {subscription?.current_period_end ? new Date(subscription.current_period_end).toLocaleDateString() : '-'}
          </p>
        </article>
        <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Plan</h3>
          <p className="mt-1 text-lg font-semibold text-slate-900">{activePlan.toUpperCase()}</p>
        </article>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {plans.map((plan) => {
          const isActive = plan.code === activePlan
          return (
            <article
              key={plan.code}
              className={`rounded-xl border p-5 shadow-sm ${
                isActive ? 'border-green-300 bg-green-50/40' : 'border-slate-200 bg-white'
              }`}
            >
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">{plan.name}</h2>
                {isActive ? (
                  <span className="inline-flex items-center gap-1 rounded-md bg-green-100 px-2.5 py-1 text-xs font-medium text-green-700">
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
                className="mt-4 inline-flex w-full items-center justify-center rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isActive || isCheckoutLoading || isMutationLoading}
                onClick={() => handleChangePlan(plan.code)}
              >
                {isActive
                  ? t('app.settings.billing.current_plan', { defaultValue: 'Current plan' })
                  : t('app.settings.billing.choose_plan', { defaultValue: 'Change to this plan' })}
              </button>
            </article>
          )
        })}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">
          {t('app.settings.billing.usage_title', { defaultValue: 'Usage and limits' })}
        </h3>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            Recruiters: {summary?.usage.recruiter_count ?? 0} / {summary?.license?.max_recruiters ?? 0}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            Supervisors: {summary?.usage.supervisor_count ?? 0} / {summary?.license?.max_supervisors ?? 0}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            Client managers: {summary?.usage.client_manager_count ?? 0} / {summary?.license?.max_client_managers ?? 0}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            Viewers: {summary?.usage.viewer_count ?? 0} / {summary?.license?.max_viewers ?? 0}
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            Storage: {Math.round(summary?.usage.storage_used_gb ?? 0)}GB / {summary?.license?.max_storage_gb ?? 0}GB
          </div>
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            Companies: limit {summary?.license?.max_companies ?? 0}
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">
          {t('app.settings.billing.manage_title', { defaultValue: 'Manage subscription' })}
        </h3>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-md bg-amber-600 px-3 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:cursor-not-allowed disabled:opacity-60"
            onClick={handleCancel}
            disabled={isMutationLoading}
          >
            {t('app.settings.billing.cancel', { defaultValue: 'Cancel at period end' })}
          </button>
          <button
            type="button"
            className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
            onClick={handleReactivate}
            disabled={isMutationLoading}
          >
            {t('app.settings.billing.reactivate', { defaultValue: 'Reactivate' })}
          </button>
          <button
            type="button"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            onClick={() => startCheckout(activePlan)}
            disabled={isCheckoutLoading}
          >
            {t('app.settings.billing.renew', { defaultValue: 'Run checkout flow' })}
          </button>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">
          {t('app.settings.billing.checkout_sim.title', { defaultValue: 'Stripe checkout simulation' })}
        </h3>
        <p className="mt-1 text-sm text-slate-600">
          {t('app.settings.billing.checkout_sim.subtitle', {
            defaultValue: 'Use these controls to test success, cancel, and payment error scenarios.',
          })}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700"
            onClick={() => simulateOutcome('success')}
            disabled={isCheckoutLoading}
          >
            {t('app.settings.billing.checkout_sim.success', { defaultValue: 'Simulate success' })}
          </button>
          <button
            type="button"
            className="rounded-md bg-amber-500 px-3 py-2 text-sm font-medium text-white hover:bg-amber-600"
            onClick={() => simulateOutcome('cancel')}
            disabled={isCheckoutLoading}
          >
            {t('app.settings.billing.checkout_sim.cancel', { defaultValue: 'Simulate cancel' })}
          </button>
          <button
            type="button"
            className="rounded-md bg-rose-600 px-3 py-2 text-sm font-medium text-white hover:bg-rose-700"
            onClick={() => simulateOutcome('error')}
            disabled={isCheckoutLoading}
          >
            {t('app.settings.billing.checkout_sim.error', { defaultValue: 'Simulate card error' })}
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            onClick={clearCheckoutState}
            disabled={isCheckoutLoading}
          >
            <IconRefresh size={15} stroke={1.9} />
            {t('common.reset', { defaultValue: 'Reset' })}
          </button>
          <button
            type="button"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            onClick={openPortal}
            disabled={isPortalLoading}
          >
            {t('app.settings.billing.portal', { defaultValue: 'Open billing portal' })}
          </button>
        </div>

        {checkoutState !== 'idle' && (
          <div
            className={`mt-4 rounded-md border px-4 py-3 text-sm ${
              checkoutState === 'success'
                ? 'border-green-200 bg-green-50 text-green-700'
                : checkoutState === 'cancel'
                  ? 'border-amber-200 bg-amber-50 text-amber-700'
                  : 'border-rose-200 bg-rose-50 text-rose-700'
            }`}
          >
            {checkoutState === 'success' && t('app.settings.billing.status.success', { defaultValue: 'Payment succeeded. Subscription is active.' })}
            {checkoutState === 'cancel' && t('app.settings.billing.status.cancel', { defaultValue: 'Checkout canceled by user. Keep context and offer one-click retry.' })}
            {(checkoutState === 'error' || checkoutState === 'incomplete') && (
              <span className="inline-flex items-center gap-1">
                <IconAlertTriangle size={14} stroke={2} />
                {checkoutState === 'error'
                  ? t('app.settings.billing.status.error', { defaultValue: 'Payment failed. Show clear reason and retry action.' })
                  : t('app.settings.billing.status.incomplete', { defaultValue: 'Checkout created. Complete payment or resolve simulation outcome.' })}
              </span>
            )}
          </div>
        )}

        <ol className="mt-4 list-decimal space-y-1 pl-5 text-sm text-slate-600">
          <li>Select plan and create Stripe Checkout session.</li>
          <li>Redirect to Stripe Checkout and collect payment method.</li>
          <li>Receive `checkout.session.completed` webhook.</li>
          <li>Activate subscription and tenant limits.</li>
          <li>Redirect user to success page with onboarding checklist.</li>
        </ol>
      </section>
    </div>
  )
}
