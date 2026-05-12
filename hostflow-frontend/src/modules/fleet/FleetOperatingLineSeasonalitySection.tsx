import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  getFleetOperatingLineSeasonalityFromData,
  listFleetOperatingLines,
  type FleetOperatingLine,
  type FleetSeasonalityFromDataResponse,
} from '../../api/fleet'
import { CRM_APP_PATHS, fleetOperatingLineSeasonalityPath } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import FleetSeasonalityBars from './FleetSeasonalityBars'

const SEASONALITY_MONTHS_BACK = 24

type Props = {
  selectedLineId: string | undefined
}

export default function FleetOperatingLineSeasonalitySection({ selectedLineId }: Props) {
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const [lines, setLines] = useState<FleetOperatingLine[]>([])
  const [linesLoading, setLinesLoading] = useState(true)
  const [linesError, setLinesError] = useState<FriendlyErrorInfo | null>(null)

  const [blendRoster, setBlendRoster] = useState(false)
  const [reloadNonce, setReloadNonce] = useState(0)
  const [dataLoading, setDataLoading] = useState(false)
  const [dataError, setDataError] = useState<FriendlyErrorInfo | null>(null)
  const [seasonalityData, setSeasonalityData] = useState<FleetSeasonalityFromDataResponse | null>(null)

  useEffect(() => {
    let cancelled = false
    setLinesLoading(true)
    setLinesError(null)
    listFleetOperatingLines()
      .then((res) => {
        if (!cancelled) setLines(res.items)
      })
      .catch((err) => {
        if (!cancelled) setLinesError(getFriendlyErrorInfo(err))
      })
      .finally(() => {
        if (!cancelled) setLinesLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const linesSorted = useMemo(
    () => [...lines].sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })),
    [lines],
  )

  useEffect(() => {
    if (!selectedLineId?.trim()) {
      setSeasonalityData(null)
      setDataLoading(false)
      setDataError(null)
      return
    }
    const lineId = selectedLineId.trim()
    let cancelled = false
    setDataLoading(true)
    setDataError(null)
    const params = blendRoster
      ? {
          months_back: SEASONALITY_MONTHS_BACK,
          sources: 'assignments,roster',
          weight_assignments: 0.5,
          weight_roster: 0.5,
        }
      : { months_back: SEASONALITY_MONTHS_BACK, sources: 'assignments' }
    getFleetOperatingLineSeasonalityFromData(lineId, params)
      .then((d) => {
        if (!cancelled) {
          setSeasonalityData(d)
          setDataLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setDataError(getFriendlyErrorInfo(err))
          setSeasonalityData(null)
          setDataLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [selectedLineId, blendRoster, reloadNonce])

  if (linesError) {
    return (
      <div className="space-y-4">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold text-slate-900">
            {t('app.fleet.line_seasonality.title', { defaultValue: 'Line seasonality' })}
          </h1>
        </header>
        <ErrorRecoveryBanner info={linesError} onRetry={() => window.location.reload()} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <h1 className="text-2xl font-semibold text-slate-900">
            {t('app.fleet.line_seasonality.title', { defaultValue: 'Line seasonality' })}
          </h1>
          <Link
            to={CRM_APP_PATHS.fleetOperatingLines}
            className="text-sm font-medium text-blue-700 hover:underline"
          >
            {t('app.fleet.line_seasonality.back_lines', { defaultValue: '← Operating lines' })}
          </Link>
        </div>
        <p className="text-slate-600">
          {t('app.fleet.line_seasonality.subtitle', {
            defaultValue: 'Monthly weights from fleet data (assignments and optionally roster). Mean ≈ 1.',
          })}
        </p>
      </header>

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <label className="flex max-w-xl flex-col gap-2 text-sm">
          <span className="font-medium text-slate-700">
            {t('app.fleet.line_seasonality.pick_line', { defaultValue: 'Operating line' })}
          </span>
          <select
            className="input rounded border border-slate-300 px-3 py-2 text-slate-900"
            disabled={linesLoading}
            value={selectedLineId ?? ''}
            onChange={(ev) => {
              const v = ev.target.value.trim()
              if (v) navigate(fleetOperatingLineSeasonalityPath(v))
              else navigate(CRM_APP_PATHS.fleetOperatingLinesSeasonality)
            }}
          >
            <option value="">
              {t('app.fleet.line_seasonality.pick_placeholder', { defaultValue: 'Select a line…' })}
            </option>
            {linesSorted.map((ln) => (
              <option key={ln.id} value={ln.id}>
                {ln.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {!selectedLineId?.trim() ? (
        <p className="text-sm text-slate-600">
          {t('app.fleet.line_seasonality.pick_hint', {
            defaultValue: 'Choose a line to load its seasonality curve.',
          })}
        </p>
      ) : null}

      {selectedLineId?.trim() ? (
        <div className="space-y-4 rounded-lg border border-slate-200 bg-slate-50/80 p-4">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              className="rounded border-slate-300"
              checked={blendRoster}
              onChange={(ev) => setBlendRoster(ev.target.checked)}
            />
            {t('app.fleet.operating_lines.seasonality_blend_roster', {
              defaultValue: 'Blend with line roster (assignments + roster, 50% / 50%)',
            })}
          </label>
          <p className="text-xs text-slate-500">
            {t('app.fleet.operating_lines.seasonality_hint', {
              defaultValue:
                'Weights are relative by calendar month (mean ≈ 1). Based on assignment overlap; optional roster mix uses drivers (effective dates) and vehicles on the line.',
            })}
          </p>

          {dataLoading ? (
            <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
          ) : null}
          {dataError ? (
            <ErrorRecoveryBanner
              info={dataError}
              onRetry={() => {
                setDataError(null)
                setReloadNonce((n) => n + 1)
              }}
            />
          ) : null}

          {!dataLoading && seasonalityData ? (
            <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs text-slate-600">
                {t('app.fleet.operating_lines.seasonality_period', { defaultValue: 'Period' })}:{' '}
                {seasonalityData.period_from.slice(0, 10)} → {seasonalityData.period_to.slice(0, 10)}
                {' · '}
                {seasonalityData.source === 'assignments'
                  ? t('app.fleet.operating_lines.seasonality_source_assignments', {
                      defaultValue: 'Assignments only',
                    })
                  : seasonalityData.source === 'roster'
                    ? t('app.fleet.operating_lines.seasonality_source_roster', {
                        defaultValue: 'Roster only',
                      })
                    : t('app.fleet.operating_lines.seasonality_source_blend', {
                        defaultValue: 'Blended',
                      })}
                {seasonalityData.blend_weights && seasonalityData.source === 'blend'
                  ? ` (${Object.entries(seasonalityData.blend_weights)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(', ')})`
                  : ''}
              </p>
              {seasonalityData.insufficient_data ? (
                <p className="text-sm text-amber-800">
                  {t('app.fleet.operating_lines.seasonality_insufficient', {
                    defaultValue: 'Not enough history in this window for a meaningful curve.',
                  })}
                  {seasonalityData.detail ? ` (${seasonalityData.detail})` : ''}
                </p>
              ) : null}
              <FleetSeasonalityBars data={seasonalityData} locale={locale} />
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
