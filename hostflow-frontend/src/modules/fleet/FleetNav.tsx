import { NavLink } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'

const LINKS: { to: string; labelKey: string; end?: boolean }[] = [
  { to: CRM_APP_PATHS.fleet, labelKey: 'app.fleet.nav.dashboard', end: true },
  { to: CRM_APP_PATHS.fleetVehicles, labelKey: 'app.fleet.nav.vehicles' },
  { to: CRM_APP_PATHS.fleetTrailers, labelKey: 'app.fleet.nav.trailers' },
  { to: CRM_APP_PATHS.fleetDrivers, labelKey: 'app.fleet.nav.drivers' },
  { to: CRM_APP_PATHS.fleetCounterparties, labelKey: 'app.fleet.nav.counterparties' },
  { to: CRM_APP_PATHS.fleetAssignments, labelKey: 'app.fleet.nav.assignments' },
  { to: CRM_APP_PATHS.fleetOperatingLines, labelKey: 'app.fleet.nav.operating_lines', end: true },
  { to: CRM_APP_PATHS.fleetOperatingLinesSeasonality, labelKey: 'app.fleet.nav.line_seasonality' },
  { to: CRM_APP_PATHS.fleetHrBridge, labelKey: 'app.fleet.nav.hr_bridge' },
  { to: CRM_APP_PATHS.fleetRotation, labelKey: 'app.fleet.nav.rotation' },
  { to: CRM_APP_PATHS.fleetCalendar, labelKey: 'app.fleet.nav.calendar' },
  { to: CRM_APP_PATHS.fleetCalculator, labelKey: 'app.fleet.nav.calculator' },
  { to: CRM_APP_PATHS.fleetTelematics, labelKey: 'app.fleet.nav.telematics' },
  { to: CRM_APP_PATHS.fleetTachograph, labelKey: 'app.fleet.nav.tachograph' },
  { to: CRM_APP_PATHS.fleetViolations, labelKey: 'app.fleet.nav.violations' },
  { to: CRM_APP_PATHS.fleetReconciliation, labelKey: 'app.fleet.nav.reconciliation' },
  { to: CRM_APP_PATHS.fleetPayroll, labelKey: 'app.fleet.nav.payroll' },
  { to: CRM_APP_PATHS.fleetReports, labelKey: 'app.fleet.nav.reports' },
  { to: CRM_APP_PATHS.fleetSettings, labelKey: 'app.fleet.nav.settings' },
]

export default function FleetNav() {
  const { t } = useI18n()

  return (
    <nav className="flex flex-wrap gap-x-3 gap-y-2 border-b border-slate-200 pb-3 text-sm" aria-label={t('app.fleet.nav.aria', { defaultValue: 'Fleet sections' })}>
      {LINKS.map(({ to, labelKey, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            [
              'rounded px-2 py-1 font-medium transition-colors',
              isActive ? 'bg-slate-100 text-slate-900' : 'text-blue-700 hover:bg-slate-50 hover:underline',
            ].join(' ')
          }
        >
          {t(labelKey)}
        </NavLink>
      ))}
    </nav>
  )
}
