import { Link } from 'react-router-dom'
import { IconAlertTriangle } from '@tabler/icons-react'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import type { QuotaWarningKind } from '../../hooks/useBillingQuotaWarnings'

export type QuotaNearLimitBannerProps = {
  kind: QuotaWarningKind
  percentUsed: number
  className?: string
}

export function QuotaNearLimitBanner({ kind, percentUsed, className }: QuotaNearLimitBannerProps) {
  const { t } = useI18n()
  const messageKey =
    kind === 'leads_monthly'
      ? 'app.billing.quota_warning.leads'
      : kind === 'candidates_active'
        ? 'app.billing.quota_warning.candidates'
        : 'app.billing.quota_warning.storage'

  return (
    <div
      className={`flex flex-wrap items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950 ${className ?? ''}`}
      role="status"
    >
      <IconAlertTriangle size={18} className="shrink-0 text-amber-600" aria-hidden />
      <span className="min-w-0 flex-1">
        {t(messageKey, { values: { percent: percentUsed } })}
      </span>
      <Link
        to={CRM_APP_PATHS.settingsBilling}
        className="shrink-0 font-medium text-brand-800 underline decoration-brand-300 underline-offset-2 hover:text-brand-900"
      >
        {t('app.billing.quota_warning.cta_addon')}
      </Link>
    </div>
  )
}
