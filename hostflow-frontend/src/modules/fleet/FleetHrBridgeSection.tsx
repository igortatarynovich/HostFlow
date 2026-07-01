import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listFleetDrivers } from '../../api/fleet'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

export default function FleetHrBridgeSection() {
  const { t } = useI18n()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [driversTotal, setDriversTotal] = useState(0)
  const [linkedTotal, setLinkedTotal] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    listFleetDrivers()
      .then((res) => {
        if (cancelled) return
        const items = res.items ?? []
        setDriversTotal(items.length)
        setLinkedTotal(items.filter((d) => Boolean(d.workforce_employee_id?.trim())).length)
      })
      .catch((err) => {
        if (!cancelled) {
          setError(getFriendlyErrorInfo(err))
          setDriversTotal(0)
          setLinkedTotal(0)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const unlinked = useMemo(() => Math.max(driversTotal - linkedTotal, 0), [driversTotal, linkedTotal])

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-slate-900">{t('app.fleet.hr_bridge.title')}</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-slate-600">{t('app.fleet.hr_bridge.body')}</p>
        <div className="flex flex-wrap gap-3 pt-1">
          <Link
            to={CRM_APP_PATHS.hrEmployees}
            className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-blue-700"
          >
            {t('app.fleet.hr_bridge.open_hr')}
          </Link>
          <Link
            to={CRM_APP_PATHS.fleetDrivers}
            className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 shadow-sm transition hover:bg-slate-50"
          >
            {t('app.fleet.hr_bridge.open_drivers', { defaultValue: 'Fleet drivers' })}
          </Link>
        </div>
      </header>

      {error ? (
        <ErrorRecoveryBanner info={error} onRetry={() => window.location.reload()} />
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('app.fleet.hr_bridge.stat_drivers', { defaultValue: 'Fleet drivers' })}
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{driversTotal}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('app.fleet.hr_bridge.stat_linked', { defaultValue: 'Linked to workforce employee' })}
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-emerald-800">{linkedTotal}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('app.fleet.hr_bridge.stat_unlinked', { defaultValue: 'Not linked yet' })}
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{unlinked}</p>
          </div>
        </div>
      )}

      <p className="max-w-3xl text-xs text-slate-500">
        {t('app.fleet.hr_bridge.hint_edit_on_driver', {
          defaultValue: 'Set the workforce employee field on each driver card in Fleet drivers.',
        })}
      </p>
    </div>
  )
}
