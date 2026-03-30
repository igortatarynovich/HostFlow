import { useCallback, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { ACTIVATION_PATHS } from '../../app/activationRoutes'
import { CRM_APP_DRILLDOWN_HREFS } from '../../app/crmAppPaths'
import type { OpsCounters } from '../../api/analytics'
import { bulkAutoProcessLeadQueue } from '../../api/client'
import { useI18n } from '../../i18n'
import { useTeamTierFeatures } from '../../hooks/useTeamTierFeatures'
import { usePermissions } from '../../hooks/usePermissions'
import { useToast } from '../Toast'

type DashboardLeadAutoFixCardProps = {
  opsCounters: OpsCounters | null
  onRefreshOps: () => void | Promise<void>
}

export function DashboardLeadAutoFixCard({ opsCounters, onRefreshOps }: DashboardLeadAutoFixCardProps) {
  const { t } = useI18n()
  const { notify } = useToast()
  const { can } = usePermissions()
  const { allowsTeamFeatures, planLoading } = useTeamTierFeatures()
  const [busy, setBusy] = useState(false)

  const pendingMeta = useMemo(() => {
    const nr = Number(opsCounters?.leads_needs_routing ?? 0)
    const fd = Number(opsCounters?.leads_failed ?? 0)
    return Math.max(0, nr) + Math.max(0, fd)
  }, [opsCounters?.leads_failed, opsCounters?.leads_needs_routing])

  const runAutoFix = useCallback(async () => {
    if (!allowsTeamFeatures || busy) return
    setBusy(true)
    try {
      const max_items = Math.min(25, Math.max(1, pendingMeta))
      const res = await bulkAutoProcessLeadQueue({ max_items })
      await onRefreshOps()
      notify({
        title: t('app.dashboard.lead_autofix.done_title'),
        description: t('app.dashboard.lead_autofix.done_desc', {
          values: {
            ok: res.succeeded,
            fail: res.failed,
            attempted: res.attempted,
          },
        }),
        variant: res.failed > 0 && res.succeeded === 0 ? 'error' : res.failed > 0 ? 'warning' : 'success',
      })
    } catch (err: unknown) {
      const ax = err as { response?: { status?: number; data?: { detail?: unknown } } }
      const st = ax?.response?.status
      const detail = ax?.response?.data?.detail
      if (st === 403 && detail && typeof detail === 'object' && !Array.isArray(detail)) {
        const code = (detail as { code?: string }).code
        if (code === 'plan_requires_team') {
          notify({
            title: t('app.dashboard.lead_autofix.plan_blocked_title'),
            description: t('app.dashboard.lead_autofix.plan_blocked_desc'),
            variant: 'warning',
          })
          return
        }
      }
      notify({
        title: t('app.dashboard.lead_autofix.error_title'),
        description: String((detail as string) || (err as Error)?.message || 'Error'),
        variant: 'error',
      })
    } finally {
      setBusy(false)
    }
  }, [allowsTeamFeatures, busy, notify, onRefreshOps, pendingMeta, t])

  if (!can('leads.view')) return null
  if (pendingMeta <= 0) return null

  return (
    <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50/90 px-4 py-3 shadow-sm">
      <div className="text-sm font-semibold text-amber-950">
        {t('app.dashboard.lead_autofix.title')}
      </div>
      <p className="mt-1 text-xs text-amber-900/90">
        {t('app.dashboard.lead_autofix.subtitle', {
          values: { count: pendingMeta },
        })}
      </p>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {allowsTeamFeatures && !planLoading ? (
          <button
            type="button"
            className="btn-primary btn-sm disabled:cursor-not-allowed disabled:opacity-60"
            disabled={busy}
            onClick={() => void runAutoFix()}
          >
            {busy ? t('common.loading') : t('app.dashboard.lead_autofix.cta')}
          </button>
        ) : (
          <Link
            className="btn-primary btn-sm inline-flex items-center"
            to={`${ACTIVATION_PATHS.billing}?focus=plan`}
          >
            {t('app.dashboard.lead_autofix.cta_upgrade')}
          </Link>
        )}
        <Link className="btn-secondary btn-sm" to={CRM_APP_DRILLDOWN_HREFS.leadsNeedsRouting}>
          {t('app.dashboard.lead_autofix.open_list')}
        </Link>
      </div>
      {!allowsTeamFeatures && !planLoading ? (
        <p className="mt-2 text-[11px] text-amber-800/90">
          {t('app.dashboard.lead_autofix.plan_hint')}
        </p>
      ) : null}
    </div>
  )
}
