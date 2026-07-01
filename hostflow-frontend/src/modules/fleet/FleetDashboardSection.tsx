import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { getFleetOverview, getFleetStatus } from '../../api/fleet'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  fleetAssignmentsHrefUtcMonthOverlap,
  fleetAssignmentsHrefUtcSingleDay,
  fleetCalendarHrefUtcMonth,
  fleetCalendarHrefUtcWeek,
} from './fleetQueryParams'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

export default function FleetDashboardSection() {
  const { t } = useI18n()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [apiOk, setApiOk] = useState<boolean | null>(null)
  const [vehiclesN, setVehiclesN] = useState(0)
  const [trailersN, setTrailersN] = useState(0)
  const [driversN, setDriversN] = useState(0)
  const [linesN, setLinesN] = useState(0)
  const [modelsN, setModelsN] = useState(0)
  const [assignmentsN, setAssignmentsN] = useState(0)
  const [assignmentsTodayUtcN, setAssignmentsTodayUtcN] = useState(0)
  const [assignmentsMonthUtcN, setAssignmentsMonthUtcN] = useState(0)
  const [driversWorkforceN, setDriversWorkforceN] = useState(0)
  const [rosterVehiclesN, setRosterVehiclesN] = useState(0)
  const [rosterDriversN, setRosterDriversN] = useState(0)
  const [rosterDriversEffectiveTodayN, setRosterDriversEffectiveTodayN] = useState(0)
  const [vehicleStatuses, setVehicleStatuses] = useState<Map<string, number>>(new Map())
  const [trailerStatuses, setTrailerStatuses] = useState<Map<string, number>>(new Map())
  const [driverStatuses, setDriverStatuses] = useState<Map<string, number>>(new Map())
  const [lineStatuses, setLineStatuses] = useState<Map<string, number>>(new Map())
  const [assignByStatus, setAssignByStatus] = useState<Map<string, number>>(new Map())

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const statusPromise = getFleetStatus().catch(() => ({ ok: false, module: 'fleet' }))
        const [statusRes, overview] = await Promise.all([statusPromise, getFleetOverview()])
        if (cancelled) return
        setApiOk(Boolean(statusRes.ok))
        setVehiclesN(overview.vehicles_total)
        setTrailersN(overview.trailers_total)
        setDriversN(overview.drivers_total)
        setDriversWorkforceN(
          typeof overview.drivers_with_workforce_total === 'number' ? overview.drivers_with_workforce_total : 0,
        )
        setRosterVehiclesN(
          typeof overview.line_roster_vehicles_total === 'number' ? overview.line_roster_vehicles_total : 0,
        )
        setRosterDriversN(
          typeof overview.line_roster_drivers_total === 'number' ? overview.line_roster_drivers_total : 0,
        )
        setRosterDriversEffectiveTodayN(
          typeof overview.line_roster_drivers_effective_today_total === 'number'
            ? overview.line_roster_drivers_effective_today_total
            : 0,
        )
        setLinesN(overview.operating_lines_total)
        setModelsN(overview.work_models_total)
        setAssignmentsN(overview.assignments_total)
        setAssignmentsTodayUtcN(
          typeof overview.assignments_overlapping_today_utc_total === 'number'
            ? overview.assignments_overlapping_today_utc_total
            : 0,
        )
        setAssignmentsMonthUtcN(
          typeof overview.assignments_overlapping_month_utc_total === 'number'
            ? overview.assignments_overlapping_month_utc_total
            : 0,
        )
        setVehicleStatuses(new Map(Object.entries(overview.vehicles_by_status || {})))
        setTrailerStatuses(new Map(Object.entries(overview.trailers_by_status ?? {})))
        setDriverStatuses(new Map(Object.entries(overview.drivers_by_status ?? {})))
        setLineStatuses(new Map(Object.entries(overview.operating_lines_by_status ?? {})))
        setAssignByStatus(new Map(Object.entries(overview.assignments_by_status || {})))
      } catch (err) {
        if (!cancelled) setError(getFriendlyErrorInfo(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const assignKeys = useMemo(() => ['planned', 'active', 'completed', 'cancelled'], [])

  const dashboardQuickLinks = useMemo(
    () =>
      [
        { to: CRM_APP_PATHS.fleetOperatingLinesSeasonality, labelKey: 'app.fleet.nav.line_seasonality' as const },
        { to: fleetCalendarHrefUtcMonth(CRM_APP_PATHS.fleetCalendar), labelKey: 'app.fleet.nav.calendar' as const },
        { to: CRM_APP_PATHS.fleetCalculator, labelKey: 'app.fleet.nav.calculator' as const },
        { to: CRM_APP_PATHS.fleetCounterparties, labelKey: 'app.fleet.nav.counterparties' as const },
        { to: CRM_APP_PATHS.fleetHrBridge, labelKey: 'app.fleet.nav.hr_bridge' as const },
      ] as const,
    [],
  )

  const monitoringLinks = useMemo(
    () =>
      [
        { to: CRM_APP_PATHS.fleetTelematics, labelKey: 'app.fleet.nav.telematics' as const },
        { to: CRM_APP_PATHS.fleetTachograph, labelKey: 'app.fleet.nav.tachograph' as const },
        { to: CRM_APP_PATHS.fleetViolations, labelKey: 'app.fleet.nav.violations' as const },
        { to: CRM_APP_PATHS.fleetReconciliation, labelKey: 'app.fleet.nav.reconciliation' as const },
      ] as const,
    [],
  )

  const financeLinks = useMemo(
    () =>
      [
        { to: CRM_APP_PATHS.fleetPayroll, labelKey: 'app.fleet.nav.payroll' as const },
        { to: CRM_APP_PATHS.fleetReports, labelKey: 'app.fleet.nav.reports' as const },
      ] as const,
    [],
  )

  const statCard = (label: string, value: number, href: string, footer?: ReactNode) => (
    <Link
      to={href}
      className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300 hover:shadow"
    >
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
      {footer}
    </Link>
  )

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-slate-900">{t('app.fleet.dashboard.title', { defaultValue: 'Fleet dashboard' })}</h1>
        <p className="text-slate-600">{t('app.fleet.dashboard.subtitle', { defaultValue: 'Live counts from your tenant fleet data.' })}</p>
      </header>

      {error ? (
        <ErrorRecoveryBanner info={error} onRetry={() => window.location.reload()} />
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
      ) : (
        <>
          {apiOk === false ? (
            <p className="text-sm text-amber-800">{t('app.fleet.dashboard.status_degraded', { defaultValue: 'Fleet API status check failed; counts below may still load.' })}</p>
          ) : apiOk ? (
            <p className="text-sm text-emerald-700">{t('app.fleet.api_ok')}</p>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {statCard(t('app.fleet.nav.vehicles'), vehiclesN, CRM_APP_PATHS.fleetVehicles)}
            {statCard(t('app.fleet.nav.trailers'), trailersN, CRM_APP_PATHS.fleetTrailers)}
            {statCard(
              t('app.fleet.nav.drivers'),
              driversN,
              CRM_APP_PATHS.fleetDrivers,
              <span className="mt-2 block text-xs leading-snug text-slate-500">
                {t('app.fleet.dashboard.drivers_workforce_linked', {
                  values: { n: driversWorkforceN },
                  defaultValue: '{n} linked to workforce',
                })}
              </span>,
            )}
            {statCard(t('app.fleet.nav.operating_lines'), linesN, CRM_APP_PATHS.fleetOperatingLines)}
            {statCard(t('app.fleet.dashboard.work_models', { defaultValue: 'Work models' }), modelsN, CRM_APP_PATHS.fleetRotation)}
            {statCard(t('app.fleet.nav.assignments'), assignmentsN, CRM_APP_PATHS.fleetAssignments)}
          </div>

          <section className="rounded-lg border border-dashed border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('app.fleet.dashboard.quick_links', { defaultValue: 'Quick links' })}
            </h2>
            <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-2 text-sm">
              {dashboardQuickLinks.map(({ to, labelKey }) => (
                <li key={to}>
                  <Link to={to} className="font-medium text-blue-700 hover:underline">
                    {t(labelKey)}
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-lg border border-slate-200 bg-slate-50/80 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <h2 className="text-sm font-semibold text-slate-900">
                {t('app.fleet.dashboard.assignments_by_status', { defaultValue: 'Assignments by status' })}
              </h2>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-slate-600">
                <span className="tabular-nums">
                  <span className="font-medium text-slate-700">
                    {t('app.fleet.dashboard.assignments_today_utc', { defaultValue: 'Active today (UTC)' })}:
                  </span>{' '}
                  <span className="font-semibold text-slate-900">{assignmentsTodayUtcN}</span>
                  <span className="ml-2 inline-flex flex-wrap gap-x-2 gap-y-0.5">
                    <Link
                      to={fleetAssignmentsHrefUtcSingleDay(CRM_APP_PATHS.fleetAssignments)}
                      className="font-medium text-blue-700 hover:underline"
                    >
                      {t('app.fleet.dashboard.drill_assignments_today_utc', { defaultValue: 'List' })}
                    </Link>
                    <Link
                      to={fleetCalendarHrefUtcWeek(CRM_APP_PATHS.fleetCalendar)}
                      className="font-medium text-blue-700 hover:underline"
                    >
                      {t('app.fleet.dashboard.drill_calendar_week_utc', { defaultValue: 'Week' })}
                    </Link>
                  </span>
                </span>
                <span className="tabular-nums">
                  <span className="font-medium text-slate-700">
                    {t('app.fleet.dashboard.assignments_month_utc', { defaultValue: 'This month (UTC)' })}:
                  </span>{' '}
                  <span className="font-semibold text-slate-900">{assignmentsMonthUtcN}</span>
                  <span className="ml-2 inline-flex flex-wrap gap-x-2 gap-y-0.5">
                    <Link
                      to={fleetAssignmentsHrefUtcMonthOverlap(CRM_APP_PATHS.fleetAssignments)}
                      className="font-medium text-blue-700 hover:underline"
                    >
                      {t('app.fleet.dashboard.drill_assignments_month_utc', { defaultValue: 'List' })}
                    </Link>
                    <Link
                      to={fleetCalendarHrefUtcMonth(CRM_APP_PATHS.fleetCalendar)}
                      className="font-medium text-blue-700 hover:underline"
                    >
                      {t('app.fleet.dashboard.drill_calendar_month_utc', { defaultValue: 'Month' })}
                    </Link>
                  </span>
                </span>
              </div>
            </div>
            <ul className="mt-2 flex flex-wrap gap-2 text-sm">
              {assignKeys.map((key) => (
                <li key={key} className="rounded-md bg-white px-2 py-1 shadow-sm ring-1 ring-slate-100">
                  <span className="text-slate-600">{t(`app.fleet.assignments.status_${key}`, { defaultValue: key })}:</span>{' '}
                  <span className="font-semibold tabular-nums text-slate-900">{assignByStatus.get(key) ?? 0}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-lg border border-slate-200 bg-slate-50/80 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <h2 className="text-sm font-semibold text-slate-900">
                  {t('app.fleet.dashboard.roster_title', { defaultValue: 'Line roster' })}
                </h2>
                <p className="text-xs text-slate-500">
                  {t('app.fleet.dashboard.roster_subtitle', {
                    defaultValue:
                      'Rows linking vehicles and drivers to operating lines (same asset may appear on multiple lines).',
                  })}
                </p>
              </div>
              <Link
                to={CRM_APP_PATHS.fleetRotation}
                className="shrink-0 text-sm font-medium text-blue-700 hover:underline"
              >
                {t('app.fleet.dashboard.roster_manage', { defaultValue: 'Manage roster →' })}
              </Link>
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {t('app.fleet.dashboard.roster_vehicles', { defaultValue: 'Vehicles on lines' })}
                </p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{rosterVehiclesN}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {t('app.fleet.dashboard.roster_drivers', { defaultValue: 'Drivers on lines' })}
                </p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{rosterDriversN}</p>
                <p className="mt-2 text-xs leading-snug text-slate-500">
                  {t('app.fleet.dashboard.roster_drivers_effective_today', {
                    values: { n: rosterDriversEffectiveTodayN },
                    defaultValue: 'Effective today (UTC): {n}',
                  })}
                </p>
              </div>
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('app.fleet.dashboard.monitoring_title', { defaultValue: 'Monitoring & compliance' })}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              {t('app.fleet.dashboard.monitoring_subtitle', {
                defaultValue: 'Alerts and cross-checks will land here once integrations are connected.',
              })}
            </p>
            <ul className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {monitoringLinks.map(({ to, labelKey }) => (
                <li key={to}>
                  <Link
                    to={to}
                    className="flex h-full flex-col gap-1 rounded-lg border border-slate-200 bg-slate-50/60 p-3 text-sm transition hover:border-slate-300 hover:bg-white"
                  >
                    <span className="font-medium text-slate-900">{t(labelKey)}</span>
                    <span className="text-xs font-medium uppercase tracking-wide text-slate-400">
                      {t('app.fleet.dashboard.monitoring_planned', { defaultValue: 'Planned' })}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('app.fleet.dashboard.finance_title', { defaultValue: 'Finance & reporting' })}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              {t('app.fleet.dashboard.finance_subtitle', {
                defaultValue: 'Payroll accruals and regulated exports will surface here as rules and integrations land.',
              })}
            </p>
            <ul className="mt-3 grid gap-3 sm:grid-cols-2">
              {financeLinks.map(({ to, labelKey }) => (
                <li key={to}>
                  <Link
                    to={to}
                    className="flex h-full flex-col gap-1 rounded-lg border border-slate-200 bg-slate-50/60 p-3 text-sm transition hover:border-slate-300 hover:bg-white"
                  >
                    <span className="font-medium text-slate-900">{t(labelKey)}</span>
                    <span className="text-xs font-medium uppercase tracking-wide text-slate-400">
                      {t('app.fleet.dashboard.monitoring_planned', { defaultValue: 'Planned' })}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          {vehicleStatuses.size > 0 ? (
            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900">{t('app.fleet.dashboard.vehicles_by_status', { defaultValue: 'Vehicles by status' })}</h2>
              <ul className="mt-2 flex flex-wrap gap-2 text-sm">
                {[...vehicleStatuses.entries()]
                  .sort((a, b) => a[0].localeCompare(b[0]))
                  .map(([st, n]) => (
                    <li key={st} className="rounded-md bg-slate-50 px-2 py-1 ring-1 ring-slate-100">
                      <span className="text-slate-600">{st}:</span> <span className="font-semibold tabular-nums">{n}</span>
                    </li>
                  ))}
              </ul>
            </section>
          ) : null}

          {trailerStatuses.size > 0 ? (
            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900">
                {t('app.fleet.dashboard.trailers_by_status', { defaultValue: 'Trailers by status' })}
              </h2>
              <ul className="mt-2 flex flex-wrap gap-2 text-sm">
                {[...trailerStatuses.entries()]
                  .sort((a, b) => a[0].localeCompare(b[0]))
                  .map(([st, n]) => (
                    <li key={st} className="rounded-md bg-slate-50 px-2 py-1 ring-1 ring-slate-100">
                      <span className="text-slate-600">{st}:</span> <span className="font-semibold tabular-nums">{n}</span>
                    </li>
                  ))}
              </ul>
            </section>
          ) : null}

          {driverStatuses.size > 0 ? (
            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900">
                {t('app.fleet.dashboard.drivers_by_status', { defaultValue: 'Drivers by status' })}
              </h2>
              <ul className="mt-2 flex flex-wrap gap-2 text-sm">
                {[...driverStatuses.entries()]
                  .sort((a, b) => a[0].localeCompare(b[0]))
                  .map(([st, n]) => (
                    <li key={st} className="rounded-md bg-slate-50 px-2 py-1 ring-1 ring-slate-100">
                      <span className="text-slate-600">{st}:</span> <span className="font-semibold tabular-nums">{n}</span>
                    </li>
                  ))}
              </ul>
            </section>
          ) : null}

          {lineStatuses.size > 0 ? (
            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900">
                {t('app.fleet.dashboard.operating_lines_by_status', { defaultValue: 'Operating lines by status' })}
              </h2>
              <ul className="mt-2 flex flex-wrap gap-2 text-sm">
                {[...lineStatuses.entries()]
                  .sort((a, b) => a[0].localeCompare(b[0]))
                  .map(([st, n]) => (
                    <li key={st} className="rounded-md bg-slate-50 px-2 py-1 ring-1 ring-slate-100">
                      <span className="text-slate-600">{st}:</span> <span className="font-semibold tabular-nums">{n}</span>
                    </li>
                  ))}
              </ul>
            </section>
          ) : null}
        </>
      )}
    </div>
  )
}
