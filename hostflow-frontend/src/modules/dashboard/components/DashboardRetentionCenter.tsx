import { Link } from 'react-router-dom'
import type { TranslateFn } from '../../../i18n'
import { CRM_APP_PATHS } from '../../../app/crmAppPaths'
import type { BillingGate } from '../../../api/billing'
import type { TrialRetentionReport } from '../../../api/analytics'
import type {
  RetentionNudge,
  RetentionReportRow,
  TrialCenterClassMap,
} from '../hooks/useDashboardRetention'
import type { TrialRetentionDay } from '../internal'

type TrialTone = 'normal' | 'warning' | 'critical'

export interface DashboardRetentionCenterProps {
  t: TranslateFn
  canManageBilling: boolean
  isTrialTenant: boolean
  billingGate: BillingGate | null
  retentionNudge: RetentionNudge | null
  dismissRetentionNudge: () => void
  trackRetentionEvent: (
    action: 'cta_click' | 'dismiss',
    payload: { day: TrialRetentionDay; stepKey: string; href: string; activationDone: boolean },
  ) => void
  showTrialPanel: boolean
  trialCenterClasses: TrialCenterClassMap
  trialDaysLeft: number | null
  trialTone: TrialTone
  retentionReport: TrialRetentionReport | null
  retentionReportLoading: boolean
  retentionReportRows: RetentionReportRow[]
}

export function DashboardRetentionCenter({
  t,
  canManageBilling,
  isTrialTenant,
  billingGate,
  retentionNudge,
  dismissRetentionNudge,
  trackRetentionEvent,
  showTrialPanel,
  trialCenterClasses,
  trialDaysLeft,
  trialTone,
  retentionReport,
  retentionReportLoading,
  retentionReportRows,
}: DashboardRetentionCenterProps) {
  return (
    <>
      {retentionNudge && (
        <div className="rounded-xl border border-brand-200 bg-brand-50/60 p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-800">
                {t('app.dashboard.retention.badge')}
              </p>
              <h2 className="text-sm font-semibold text-brand-950">
                {retentionNudge.activationDone
                  ? t('app.dashboard.retention.post_activation.title')
                  : t(`app.dashboard.retention.${retentionNudge.dayKey}.title`)}
              </h2>
              <p className="text-xs text-brand-900/90">
                {retentionNudge.activationDone
                  ? t('app.dashboard.retention.post_activation.subtitle')
                  : t(`app.dashboard.retention.${retentionNudge.dayKey}.subtitle`)}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Link
                to={retentionNudge.href}
                className="btn-secondary btn-sm"
                onClick={() =>
                  trackRetentionEvent('cta_click', {
                    day: retentionNudge.day,
                    stepKey: retentionNudge.stepKey,
                    href: retentionNudge.href,
                    activationDone: retentionNudge.activationDone,
                  })
                }
              >
                {retentionNudge.activationDone
                  ? t('app.dashboard.retention.cta_billing')
                  : (() => {
                      const full = `app.dashboard.retention.cta_step.${retentionNudge.stepKey}`
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- dynamic i18n key with runtime fallback below
                      const out = t(full as any)
                      return out === full ? t('app.dashboard.retention.cta_step.fallback') : out
                    })()}
              </Link>
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => {
                  trackRetentionEvent('dismiss', {
                    day: retentionNudge.day,
                    stepKey: retentionNudge.stepKey,
                    href: retentionNudge.href,
                    activationDone: retentionNudge.activationDone,
                  })
                  dismissRetentionNudge()
                }}
              >
                {t('app.dashboard.retention.dismiss')}
              </button>
            </div>
          </div>
        </div>
      )}
      {billingGate?.side_effects_blocked && canManageBilling && (
        <div className="rounded-xl border border-rose-400 bg-rose-50 p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-wide text-rose-900">
                {t('app.dashboard.billing_gate.badge')}
              </p>
              <h2 className="text-sm font-semibold text-rose-950">
                {t('app.dashboard.billing_gate.blocked_title')}
              </h2>
              <p className="text-xs text-rose-900/90">
                {billingGate.block_reason === 'past_due'
                  ? t('app.dashboard.billing_gate.blocked_subtitle_past_due')
                  : t('app.dashboard.billing_gate.blocked_subtitle_trial_expired')}
              </p>
            </div>
            <Link to={CRM_APP_PATHS.settingsBilling} className="btn-secondary">
              {t('app.dashboard.billing_gate.cta')}
            </Link>
          </div>
        </div>
      )}
      {showTrialPanel && (
        <div className={trialCenterClasses.wrapper}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <p className={trialCenterClasses.badge}>
                {t('app.dashboard.trial_center.badge')}
              </p>
              <h2 className={trialCenterClasses.title}>
                {billingGate?.trial_grace_active
                  ? t('app.dashboard.trial_center.grace_title')
                  : trialDaysLeft != null
                    ? t('app.dashboard.trial_center.title_with_days', { values: { days: trialDaysLeft } })
                    : t('app.dashboard.trial_center.title')}
              </h2>
              <p className={trialCenterClasses.subtitle}>
                {billingGate?.trial_grace_active
                  ? t('app.dashboard.trial_center.grace_subtitle', {
                      values: {
                        hours:
                          billingGate.side_effect_grace_hours_remaining != null
                            ? Math.max(0, Math.ceil(billingGate.side_effect_grace_hours_remaining))
                            : 0,
                      },
                    })
                  : t('app.dashboard.trial_center.subtitle')}
              </p>
              {trialTone === 'critical' && (
                <span className={trialCenterClasses.urgency}>
                  {t('app.dashboard.trial_center.urgency_critical')}
                </span>
              )}
              {trialTone === 'warning' && (
                <span className={trialCenterClasses.urgency}>
                  {t('app.dashboard.trial_center.urgency_warning')}
                </span>
              )}
            </div>
            {canManageBilling && (
              <Link to={CRM_APP_PATHS.settingsBilling} className="btn-secondary">
                {t('app.dashboard.trial_center.open_billing')}
              </Link>
            )}
          </div>
          <p className={trialCenterClasses.legal}>
            {t('app.dashboard.trial_center.legal_prefix')}{' '}
            <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
              {t('app.dashboard.trial_center.legal_terms')}
            </a>
            {', '}
            <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
              {t('app.dashboard.trial_center.legal_privacy')}
            </a>
            {', '}
            <a href="/legal/cookies.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
              {t('app.dashboard.trial_center.legal_cookies')}
            </a>
            .
          </p>
          {canManageBilling && isTrialTenant && (
            <div className="mt-3 rounded-lg border border-slate-200 bg-white/80 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-700">
                  {t('app.dashboard.trial_center.retention.title')}
                </p>
                {retentionReportLoading && (
                  <span className="text-[11px] text-slate-500">
                    {t('app.dashboard.trial_center.retention.loading')}
                  </span>
                )}
              </div>
              <div className="overflow-x-auto">
                <table className="table table-sm">
                  <thead>
                    <tr>
                      <th>{t('app.dashboard.trial_center.retention.columns.day')}</th>
                      <th>{t('app.dashboard.trial_center.retention.columns.impression')}</th>
                      <th>{t('app.dashboard.trial_center.retention.columns.click')}</th>
                      <th>{t('app.dashboard.trial_center.retention.columns.dismiss')}</th>
                      <th>{t('app.dashboard.trial_center.retention.columns.ctr')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {retentionReportRows.map((row) => (
                      <tr key={row.key}>
                        <td>{row.label}</td>
                        <td>{row.impression}</td>
                        <td>{row.ctaClick}</td>
                        <td>{row.dismiss}</td>
                        <td>{row.ctr.toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-xs text-slate-600">
                {t('app.dashboard.trial_center.retention.summary', {
                  values: {
                    impression: retentionReport?.totals?.impression ?? 0,
                    click: retentionReport?.totals?.cta_click ?? 0,
                    dismiss: retentionReport?.totals?.dismiss ?? 0,
                    ctr: Number(retentionReport?.totals?.ctr_percent ?? 0).toFixed(2),
                  },
                })}
              </p>
            </div>
          )}
        </div>
      )}
    </>
  )
}
