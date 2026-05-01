import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { getFleetStatus } from '../../api/fleet'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import FleetOperatingLinesSection from '../../modules/fleet/FleetOperatingLinesSection'
import FleetParkSection from '../../modules/fleet/FleetParkSection'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

function FleetHome() {
  const { t } = useI18n()
  const [statusOk, setStatusOk] = useState<boolean | null>(null)
  const [statusError, setStatusError] = useState<FriendlyErrorInfo | null>(null)

  useEffect(() => {
    let cancelled = false
    getFleetStatus()
      .then((res) => {
        if (!cancelled) setStatusOk(Boolean(res.ok))
      })
      .catch((err) => {
        if (!cancelled) setStatusError(getFriendlyErrorInfo(err))
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="mx-auto max-w-5xl space-y-8 p-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-slate-900">{t('app.fleet.title')}</h1>
        <p className="text-slate-600">{t('app.fleet.subtitle')}</p>
      </header>

      {statusError ? (
        <ErrorRecoveryBanner
          primary={statusError.title}
          secondary={friendlyErrorBannerSecondary(statusError)}
          onRetry={() => window.location.reload()}
        />
      ) : statusOk === null ? (
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
      ) : (
        <p className="text-sm text-emerald-700">{t('app.fleet.api_ok')}</p>
      )}

      <nav className="flex flex-wrap gap-3 text-sm">
        <Link className="font-medium text-blue-700 underline-offset-4 hover:underline" to={CRM_APP_PATHS.fleetOperatingLines}>
          {t('app.fleet.nav.operating_lines')}
        </Link>
        <Link className="font-medium text-blue-700 underline-offset-4 hover:underline" to={CRM_APP_PATHS.fleetVehicles}>
          {t('app.fleet.nav.vehicles')}
        </Link>
        <Link className="font-medium text-blue-700 underline-offset-4 hover:underline" to={CRM_APP_PATHS.fleetTrailers}>
          {t('app.fleet.nav.trailers')}
        </Link>
        <Link className="font-medium text-blue-700 underline-offset-4 hover:underline" to={CRM_APP_PATHS.fleetDrivers}>
          {t('app.fleet.nav.drivers')}
        </Link>
      </nav>

      <div className="grid gap-8 lg:grid-cols-2">
        <FleetParkSection kind="vehicles" preview />
        <FleetParkSection kind="trailers" preview />
        <FleetParkSection kind="drivers" preview />
        <FleetOperatingLinesSection preview />
      </div>
    </div>
  )
}

export default function FleetModulePage() {
  const location = useLocation()
  const path = location.pathname

  if (path.startsWith(CRM_APP_PATHS.fleetOperatingLines)) {
    return (
      <div className="mx-auto max-w-5xl space-y-8 p-6">
        <FleetOperatingLinesSection />
      </div>
    )
  }
  if (path.startsWith(CRM_APP_PATHS.fleetVehicles)) {
    return (
      <div className="mx-auto max-w-5xl space-y-8 p-6">
        <FleetParkSection kind="vehicles" />
      </div>
    )
  }
  if (path.startsWith(CRM_APP_PATHS.fleetTrailers)) {
    return (
      <div className="mx-auto max-w-5xl space-y-8 p-6">
        <FleetParkSection kind="trailers" />
      </div>
    )
  }
  if (path.startsWith(CRM_APP_PATHS.fleetDrivers)) {
    return (
      <div className="mx-auto max-w-5xl space-y-8 p-6">
        <FleetParkSection kind="drivers" />
      </div>
    )
  }

  return <FleetHome />
}
