import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  addFleetLineDriver,
  addFleetLineVehicle,
  createFleetWorkModel,
  deleteFleetLineDriver,
  deleteFleetLineVehicle,
  deleteFleetWorkModel,
  listFleetDrivers,
  listFleetLineDrivers,
  listFleetLineVehicles,
  listFleetOperatingLines,
  listFleetVehicles,
  listFleetWorkModels,
  patchFleetLineDriver,
  patchFleetLineVehicle,
  patchFleetWorkModel,
  type FleetDriver,
  type FleetLineDriver,
  type FleetLineVehicle,
  type FleetOperatingLine,
  type FleetVehicle,
  type FleetWorkModel,
} from '../../api/fleet'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

function vehicleOptionLabel(v: FleetVehicle): string {
  return (
    v.internal_code ||
    v.registration_plate ||
    [v.brand, v.model].filter(Boolean).join(' ') ||
    v.id.slice(0, 8)
  )
}

function driverOptionLabel(d: FleetDriver): string {
  return d.display_code || [d.first_name, d.last_name].filter(Boolean).join(' ') || d.id.slice(0, 8)
}

export default function FleetRotationSection() {
  const { t } = useI18n()
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)

  const [workModels, setWorkModels] = useState<FleetWorkModel[]>([])
  const [wmLoading, setWmLoading] = useState(true)
  const [wmReload, setWmReload] = useState(0)
  const [wmName, setWmName] = useState('')
  const [wmWork, setWmWork] = useState('5')
  const [wmRest, setWmRest] = useState('2')
  const [wmCycle, setWmCycle] = useState('7')
  const [wmNotes, setWmNotes] = useState('')
  const [wmCreating, setWmCreating] = useState(false)
  const [wmEditingId, setWmEditingId] = useState<string | null>(null)
  const [wmEditName, setWmEditName] = useState('')
  const [wmEditWork, setWmEditWork] = useState('')
  const [wmEditRest, setWmEditRest] = useState('')
  const [wmEditCycle, setWmEditCycle] = useState('')
  const [wmEditNotes, setWmEditNotes] = useState('')
  const [wmSavingId, setWmSavingId] = useState<string | null>(null)
  const [wmDeletingId, setWmDeletingId] = useState<string | null>(null)

  const [lines, setLines] = useState<FleetOperatingLine[]>([])
  const [lineId, setLineId] = useState('')
  const [linesLoading, setLinesLoading] = useState(true)

  const [vehicles, setVehicles] = useState<FleetVehicle[]>([])
  const [drivers, setDrivers] = useState<FleetDriver[]>([])
  const [lineVehicles, setLineVehicles] = useState<FleetLineVehicle[]>([])
  const [lineDrivers, setLineDrivers] = useState<FleetLineDriver[]>([])
  const [membersLoading, setMembersLoading] = useState(false)
  const [membersReload, setMembersReload] = useState(0)

  const [addVehicleId, setAddVehicleId] = useState('')
  const [addVehicleWm, setAddVehicleWm] = useState('')
  const [addDriverId, setAddDriverId] = useState('')
  const [addDriverWm, setAddDriverWm] = useState('')
  const [addDriverFrom, setAddDriverFrom] = useState('')
  const [addDriverTo, setAddDriverTo] = useState('')
  const [addingVehicle, setAddingVehicle] = useState(false)
  const [addingDriver, setAddingDriver] = useState(false)
  const [removingVehicleId, setRemovingVehicleId] = useState<string | null>(null)
  const [removingDriverId, setRemovingDriverId] = useState<string | null>(null)

  const [driverDrafts, setDriverDrafts] = useState<
    Record<string, { work_model_id: string; effective_from: string; effective_to: string }>
  >({})
  const [driverSavingId, setDriverSavingId] = useState<string | null>(null)

  const loadWorkModels = useCallback(() => {
    let cancelled = false
    setWmLoading(true)
    setError(null)
    listFleetWorkModels()
      .then((res) => {
        if (!cancelled) setWorkModels(res.items)
      })
      .catch((err) => {
        if (!cancelled) setError(getFriendlyErrorInfo(err))
      })
      .finally(() => {
        if (!cancelled) setWmLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    return loadWorkModels()
  }, [loadWorkModels, wmReload])

  const loadLinesAndPark = useCallback(() => {
    let cancelled = false
    setLinesLoading(true)
    setError(null)
    Promise.all([listFleetOperatingLines(), listFleetVehicles(), listFleetDrivers()])
      .then(([lo, ve, dr]) => {
        if (!cancelled) {
          setLines(lo.items)
          setVehicles(ve.items)
          setDrivers(dr.items)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(getFriendlyErrorInfo(err))
      })
      .finally(() => {
        if (!cancelled) setLinesLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    return loadLinesAndPark()
  }, [loadLinesAndPark])

  const loadMembers = useCallback(() => {
    if (!lineId) {
      setLineVehicles([])
      setLineDrivers([])
      return () => undefined
    }
    let cancelled = false
    setMembersLoading(true)
    setError(null)
    Promise.all([listFleetLineVehicles(lineId), listFleetLineDrivers(lineId)])
      .then(([lv, ld]) => {
        if (!cancelled) {
          setLineVehicles(lv.items)
          setLineDrivers(ld.items)
          const next: Record<string, { work_model_id: string; effective_from: string; effective_to: string }> = {}
          for (const row of ld.items) {
            next[row.id] = {
              work_model_id: row.work_model_id,
              effective_from: row.effective_from?.slice(0, 10) ?? '',
              effective_to: row.effective_to?.slice(0, 10) ?? '',
            }
          }
          setDriverDrafts(next)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(getFriendlyErrorInfo(err))
      })
      .finally(() => {
        if (!cancelled) setMembersLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [lineId, membersReload])

  useEffect(() => {
    return loadMembers()
  }, [loadMembers])

  const vehicleIdsOnLine = useMemo(() => new Set(lineVehicles.map((x) => x.vehicle_id)), [lineVehicles])
  const driverIdsOnLine = useMemo(() => new Set(lineDrivers.map((x) => x.fleet_driver_id)), [lineDrivers])

  const vehiclesToAdd = useMemo(
    () => vehicles.filter((v) => !vehicleIdsOnLine.has(v.id)),
    [vehicles, vehicleIdsOnLine],
  )
  const driversToAdd = useMemo(
    () => drivers.filter((d) => !driverIdsOnLine.has(d.id)),
    [drivers, driverIdsOnLine],
  )

  function beginEditWm(row: FleetWorkModel) {
    setWmEditingId(row.id)
    setWmEditName(row.name)
    setWmEditWork(String(row.work_days))
    setWmEditRest(String(row.rest_days))
    setWmEditCycle(String(row.cycle_length))
    setWmEditNotes(row.notes ?? '')
  }

  function cancelEditWm() {
    setWmEditingId(null)
  }

  async function saveEditWm() {
    if (!wmEditingId) return
    const name = wmEditName.trim()
    if (!name) return
    const work_days = Number.parseInt(wmEditWork, 10)
    const rest_days = Number.parseInt(wmEditRest, 10)
    const cycle_length = Number.parseInt(wmEditCycle, 10)
    if (!Number.isFinite(work_days) || !Number.isFinite(rest_days) || !Number.isFinite(cycle_length)) return
    setWmSavingId(wmEditingId)
    setError(null)
    try {
      await patchFleetWorkModel(wmEditingId, {
        name,
        work_days,
        rest_days,
        cycle_length,
        notes: wmEditNotes.trim() || null,
      })
      setWmEditingId(null)
      setWmReload((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setWmSavingId(null)
    }
  }

  async function handleCreateWm(e: FormEvent) {
    e.preventDefault()
    const name = wmName.trim()
    if (!name) return
    const work_days = Number.parseInt(wmWork, 10)
    const rest_days = Number.parseInt(wmRest, 10)
    const cycle_length = Number.parseInt(wmCycle, 10)
    if (!Number.isFinite(work_days) || !Number.isFinite(rest_days) || !Number.isFinite(cycle_length)) return
    setWmCreating(true)
    setError(null)
    try {
      await createFleetWorkModel({
        name,
        work_days,
        rest_days,
        cycle_length,
        notes: wmNotes.trim() || undefined,
      })
      setWmName('')
      setWmNotes('')
      setWmReload((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setWmCreating(false)
    }
  }

  async function removeWm(id: string) {
    const ok = window.confirm(
      t('app.fleet.rotation.delete_wm_confirm', { defaultValue: 'Delete this work model? It may be in use.' }),
    )
    if (!ok) return
    setWmDeletingId(id)
    setError(null)
    try {
      await deleteFleetWorkModel(id)
      if (wmEditingId === id) setWmEditingId(null)
      setWmReload((k) => k + 1)
      setMembersReload((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setWmDeletingId(null)
    }
  }

  async function onVehicleDefaultWmChange(m: FleetLineVehicle, wmId: string | '') {
    if (!lineId) return
    setError(null)
    try {
      await patchFleetLineVehicle(lineId, m.id, {
        default_work_model_id: wmId || null,
      })
      setMembersReload((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    }
  }

  async function handleAddVehicle(e: FormEvent) {
    e.preventDefault()
    if (!lineId || !addVehicleId) return
    setAddingVehicle(true)
    setError(null)
    try {
      await addFleetLineVehicle(lineId, {
        vehicle_id: addVehicleId,
        default_work_model_id: addVehicleWm || null,
      })
      setAddVehicleId('')
      setAddVehicleWm('')
      setMembersReload((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setAddingVehicle(false)
    }
  }

  async function removeLineVehicle(m: FleetLineVehicle) {
    if (!lineId) return
    const ok = window.confirm(
      t('app.fleet.rotation.remove_vehicle_confirm', { defaultValue: 'Remove this vehicle from the line?' }),
    )
    if (!ok) return
    setRemovingVehicleId(m.id)
    setError(null)
    try {
      await deleteFleetLineVehicle(lineId, m.id)
      setMembersReload((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setRemovingVehicleId(null)
    }
  }

  async function handleAddDriver(e: FormEvent) {
    e.preventDefault()
    if (!lineId || !addDriverId || !addDriverWm) return
    setAddingDriver(true)
    setError(null)
    try {
      await addFleetLineDriver(lineId, {
        fleet_driver_id: addDriverId,
        work_model_id: addDriverWm,
        effective_from: addDriverFrom || null,
        effective_to: addDriverTo || null,
      })
      setAddDriverId('')
      setAddDriverWm('')
      setAddDriverFrom('')
      setAddDriverTo('')
      setMembersReload((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setAddingDriver(false)
    }
  }

  async function saveDriverRow(membershipId: string) {
    if (!lineId) return
    const d = driverDrafts[membershipId]
    if (!d?.work_model_id) return
    setDriverSavingId(membershipId)
    setError(null)
    try {
      await patchFleetLineDriver(lineId, membershipId, {
        work_model_id: d.work_model_id,
        effective_from: d.effective_from || null,
        effective_to: d.effective_to || null,
      })
      setMembersReload((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setDriverSavingId(null)
    }
  }

  async function removeLineDriver(m: FleetLineDriver) {
    if (!lineId) return
    const ok = window.confirm(
      t('app.fleet.rotation.remove_driver_confirm', { defaultValue: 'Remove this driver from the line?' }),
    )
    if (!ok) return
    setRemovingDriverId(m.id)
    setError(null)
    try {
      await deleteFleetLineDriver(lineId, m.id)
      setMembersReload((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setRemovingDriverId(null)
    }
  }

  if (error) {
    return (
      <section className="space-y-3">
        <h1 className="text-2xl font-semibold text-slate-900">
          {t('app.fleet.rotation.page_title', { defaultValue: 'Rotation & line roster' })}
        </h1>
        <ErrorRecoveryBanner info={error} onRetry={() => window.location.reload()} />
      </section>
    )
  }

  const wmSelect = (value: string, onChange: (v: string) => void, includeEmpty: boolean) => (
    <select
      className="input rounded border border-slate-300 px-2 py-1.5 text-sm text-slate-900"
      value={value}
      onChange={(ev) => onChange(ev.target.value)}
    >
      {includeEmpty ? <option value="">{t('app.fleet.rotation.none', { defaultValue: '—' })}</option> : null}
      {workModels.map((wm) => (
        <option key={wm.id} value={wm.id}>
          {wm.name} ({wm.work_days}+{wm.rest_days}/{wm.cycle_length})
        </option>
      ))}
    </select>
  )

  return (
    <div className="space-y-10">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-slate-900">
          {t('app.fleet.rotation.page_title', { defaultValue: 'Rotation & line roster' })}
        </h1>
        <p className="text-slate-600">
          {t('app.fleet.rotation.page_subtitle', {
            defaultValue: 'Define work/rest cycle templates and assign vehicles and drivers to an operating line.',
          })}
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-900">
          {t('app.fleet.rotation.work_models_title', { defaultValue: 'Work models' })}
        </h2>
        <p className="text-sm text-slate-600">
          {t('app.fleet.rotation.cycle_hint', {
            defaultValue: 'Work days + rest days must equal the cycle length (e.g. 5+2=7).',
          })}
        </p>
        <form onSubmit={handleCreateWm} className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <label className="flex min-w-hf-160 flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t('app.fleet.rotation.wm_name', { defaultValue: 'Name' })}</span>
            <input
              className="input rounded border border-slate-300 px-3 py-2 text-slate-900"
              value={wmName}
              onChange={(ev) => setWmName(ev.target.value)}
              maxLength={255}
              disabled={wmCreating}
            />
          </label>
          <label className="flex w-20 flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t('app.fleet.rotation.wm_work', { defaultValue: 'Work' })}</span>
            <input
              type="number"
              min={1}
              className="input rounded border border-slate-300 px-2 py-2 text-slate-900"
              value={wmWork}
              onChange={(ev) => setWmWork(ev.target.value)}
              disabled={wmCreating}
            />
          </label>
          <label className="flex w-20 flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t('app.fleet.rotation.wm_rest', { defaultValue: 'Rest' })}</span>
            <input
              type="number"
              min={0}
              className="input rounded border border-slate-300 px-2 py-2 text-slate-900"
              value={wmRest}
              onChange={(ev) => setWmRest(ev.target.value)}
              disabled={wmCreating}
            />
          </label>
          <label className="flex w-24 flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t('app.fleet.rotation.wm_cycle', { defaultValue: 'Cycle' })}</span>
            <input
              type="number"
              min={1}
              className="input rounded border border-slate-300 px-2 py-2 text-slate-900"
              value={wmCycle}
              onChange={(ev) => setWmCycle(ev.target.value)}
              disabled={wmCreating}
            />
          </label>
          <label className="flex min-w-hf-200 flex-1 flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t('app.fleet.rotation.wm_notes', { defaultValue: 'Notes' })}</span>
            <input
              className="input rounded border border-slate-300 px-3 py-2 text-slate-900"
              value={wmNotes}
              onChange={(ev) => setWmNotes(ev.target.value)}
              disabled={wmCreating}
            />
          </label>
          <button
            type="submit"
            className="btn rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            disabled={wmCreating}
          >
            {t('app.fleet.rotation.wm_add', { defaultValue: 'Add model' })}
          </button>
        </form>

        {wmLoading ? (
          <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
        ) : workModels.length === 0 ? (
          <p className="text-sm text-slate-600">{t('app.fleet.rotation.wm_empty', { defaultValue: 'No work models yet.' })}</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">{t('app.fleet.rotation.wm_name', { defaultValue: 'Name' })}</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">{t('app.fleet.rotation.wm_work', { defaultValue: 'Work' })}</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">{t('app.fleet.rotation.wm_rest', { defaultValue: 'Rest' })}</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">{t('app.fleet.rotation.wm_cycle', { defaultValue: 'Cycle' })}</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">{t('app.fleet.rotation.wm_notes', { defaultValue: 'Notes' })}</th>
                  <th className="px-3 py-2 text-right font-medium text-slate-700">{t('app.fleet.rotation.actions', { defaultValue: 'Actions' })}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {workModels.map((row) => (
                  <tr key={row.id}>
                    {wmEditingId === row.id ? (
                      <>
                        <td className="px-3 py-2">
                          <input
                            className="input w-full rounded border border-slate-300 px-2 py-1"
                            value={wmEditName}
                            onChange={(ev) => setWmEditName(ev.target.value)}
                          />
                        </td>
                        <td className="px-3 py-2">
                          <input
                            type="number"
                            min={1}
                            className="input w-16 rounded border border-slate-300 px-2 py-1"
                            value={wmEditWork}
                            onChange={(ev) => setWmEditWork(ev.target.value)}
                          />
                        </td>
                        <td className="px-3 py-2">
                          <input
                            type="number"
                            min={0}
                            className="input w-16 rounded border border-slate-300 px-2 py-1"
                            value={wmEditRest}
                            onChange={(ev) => setWmEditRest(ev.target.value)}
                          />
                        </td>
                        <td className="px-3 py-2">
                          <input
                            type="number"
                            min={1}
                            className="input w-16 rounded border border-slate-300 px-2 py-1"
                            value={wmEditCycle}
                            onChange={(ev) => setWmEditCycle(ev.target.value)}
                          />
                        </td>
                        <td className="px-3 py-2">
                          <input
                            className="input w-full rounded border border-slate-300 px-2 py-1"
                            value={wmEditNotes}
                            onChange={(ev) => setWmEditNotes(ev.target.value)}
                          />
                        </td>
                        <td className="space-x-2 px-3 py-2 text-right whitespace-nowrap">
                          <button
                            type="button"
                            className="btn text-blue-700 hover:underline"
                            onClick={() => void saveEditWm()}
                            disabled={wmSavingId === row.id}
                          >
                            {t('common.actions.save', { defaultValue: 'Save' })}
                          </button>
                          <button type="button" className="btn text-slate-600 hover:underline" onClick={cancelEditWm}>
                            {t('common.actions.cancel', { defaultValue: 'Cancel' })}
                          </button>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-3 py-2 font-medium text-slate-900">{row.name}</td>
                        <td className="px-3 py-2 text-slate-700">{row.work_days}</td>
                        <td className="px-3 py-2 text-slate-700">{row.rest_days}</td>
                        <td className="px-3 py-2 text-slate-700">{row.cycle_length}</td>
                        <td className="max-w-xs truncate px-3 py-2 text-slate-600">{row.notes ?? '—'}</td>
                        <td className="space-x-2 px-3 py-2 text-right whitespace-nowrap">
                          <button type="button" className="btn text-blue-700 hover:underline" onClick={() => beginEditWm(row)}>
                            {t('common.actions.edit', { defaultValue: 'Edit' })}
                          </button>
                          <button
                            type="button"
                            className="btn text-red-700 hover:underline disabled:opacity-50"
                            onClick={() => void removeWm(row.id)}
                            disabled={wmDeletingId === row.id}
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

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-slate-900">
          {t('app.fleet.rotation.line_roster_title', { defaultValue: 'Line roster' })}
        </h2>
        {linesLoading ? (
          <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
        ) : (
          <label className="flex max-w-md flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t('app.fleet.rotation.pick_line', { defaultValue: 'Operating line' })}</span>
            <select
              className="input rounded border border-slate-300 px-3 py-2 text-slate-900"
              value={lineId}
              onChange={(ev) => setLineId(ev.target.value)}
            >
              <option value="">{t('app.fleet.rotation.pick_line_placeholder', { defaultValue: 'Select a line…' })}</option>
              {lines.map((ln) => (
                <option key={ln.id} value={ln.id}>
                  {ln.name}
                </option>
              ))}
            </select>
          </label>
        )}

        {!lineId ? (
          <p className="text-sm text-slate-600">{t('app.fleet.rotation.pick_line_hint', { defaultValue: 'Choose a line to manage vehicles and drivers.' })}</p>
        ) : membersLoading ? (
          <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
        ) : (
          <div className="grid gap-8 lg:grid-cols-2">
            <div className="space-y-3">
              <h3 className="font-medium text-slate-900">{t('app.fleet.rotation.vehicles_on_line', { defaultValue: 'Vehicles on line' })}</h3>
              <form onSubmit={handleAddVehicle} className="flex flex-wrap items-end gap-2 rounded border border-slate-200 bg-slate-50/80 p-3">
                <label className="flex min-w-hf-180 flex-1 flex-col gap-1 text-xs">
                  <span>{t('app.fleet.rotation.add_vehicle', { defaultValue: 'Add vehicle' })}</span>
                  <select
                    className="input rounded border border-slate-300 px-2 py-1.5 text-sm"
                    value={addVehicleId}
                    onChange={(ev) => setAddVehicleId(ev.target.value)}
                    disabled={addingVehicle || vehiclesToAdd.length === 0}
                  >
                    <option value="">{t('app.fleet.rotation.pick_vehicle', { defaultValue: 'Select vehicle…' })}</option>
                    {vehiclesToAdd.map((v) => (
                      <option key={v.id} value={v.id}>
                        {vehicleOptionLabel(v)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex min-w-hf-160 flex-col gap-1 text-xs">
                  <span>{t('app.fleet.rotation.default_model', { defaultValue: 'Default work model' })}</span>
                  {wmSelect(addVehicleWm, setAddVehicleWm, true)}
                </label>
                <button
                  type="submit"
                  className="btn rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50"
                  disabled={addingVehicle || !addVehicleId}
                >
                  {t('app.fleet.park.add', { defaultValue: 'Add' })}
                </button>
              </form>
              {lineVehicles.length === 0 ? (
                <p className="text-sm text-slate-600">{t('app.fleet.rotation.vehicles_empty', { defaultValue: 'No vehicles on this line.' })}</p>
              ) : (
                <ul className="space-y-2">
                  {lineVehicles.map((m) => (
                    <li
                      key={m.id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded border border-slate-100 bg-white px-3 py-2 text-sm"
                    >
                      <span className="font-medium text-slate-900">{m.vehicle_label}</span>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs text-slate-600">{t('app.fleet.rotation.default_model', { defaultValue: 'Default work model' })}</span>
                        <select
                          className="input rounded border border-slate-300 px-2 py-1 text-xs"
                          value={m.default_work_model_id ?? ''}
                          onChange={(ev) => void onVehicleDefaultWmChange(m, ev.target.value)}
                        >
                          <option value="">{t('app.fleet.rotation.none', { defaultValue: '—' })}</option>
                          {workModels.map((wm) => (
                            <option key={wm.id} value={wm.id}>
                              {wm.name}
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          className="btn text-red-700 hover:underline disabled:opacity-50"
                          onClick={() => void removeLineVehicle(m)}
                          disabled={removingVehicleId === m.id}
                        >
                          {t('app.fleet.rotation.remove', { defaultValue: 'Remove' })}
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="space-y-3">
              <h3 className="font-medium text-slate-900">{t('app.fleet.rotation.drivers_on_line', { defaultValue: 'Drivers on line' })}</h3>
              <form onSubmit={handleAddDriver} className="flex flex-col gap-2 rounded border border-slate-200 bg-slate-50/80 p-3">
                <div className="flex flex-wrap items-end gap-2">
                  <label className="flex min-w-hf-160 flex-1 flex-col gap-1 text-xs">
                    <span>{t('app.fleet.rotation.add_driver', { defaultValue: 'Add driver' })}</span>
                    <select
                      className="input rounded border border-slate-300 px-2 py-1.5 text-sm"
                      value={addDriverId}
                      onChange={(ev) => setAddDriverId(ev.target.value)}
                      disabled={addingDriver || driversToAdd.length === 0}
                    >
                      <option value="">{t('app.fleet.rotation.pick_driver', { defaultValue: 'Select driver…' })}</option>
                      {driversToAdd.map((d) => (
                        <option key={d.id} value={d.id}>
                          {driverOptionLabel(d)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex min-w-hf-160 flex-col gap-1 text-xs">
                    <span>{t('app.fleet.rotation.work_model', { defaultValue: 'Work model' })}</span>
                    {wmSelect(addDriverWm, setAddDriverWm, false)}
                  </label>
                </div>
                <div className="flex flex-wrap items-end gap-2">
                  <label className="flex flex-col gap-1 text-xs">
                    <span>{t('app.fleet.rotation.effective_from', { defaultValue: 'Effective from' })}</span>
                    <input
                      type="date"
                      className="input rounded border border-slate-300 px-2 py-1 text-sm"
                      value={addDriverFrom}
                      onChange={(ev) => setAddDriverFrom(ev.target.value)}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs">
                    <span>{t('app.fleet.rotation.effective_to', { defaultValue: 'Effective to' })}</span>
                    <input
                      type="date"
                      className="input rounded border border-slate-300 px-2 py-1 text-sm"
                      value={addDriverTo}
                      onChange={(ev) => setAddDriverTo(ev.target.value)}
                    />
                  </label>
                  <button
                    type="submit"
                    className="btn rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50"
                    disabled={addingDriver || !addDriverId || !addDriverWm}
                  >
                    {t('app.fleet.park.add', { defaultValue: 'Add' })}
                  </button>
                </div>
              </form>
              {lineDrivers.length === 0 ? (
                <p className="text-sm text-slate-600">{t('app.fleet.rotation.drivers_empty', { defaultValue: 'No drivers on this line.' })}</p>
              ) : (
                <ul className="space-y-3">
                  {lineDrivers.map((m) => {
                    const draft = driverDrafts[m.id]
                    return (
                      <li key={m.id} className="rounded border border-slate-100 bg-white p-3 text-sm">
                        <div className="mb-2 font-medium text-slate-900">{m.driver_label}</div>
                        <div className="flex flex-wrap items-end gap-2">
                          <label className="flex min-w-hf-140 flex-col gap-1 text-xs">
                            <span>{t('app.fleet.rotation.work_model', { defaultValue: 'Work model' })}</span>
                            <select
                              className="input rounded border border-slate-300 px-2 py-1 text-xs"
                              value={draft?.work_model_id ?? m.work_model_id}
                              onChange={(ev) =>
                                setDriverDrafts((prev) => ({
                                  ...prev,
                                  [m.id]: {
                                    work_model_id: ev.target.value,
                                    effective_from: prev[m.id]?.effective_from ?? m.effective_from?.slice(0, 10) ?? '',
                                    effective_to: prev[m.id]?.effective_to ?? m.effective_to?.slice(0, 10) ?? '',
                                  },
                                }))
                              }
                            >
                              {workModels.map((wm) => (
                                <option key={wm.id} value={wm.id}>
                                  {wm.name}
                                </option>
                              ))}
                            </select>
                          </label>
                          <label className="flex flex-col gap-1 text-xs">
                            <span>{t('app.fleet.rotation.effective_from', { defaultValue: 'Effective from' })}</span>
                            <input
                              type="date"
                              className="input rounded border border-slate-300 px-2 py-1 text-xs"
                              value={draft?.effective_from ?? ''}
                              onChange={(ev) =>
                                setDriverDrafts((prev) => ({
                                  ...prev,
                                  [m.id]: {
                                    work_model_id: prev[m.id]?.work_model_id ?? m.work_model_id,
                                    effective_from: ev.target.value,
                                    effective_to: prev[m.id]?.effective_to ?? m.effective_to?.slice(0, 10) ?? '',
                                  },
                                }))
                              }
                            />
                          </label>
                          <label className="flex flex-col gap-1 text-xs">
                            <span>{t('app.fleet.rotation.effective_to', { defaultValue: 'Effective to' })}</span>
                            <input
                              type="date"
                              className="input rounded border border-slate-300 px-2 py-1 text-xs"
                              value={draft?.effective_to ?? ''}
                              onChange={(ev) =>
                                setDriverDrafts((prev) => ({
                                  ...prev,
                                  [m.id]: {
                                    work_model_id: prev[m.id]?.work_model_id ?? m.work_model_id,
                                    effective_from: prev[m.id]?.effective_from ?? m.effective_from?.slice(0, 10) ?? '',
                                    effective_to: ev.target.value,
                                  },
                                }))
                              }
                            />
                          </label>
                          <button
                            type="button"
                            className="btn rounded bg-blue-600 px-2 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                            onClick={() => void saveDriverRow(m.id)}
                            disabled={driverSavingId === m.id}
                          >
                            {t('common.actions.save', { defaultValue: 'Save' })}
                          </button>
                          <button
                            type="button"
                            className="btn text-red-700 hover:underline disabled:opacity-50"
                            onClick={() => void removeLineDriver(m)}
                            disabled={removingDriverId === m.id}
                          >
                            {t('app.fleet.rotation.remove', { defaultValue: 'Remove' })}
                          </button>
                        </div>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
