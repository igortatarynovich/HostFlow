import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import {
  createFleetAssignment,
  deleteFleetAssignment,
  listFleetAssignments,
  listFleetDrivers,
  listFleetOperatingLines,
  listFleetTrailers,
  listFleetVehicles,
  patchFleetAssignment,
  type FleetAssignment,
  type FleetDriver,
  type FleetOperatingLine,
  type FleetTrailer,
  type FleetVehicle,
} from '../../api/fleet'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import {
  FLEET_ASSIGNMENT_STATUSES,
  fleetCalendarHrefFromAssignmentsQuery,
  isValidIsoCalendarDateUtc,
  ISO_DATE,
  ISO_MONTH,
  normalizeFleetAssignmentStatus,
  normalizeFleetCalendarView,
  normalizeServiceDateParam,
  syncFleetCalParamsWithServiceRange,
  utcMonthRangeIso,
} from './fleetQueryParams'

const STATUS_OPTIONS = FLEET_ASSIGNMENT_STATUSES

type AssignmentsQueryKey =
  | 'line_id'
  | 'status'
  | 'service_from'
  | 'service_to'
  | 'cal_view'
  | 'cal_month'
  | 'cal_week'

export default function FleetAssignmentsSection() {
  const { t } = useI18n()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const filterLineId = (searchParams.get('line_id') ?? '').trim()
  const filterStatus = normalizeFleetAssignmentStatus(searchParams.get('status') ?? '')
  const filterServiceFrom = normalizeServiceDateParam(searchParams.get('service_from') ?? '')
  const filterServiceTo = normalizeServiceDateParam(searchParams.get('service_to') ?? '')

  const patchQuery = useCallback(
    (patch: Partial<Record<AssignmentsQueryKey, string>>) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          ;(Object.keys(patch) as AssignmentsQueryKey[]).forEach((key) => {
            if (patch[key] === undefined) return
            const v = patch[key] ?? ''
            if (v) next.set(key, v)
            else next.delete(key)
          })
          syncFleetCalParamsWithServiceRange(next)
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [items, setItems] = useState<FleetAssignment[]>([])
  const [loading, setLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)

  const [lines, setLines] = useState<FleetOperatingLine[]>([])
  const [vehicles, setVehicles] = useState<FleetVehicle[]>([])
  const [trailers, setTrailers] = useState<FleetTrailer[]>([])
  const [drivers, setDrivers] = useState<FleetDriver[]>([])
  const [refsLoading, setRefsLoading] = useState(true)

  const [newLineId, setNewLineId] = useState('')
  const [newVehicleId, setNewVehicleId] = useState('')
  const [newTrailerId, setNewTrailerId] = useState('')
  const [newDriverId, setNewDriverId] = useState('')
  const [newStatus, setNewStatus] = useState('planned')
  const [newStart, setNewStart] = useState(() => new Date().toISOString().slice(0, 10))
  const [newEnd, setNewEnd] = useState('')
  const [newNotes, setNewNotes] = useState('')
  const [creating, setCreating] = useState(false)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTrailerId, setEditTrailerId] = useState('')
  const [editDriverId, setEditDriverId] = useState('')
  const [editStatus, setEditStatus] = useState('planned')
  const [editStart, setEditStart] = useState('')
  const [editEnd, setEditEnd] = useState('')
  const [editNotes, setEditNotes] = useState('')
  const [savingId, setSavingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [highlightAssignmentId, setHighlightAssignmentId] = useState<string | null>(null)

  const loadRefs = useCallback(() => {
    let cancelled = false
    setRefsLoading(true)
    Promise.all([listFleetOperatingLines(), listFleetVehicles(), listFleetTrailers(), listFleetDrivers()])
      .then(([lo, ve, tr, dr]) => {
        if (!cancelled) {
          setLines(lo.items)
          setVehicles(ve.items)
          setTrailers(tr.items)
          setDrivers(dr.items)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(getFriendlyErrorInfo(err))
      })
      .finally(() => {
        if (!cancelled) setRefsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    return loadRefs()
  }, [loadRefs])

  useEffect(() => {
    const bad: Partial<Record<AssignmentsQueryKey, string>> = {}
    const st = (searchParams.get('status') ?? '').trim()
    if (st && !normalizeFleetAssignmentStatus(st)) bad.status = ''
    const sf = (searchParams.get('service_from') ?? '').trim()
    if (sf && !normalizeServiceDateParam(sf)) bad.service_from = ''
    const sto = (searchParams.get('service_to') ?? '').trim()
    if (sto && !normalizeServiceDateParam(sto)) bad.service_to = ''
    const cvRaw = (searchParams.get('cal_view') ?? '').trim()
    const cv = normalizeFleetCalendarView(cvRaw)
    if (cvRaw && !cv) {
      bad.cal_view = ''
      bad.cal_month = ''
      bad.cal_week = ''
    }
    const cm = (searchParams.get('cal_month') ?? '').trim()
    if (cm) {
      if (!ISO_MONTH.test(cm)) bad.cal_month = ''
      else {
        const mn = Number(cm.slice(5, 7))
        if (mn < 1 || mn > 12) bad.cal_month = ''
      }
    }
    const cw = (searchParams.get('cal_week') ?? '').trim()
    if (cw) {
      if (!isValidIsoCalendarDateUtc(cw)) bad.cal_week = ''
    }
    if (Object.keys(bad).length) patchQuery(bad)
  }, [searchParams, patchQuery])

  const loadList = useCallback(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    listFleetAssignments({
      line_id: filterLineId || undefined,
      status: filterStatus || undefined,
      service_from: filterServiceFrom || undefined,
      service_to: filterServiceTo || undefined,
    })
      .then((res) => {
        if (!cancelled) setItems(res.items)
      })
      .catch((err) => {
        if (!cancelled) setError(getFriendlyErrorInfo(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [filterLineId, filterStatus, filterServiceFrom, filterServiceTo, reloadKey])

  useEffect(() => {
    return loadList()
  }, [loadList])

  useEffect(() => {
    const raw = (location.hash || '').replace(/^#/, '')
    if (!raw.startsWith('fleet-assignment-')) {
      setHighlightAssignmentId(null)
      return
    }
    const id = raw.slice('fleet-assignment-'.length)
    if (!id) {
      setHighlightAssignmentId(null)
      return
    }
    setHighlightAssignmentId(id)
    const el = document.getElementById(raw)
    if (el) {
      window.requestAnimationFrame(() => {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      })
    }
    const tid = window.setTimeout(() => setHighlightAssignmentId(null), 4500)
    return () => window.clearTimeout(tid)
  }, [location.hash, items.length, loading])

  function beginEdit(row: FleetAssignment) {
    setEditingId(row.id)
    setEditTrailerId(row.trailer_id ?? '')
    setEditDriverId(row.primary_driver_id ?? '')
    setEditStatus(row.status)
    setEditStart(row.service_start.slice(0, 10))
    setEditEnd(row.service_end?.slice(0, 10) ?? '')
    setEditNotes(row.notes ?? '')
  }

  function cancelEdit() {
    setEditingId(null)
  }

  async function saveEdit(id: string) {
    setSavingId(id)
    setError(null)
    try {
      await patchFleetAssignment(id, {
        trailer_id: editTrailerId || null,
        primary_driver_id: editDriverId || null,
        status: editStatus,
        service_start: editStart,
        service_end: editEnd || null,
        notes: editNotes.trim() || null,
      })
      setEditingId(null)
      setReloadKey((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setSavingId(null)
    }
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    if (!newLineId || !newVehicleId || !newStart) return
    setCreating(true)
    setError(null)
    try {
      await createFleetAssignment({
        line_id: newLineId,
        vehicle_id: newVehicleId,
        trailer_id: newTrailerId || null,
        primary_driver_id: newDriverId || null,
        status: newStatus,
        service_start: newStart,
        service_end: newEnd || null,
        notes: newNotes.trim() || null,
      })
      setNewVehicleId('')
      setNewTrailerId('')
      setNewDriverId('')
      setNewNotes('')
      setReloadKey((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setCreating(false)
    }
  }

  const calendarBackHref = fleetCalendarHrefFromAssignmentsQuery(CRM_APP_PATHS.fleetCalendar, searchParams)

  async function removeRow(id: string) {
    const ok = window.confirm(
      t('app.fleet.assignments.delete_confirm', { defaultValue: 'Delete this assignment?' }),
    )
    if (!ok) return
    setDeletingId(id)
    setError(null)
    try {
      await deleteFleetAssignment(id)
      if (editingId === id) setEditingId(null)
      setReloadKey((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-slate-900">
          {t('app.fleet.assignments.title', { defaultValue: 'Assignments' })}
        </h1>
        <p className="text-slate-600">
          {t('app.fleet.assignments.subtitle', {
            defaultValue: 'Plan which vehicle (and optionally trailer and driver) serves an operating line over a date range.',
          })}
        </p>
        {calendarBackHref ? (
          <p>
            <Link to={calendarBackHref} className="text-sm font-medium text-blue-700 hover:underline">
              {t('app.fleet.assignments.back_to_calendar', { defaultValue: '← Fleet calendar' })}
            </Link>
          </p>
        ) : null}
      </header>

      {error ? (
        <ErrorRecoveryBanner
          info={error}
          onRetry={() => {
            setError(null)
            setReloadKey((k) => k + 1)
          }}
        />
      ) : null}

      <div className="flex flex-wrap gap-3">
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">{t('app.fleet.assignments.filter_line', { defaultValue: 'Line' })}</span>
          <select
            className="input rounded border border-slate-300 px-3 py-2 text-slate-900"
            value={filterLineId}
            onChange={(ev) => patchQuery({ line_id: ev.target.value })}
          >
            <option value="">{t('app.fleet.assignments.filter_all_lines', { defaultValue: 'All lines' })}</option>
            {lines.map((ln) => (
              <option key={ln.id} value={ln.id}>
                {ln.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">{t('app.fleet.assignments.filter_status', { defaultValue: 'Status' })}</span>
          <select
            className="input rounded border border-slate-300 px-3 py-2 text-slate-900"
            value={filterStatus}
            onChange={(ev) => patchQuery({ status: ev.target.value })}
          >
            <option value="">{t('app.fleet.assignments.filter_all_status', { defaultValue: 'All statuses' })}</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {t(`app.fleet.assignments.status_${s}`, { defaultValue: s })}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">
            {t('app.fleet.assignments.filter_service_from', { defaultValue: 'Active from (optional)' })}
          </span>
          <input
            type="date"
            className="input rounded border border-slate-300 px-3 py-2 text-slate-900"
            value={filterServiceFrom}
            onChange={(ev) => patchQuery({ service_from: ev.target.value })}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">
            {t('app.fleet.assignments.filter_service_to', { defaultValue: 'Active through (optional)' })}
          </span>
          <input
            type="date"
            className="input rounded border border-slate-300 px-3 py-2 text-slate-900"
            value={filterServiceTo}
            onChange={(ev) => patchQuery({ service_to: ev.target.value })}
          />
        </label>
        <div className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">
            {t('app.fleet.assignments.filter_period_shortcuts', { defaultValue: 'Quick range' })}
          </span>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => {
                const { from, to } = utcMonthRangeIso(new Date())
                patchQuery({ service_from: from, service_to: to })
              }}
            >
              {t('app.fleet.assignments.period_this_month', { defaultValue: 'This month' })}
            </button>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => {
                patchQuery({ service_from: '', service_to: '' })
              }}
            >
              {t('app.fleet.assignments.period_clear', { defaultValue: 'Clear dates' })}
            </button>
          </div>
        </div>
      </div>
      <p className="text-xs text-slate-500">
        {t('app.fleet.assignments.filter_period_hint', {
          defaultValue:
            'Shows assignments whose service period overlaps the window. Leave both blank for all dates. «This month» is the current UTC calendar month (same as fleet overview / calendar).',
        })}
      </p>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-900">
          {t('app.fleet.assignments.new_title', { defaultValue: 'New assignment' })}
        </h2>
        <form onSubmit={handleCreate} className="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 md:grid-cols-2 lg:grid-cols-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t('app.fleet.assignments.field_line', { defaultValue: 'Operating line' })}</span>
            <select
              className="input rounded border border-slate-300 px-3 py-2"
              value={newLineId}
              onChange={(ev) => setNewLineId(ev.target.value)}
              disabled={creating || refsLoading}
              required
            >
              <option value="">{t('app.fleet.assignments.pick_line', { defaultValue: 'Select…' })}</option>
              {lines.map((ln) => (
                <option key={ln.id} value={ln.id}>
                  {ln.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t('app.fleet.assignments.field_vehicle', { defaultValue: 'Vehicle' })}</span>
            <select
              className="input rounded border border-slate-300 px-3 py-2"
              value={newVehicleId}
              onChange={(ev) => setNewVehicleId(ev.target.value)}
              disabled={creating || refsLoading}
              required
            >
              <option value="">{t('app.fleet.assignments.pick_vehicle', { defaultValue: 'Select…' })}</option>
              {vehicles.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.internal_code || v.registration_plate || [v.brand, v.model].filter(Boolean).join(' ') || v.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t('app.fleet.assignments.field_trailer', { defaultValue: 'Trailer (optional)' })}</span>
            <select
              className="input rounded border border-slate-300 px-3 py-2"
              value={newTrailerId}
              onChange={(ev) => setNewTrailerId(ev.target.value)}
              disabled={creating || refsLoading}
            >
              <option value="">{t('app.fleet.assignments.none', { defaultValue: '—' })}</option>
              {trailers.map((tr) => (
                <option key={tr.id} value={tr.id}>
                  {tr.internal_code || tr.registration_plate || tr.trailer_type || tr.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t('app.fleet.assignments.field_driver', { defaultValue: 'Driver (optional)' })}</span>
            <select
              className="input rounded border border-slate-300 px-3 py-2"
              value={newDriverId}
              onChange={(ev) => setNewDriverId(ev.target.value)}
              disabled={creating || refsLoading}
            >
              <option value="">{t('app.fleet.assignments.none', { defaultValue: '—' })}</option>
              {drivers.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.display_code || [d.first_name, d.last_name].filter(Boolean).join(' ') || d.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t('app.fleet.assignments.field_status', { defaultValue: 'Status' })}</span>
            <select
              className="input rounded border border-slate-300 px-3 py-2"
              value={newStatus}
              onChange={(ev) => setNewStatus(ev.target.value)}
              disabled={creating}
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {t(`app.fleet.assignments.status_${s}`, { defaultValue: s })}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t('app.fleet.assignments.field_start', { defaultValue: 'Service start' })}</span>
            <input
              type="date"
              className="input rounded border border-slate-300 px-3 py-2"
              value={newStart}
              onChange={(ev) => setNewStart(ev.target.value)}
              disabled={creating}
              required
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t('app.fleet.assignments.field_end', { defaultValue: 'Service end (optional)' })}</span>
            <input
              type="date"
              className="input rounded border border-slate-300 px-3 py-2"
              value={newEnd}
              onChange={(ev) => setNewEnd(ev.target.value)}
              disabled={creating}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm md:col-span-2 lg:col-span-3">
            <span className="font-medium text-slate-700">{t('app.fleet.assignments.field_notes', { defaultValue: 'Notes' })}</span>
            <input
              className="input rounded border border-slate-300 px-3 py-2"
              value={newNotes}
              onChange={(ev) => setNewNotes(ev.target.value)}
              disabled={creating}
            />
          </label>
          <div className="md:col-span-2 lg:col-span-3">
            <button
              type="submit"
              className="btn rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              disabled={creating || refsLoading || !newLineId || !newVehicleId}
            >
              {t('app.fleet.assignments.create', { defaultValue: 'Create assignment' })}
            </button>
          </div>
        </form>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-slate-900">
          {t('app.fleet.assignments.list_title', { defaultValue: 'Assignments' })}
        </h2>
        {loading ? (
          <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-slate-600">{t('app.fleet.assignments.empty', { defaultValue: 'No assignments match the filters.' })}</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">
                    {t('app.fleet.assignments.col_line', { defaultValue: 'Line' })}
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">
                    {t('app.fleet.assignments.col_vehicle', { defaultValue: 'Vehicle' })}
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">
                    {t('app.fleet.assignments.col_trailer', { defaultValue: 'Trailer' })}
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">
                    {t('app.fleet.assignments.col_driver', { defaultValue: 'Driver' })}
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">
                    {t('app.fleet.assignments.col_status', { defaultValue: 'Status' })}
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">
                    {t('app.fleet.assignments.col_period', { defaultValue: 'Period' })}
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">
                    {t('app.fleet.assignments.col_notes', { defaultValue: 'Notes' })}
                  </th>
                  <th className="px-3 py-2 text-right font-medium text-slate-700">
                    {t('app.fleet.assignments.col_actions', { defaultValue: 'Actions' })}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {items.map((row) => (
                  <tr
                    key={row.id}
                    id={`fleet-assignment-${row.id}`}
                    className={
                      highlightAssignmentId === row.id
                        ? 'bg-amber-50 ring-1 ring-inset ring-amber-200 transition-colors duration-300'
                        : undefined
                    }
                  >
                    {editingId === row.id ? (
                      <>
                        <td className="px-3 py-2 text-slate-700">{row.line_name}</td>
                        <td className="px-3 py-2 text-slate-700">{row.vehicle_label}</td>
                        <td className="px-3 py-2">
                          <select
                            className="input max-w-hf-140 rounded border border-slate-300 px-1 py-1 text-xs"
                            value={editTrailerId}
                            onChange={(ev) => setEditTrailerId(ev.target.value)}
                          >
                            <option value="">{t('app.fleet.assignments.none', { defaultValue: '—' })}</option>
                            {trailers.map((tr) => (
                              <option key={tr.id} value={tr.id}>
                                {tr.internal_code || tr.registration_plate || tr.id.slice(0, 8)}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-3 py-2">
                          <select
                            className="input max-w-hf-140 rounded border border-slate-300 px-1 py-1 text-xs"
                            value={editDriverId}
                            onChange={(ev) => setEditDriverId(ev.target.value)}
                          >
                            <option value="">{t('app.fleet.assignments.none', { defaultValue: '—' })}</option>
                            {drivers.map((d) => (
                              <option key={d.id} value={d.id}>
                                {d.display_code || d.id.slice(0, 8)}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-3 py-2">
                          <select
                            className="input rounded border border-slate-300 px-1 py-1 text-xs"
                            value={editStatus}
                            onChange={(ev) => setEditStatus(ev.target.value)}
                          >
                            {STATUS_OPTIONS.map((s) => (
                              <option key={s} value={s}>
                                {s}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex flex-col gap-1">
                            <input
                              type="date"
                              className="input rounded border border-slate-300 px-1 py-1 text-xs"
                              value={editStart}
                              onChange={(ev) => setEditStart(ev.target.value)}
                            />
                            <input
                              type="date"
                              className="input rounded border border-slate-300 px-1 py-1 text-xs"
                              value={editEnd}
                              onChange={(ev) => setEditEnd(ev.target.value)}
                            />
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          <input
                            className="input w-full min-w-hf-100 rounded border border-slate-300 px-1 py-1 text-xs"
                            value={editNotes}
                            onChange={(ev) => setEditNotes(ev.target.value)}
                          />
                        </td>
                        <td className="space-x-2 px-3 py-2 text-right whitespace-nowrap">
                          <button
                            type="button"
                            className="btn text-blue-700 hover:underline"
                            onClick={() => void saveEdit(row.id)}
                            disabled={savingId === row.id}
                          >
                            {t('common.actions.save', { defaultValue: 'Save' })}
                          </button>
                          <button type="button" className="btn text-slate-600 hover:underline" onClick={cancelEdit}>
                            {t('common.actions.cancel', { defaultValue: 'Cancel' })}
                          </button>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-3 py-2 font-medium text-slate-900">{row.line_name}</td>
                        <td className="px-3 py-2 text-slate-700">{row.vehicle_label}</td>
                        <td className="px-3 py-2 text-slate-600">{row.trailer_label ?? '—'}</td>
                        <td className="px-3 py-2 text-slate-600">{row.primary_driver_label ?? '—'}</td>
                        <td className="px-3 py-2 text-slate-700">
                          {t(`app.fleet.assignments.status_${row.status}`, { defaultValue: row.status })}
                        </td>
                        <td className="px-3 py-2 text-slate-600">
                          {row.service_start.slice(0, 10)}
                          {row.service_end ? ` → ${row.service_end.slice(0, 10)}` : ''}
                        </td>
                        <td className="max-w-hf-180 truncate px-3 py-2 text-slate-500">{row.notes ?? '—'}</td>
                        <td className="space-x-2 px-3 py-2 text-right whitespace-nowrap">
                          <button type="button" className="btn text-blue-700 hover:underline" onClick={() => beginEdit(row)}>
                            {t('common.actions.edit', { defaultValue: 'Edit' })}
                          </button>
                          <button
                            type="button"
                            className="btn text-red-700 hover:underline disabled:opacity-50"
                            onClick={() => void removeRow(row.id)}
                            disabled={deletingId === row.id}
                          >
                            {t('common.actions.delete', { defaultValue: 'Delete' })}
                          </button>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
