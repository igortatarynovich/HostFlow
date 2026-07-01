import { Link } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import { useI18n } from '../i18n'
import { ACTIVATION_PATHS } from '../app/activationRoutes'

type Props = {
  visible: boolean
  validUntil: string | null
  canOpenBilling: boolean
  onSetupClick?: () => void
}

const DAY_MS = 24 * 60 * 60 * 1000

export function TrialStatusBanner({ visible, validUntil, canOpenBilling, onSetupClick }: Props) {
  const { t } = useI18n()
  const endDate = validUntil ? new Date(validUntil) : null
  const hasValidDate = Boolean(endDate && !Number.isNaN(endDate.getTime()))
  const [nowTs, setNowTs] = useState<number>(0)
  useEffect(() => {
    // Keep render pure; set "now" from effect.
    setNowTs(Date.now())
  }, [validUntil, visible])

  const daysLeft = useMemo(() => {
    if (!hasValidDate || !nowTs) return null
    return Math.max(0, Math.ceil((endDate!.getTime() - nowTs) / DAY_MS))
  }, [endDate, hasValidDate, nowTs])
  const tone: 'normal' | 'warning' | 'critical' = daysLeft == null ? 'normal' : daysLeft <= 2 ? 'critical' : daysLeft <= 7 ? 'warning' : 'normal'

  if (!visible) return null

  const wrapperClass =
    tone === 'critical'
      ? 'border-rose-300 bg-rose-50'
      : tone === 'warning'
        ? 'border-amber-300 bg-amber-50'
        : 'border-emerald-300 bg-emerald-50'
  const textClass =
    tone === 'critical'
      ? 'text-rose-950'
      : tone === 'warning'
        ? 'text-amber-950'
        : 'text-emerald-950'
  const subtextClass =
    tone === 'critical'
      ? 'text-rose-900/90'
      : tone === 'warning'
        ? 'text-amber-900/90'
        : 'text-emerald-900/90'

  return (
    <div className={`border-b px-4 py-2 ${wrapperClass}`} role="status" aria-live="polite">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className={`text-[11px] font-semibold uppercase tracking-wide ${subtextClass}`}>
            {t('app.trial_banner.badge', { defaultValue: 'Trial status' })}
          </p>
          <p className={`text-sm font-semibold ${textClass}`}>
            {daysLeft != null
              ? t('app.trial_banner.title_with_days', {
                  defaultValue: 'Trial active: {days} day(s) left',
                  values: { days: daysLeft },
                })
              : t('app.trial_banner.title', { defaultValue: 'Trial active' })}
          </p>
          <p className={`text-xs ${subtextClass}`}>
            {t('app.trial_banner.subtitle', {
              defaultValue: 'Review billing and legal terms now to avoid interruption when trial ends.',
            })}
          </p>
          {!canOpenBilling && (
            <p className={`text-xs ${subtextClass}`}>
              {t('app.trial_banner.billing_admin_hint', {
                defaultValue: 'Billing is available for administrators.',
              })}
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {canOpenBilling && (
            <Link to={ACTIVATION_PATHS.billing} className="btn-primary btn-sm">
              {t('app.trial_banner.cta_billing', { defaultValue: 'Open billing' })}
            </Link>
          )}
          <button type="button" className="btn-secondary btn-sm" onClick={onSetupClick}>
            {t('app.trial_banner.cta_setup', { defaultValue: 'Continue setup' })}
          </button>
        </div>
      </div>
      <p className={`mx-auto mt-1 max-w-7xl text-xs ${subtextClass}`}>
        {t('app.trial_banner.legal_prefix', { defaultValue: 'Legal:' })}{' '}
        <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
          {t('app.trial_banner.legal_terms', { defaultValue: 'Terms' })}
        </a>
        {', '}
        <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
          {t('app.trial_banner.legal_privacy', { defaultValue: 'Privacy' })}
        </a>
        {', '}
        <a href="/legal/cookies.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
          {t('app.trial_banner.legal_cookies', { defaultValue: 'Cookies' })}
        </a>
        .
      </p>
    </div>
  )
}
