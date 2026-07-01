import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  createFleetDriver,
  createFleetTrailer,
  createFleetVehicle,
  deleteFleetDriver,
  deleteFleetTrailer,
  deleteFleetVehicle,
  listFleetDrivers,
  listFleetTrailers,
  listFleetVehicles,
  patchFleetDriver,
  patchFleetTrailer,
  patchFleetVehicle,
  type FleetDriver,
  type FleetTrailer,
  type FleetVehicle,
} from '../../api/fleet'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

export type FleetParkKind = 'vehicles' | 'trailers' | 'drivers'

type Props = {
  kind: FleetParkKind
  /** When true, show a short read-only sample (no create/edit/delete). */
  preview?: boolean
}

type Row = FleetVehicle | FleetTrailer | FleetDriver

function rowLabel(kind: FleetParkKind, row: Row): string {
  if (kind === 'vehicles') {
    const v = row as FleetVehicle
    return (
      v.internal_code ||
      v.registration_plate ||
      [v.brand, v.model].filter(Boolean).join(' ') ||
      v.id.slice(0, 8)
    )
  }
  if (kind === 'trailers') {
    const t = row as FleetTrailer
    return t.internal_code || t.registration_plate || t.trailer_type || t.id.slice(0, 8)
  }
  const d = row as FleetDriver
  return d.display_code || [d.first_name, d.last_name].filter(Boolean).join(' ') || d.id.slice(0, 8)
}

export default function FleetParkSection({ kind, preview = false }: Props) {
  const { t } = useI18n()
  const [items, setItems] = useState<Row[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const titleKey =
    kind === 'vehicles'
      ? 'app.fleet.park.vehicles_title'
      : kind === 'trailers'
        ? 'app.fleet.park.trailers_title'
        : 'app.fleet.park.drivers_title'
  const titleDefault = kind === 'vehicles' ? 'Tractors' : kind === 'trailers' ? 'Trailers' : 'Drivers'

  const load = useCallback(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    const p =
      kind === 'vehicles'
        ? listFleetVehicles().then((r) => r.items as Row[])
        : kind === 'trailers'
          ? listFleetTrailers().then((r) => r.items as Row[])
          : listFleetDrivers().then((r) => r.items as Row[])
    p.then((rows) => {
      if (!cancelled) setItems(rows)
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
  }, [kind])

  useEffect(() => {
    return load()
  }, [load, reloadKey])

  const title = t(titleKey, { defaultValue: titleDefault })

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    if (preview) return
    const fd = new FormData(e.currentTarget as HTMLFormElement)
    setSaving(true)
    setError(null)
    try {
      if (kind === 'vehicles') {
        await createFleetVehicle({
          internal_code: (fd.get('internal_code') as string) || undefined,
          registration_plate: (fd.get('registration_plate') as string) || undefined,
          brand: (fd.get('brand') as string) || undefined,
          model: (fd.get('model') as string) || undefined,
        })
      } else if (kind === 'trailers') {
        await createFleetTrailer({
          internal_code: (fd.get('internal_code') as string) || undefined,
          registration_plate: (fd.get('registration_plate') as string) || undefined,
          trailer_type: (fd.get('trailer_type') as string) || undefined,
        })
      } else {
        await createFleetDriver({
          display_code: (fd.get('display_code') as string) || undefined,
          last_name: (fd.get('last_name') as string) || undefined,
          first_name: (fd.get('first_name') as string) || undefined,
        })
      }
      ;(e.currentTarget as HTMLFormElement).reset()
      setReloadKey((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setSaving(false)
    }
  }

  async function saveEdit(row: Row) {
    if (preview) return
    const fd = new FormData(document.getElementById(`edit-form-${row.id}`) as HTMLFormElement)
    setSaving(true)
    setError(null)
    try {
      if (kind === 'vehicles') {
        await patchFleetVehicle(row.id, {
          internal_code: (fd.get('internal_code') as string) || undefined,
          registration_plate: (fd.get('registration_plate') as string) || undefined,
          brand: (fd.get('brand') as string) || undefined,
          model: (fd.get('model') as string) || undefined,
          status: (fd.get('status') as string) || undefined,
        })
      } else if (kind === 'trailers') {
        await patchFleetTrailer(row.id, {
          internal_code: (fd.get('internal_code') as string) || undefined,
          registration_plate: (fd.get('registration_plate') as string) || undefined,
          trailer_type: (fd.get('trailer_type') as string) || undefined,
          status: (fd.get('status') as string) || undefined,
        })
      } else {
        await patchFleetDriver(row.id, {
          display_code: (fd.get('display_code') as string) || undefined,
          first_name: (fd.get('first_name') as string) || undefined,
          last_name: (fd.get('last_name') as string) || undefined,
          status: (fd.get('status') as string) || undefined,
        })
      }
      setEditingId(null)
      setReloadKey((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setSaving(false)
    }
  }

  async function remove(id: string) {
    if (preview) return
    if (!window.confirm(t('app.fleet.park.delete_confirm', { defaultValue: 'Delete this record?' }))) return
    setDeletingId(id)
    setError(null)
    try {
      if (kind === 'vehicles') await deleteFleetVehicle(id)
      else if (kind === 'trailers') await deleteFleetTrailer(id)
      else await deleteFleetDriver(id)
      if (editingId === id) setEditingId(null)
      setReloadKey((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setDeletingId(null)
    }
  }

  if (error) {
    return (
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <ErrorRecoveryBanner
          primary={error.title}
          secondary={friendlyErrorBannerSecondary(error)}
          onRetry={() => window.location.reload()}
        />
      </section>
    )
  }

  const displayItems = preview ? items.slice(0, 5) : items

  return (
    <section className="space-y-6">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>

      {!preview ? (
      <form onSubmit={handleCreate} className="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 sm:grid-cols-2 lg:grid-cols-4">
        {kind === 'vehicles' ? (
          <>
            <Field name="internal_code" label={t('app.fleet.park.field_internal', { defaultValue: 'Internal #' })} disabled={saving} />
            <Field name="registration_plate" label={t('app.fleet.park.field_plate', { defaultValue: 'Plate' })} disabled={saving} />
            <Field name="brand" label={t('app.fleet.park.field_brand', { defaultValue: 'Brand' })} disabled={saving} />
            <Field name="model" label={t('app.fleet.park.field_model', { defaultValue: 'Model' })} disabled={saving} />
          </>
        ) : kind === 'trailers' ? (
          <>
            <Field name="internal_code" label={t('app.fleet.park.field_internal', { defaultValue: 'Internal #' })} disabled={saving} />
            <Field name="registration_plate" label={t('app.fleet.park.field_plate', { defaultValue: 'Plate' })} disabled={saving} />
            <Field name="trailer_type" label={t('app.fleet.park.field_trailer_type', { defaultValue: 'Type' })} disabled={saving} />
          </>
        ) : (
          <>
            <Field name="display_code" label={t('app.fleet.park.field_driver_code', { defaultValue: 'Code' })} disabled={saving} />
            <Field name="last_name" label={t('app.fleet.park.field_last_name', { defaultValue: 'Last name' })} disabled={saving} />
            <Field name="first_name" label={t('app.fleet.park.field_first_name', { defaultValue: 'First name' })} disabled={saving} />
          </>
        )}
        <div className="flex items-end">
          <button
            type="submit"
            disabled={saving}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {t('app.fleet.park.add', { defaultValue: 'Add' })}
          </button>
        </div>
      </form>
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
      ) : displayItems.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-600">
          {t('app.fleet.park.empty', { defaultValue: 'No records yet.' })}
        </p>
      ) : (
        <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white">
          {displayItems.map((row) => (
            <li key={row.id} className="px-4 py-3 text-sm">
              {editingId === row.id && !preview ? (
                <form
                  id={`edit-form-${row.id}`}
                  className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
                  onSubmit={(e) => {
                    e.preventDefault()
                    void saveEdit(row)
                  }}
                >
                  {kind === 'vehicles' ? (
                    <>
                      <Field name="internal_code" label={t('app.fleet.park.field_internal', { defaultValue: 'Internal #' })} defaultValue={(row as FleetVehicle).internal_code ?? ''} disabled={saving} />
                      <Field name="registration_plate" label={t('app.fleet.park.field_plate', { defaultValue: 'Plate' })} defaultValue={(row as FleetVehicle).registration_plate ?? ''} disabled={saving} />
                      <Field name="brand" label={t('app.fleet.park.field_brand', { defaultValue: 'Brand' })} defaultValue={(row as FleetVehicle).brand ?? ''} disabled={saving} />
                      <Field name="model" label={t('app.fleet.park.field_model', { defaultValue: 'Model' })} defaultValue={(row as FleetVehicle).model ?? ''} disabled={saving} />
                      <StatusSelect defaultValue={(row as FleetVehicle).status || 'active'} disabled={saving} />
                    </>
                  ) : kind === 'trailers' ? (
                    <>
                      <Field name="internal_code" label={t('app.fleet.park.field_internal', { defaultValue: 'Internal #' })} defaultValue={(row as FleetTrailer).internal_code ?? ''} disabled={saving} />
                      <Field name="registration_plate" label={t('app.fleet.park.field_plate', { defaultValue: 'Plate' })} defaultValue={(row as FleetTrailer).registration_plate ?? ''} disabled={saving} />
                      <Field name="trailer_type" label={t('app.fleet.park.field_trailer_type', { defaultValue: 'Type' })} defaultValue={(row as FleetTrailer).trailer_type ?? ''} disabled={saving} />
                      <StatusSelect defaultValue={(row as FleetTrailer).status || 'active'} disabled={saving} />
                    </>
                  ) : (
                    <>
                      <Field name="display_code" label={t('app.fleet.park.field_driver_code', { defaultValue: 'Code' })} defaultValue={(row as FleetDriver).display_code ?? ''} disabled={saving} />
                      <Field name="last_name" label={t('app.fleet.park.field_last_name', { defaultValue: 'Last name' })} defaultValue={(row as FleetDriver).last_name ?? ''} disabled={saving} />
                      <Field name="first_name" label={t('app.fleet.park.field_first_name', { defaultValue: 'First name' })} defaultValue={(row as FleetDriver).first_name ?? ''} disabled={saving} />
                      <StatusSelect defaultValue={(row as FleetDriver).status || 'active'} disabled={saving} />
                    </>
                  )}
                  <div className="flex flex-wrap gap-2 sm:col-span-2 lg:col-span-4">
                    <button type="submit" disabled={saving} className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">
                      {t('common.save', { defaultValue: 'Save' })}
                    </button>
                    <button type="button" disabled={saving} className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700" onClick={() => setEditingId(null)}>
                      {t('common.cancel', { defaultValue: 'Cancel' })}
                    </button>
                  </div>
                </form>
              ) : (
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-slate-900">{rowLabel(kind, row)}</span>
                  {!preview ? (
                    <div className="flex gap-2">
                      <button type="button" className="text-xs font-medium text-blue-700 hover:underline" disabled={deletingId === row.id} onClick={() => setEditingId(row.id)}>
                        {t('common.edit', { defaultValue: 'Edit' })}
                      </button>
                      <button type="button" className="text-xs font-medium text-red-600 hover:underline" disabled={deletingId === row.id} onClick={() => void remove(row.id)}>
                        {t('common.delete', { defaultValue: 'Delete' })}
                      </button>
                    </div>
                  ) : null}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function Field({
  name,
  label,
  defaultValue,
  disabled,
}: {
  name: string
  label: string
  defaultValue?: string
  disabled?: boolean
}) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="font-medium text-slate-600">{label}</span>
      <input name={name} defaultValue={defaultValue} disabled={disabled} className="rounded border border-slate-300 px-2 py-1.5 text-slate-900" />
    </label>
  )
}

function StatusSelect({ defaultValue, disabled }: { defaultValue: string; disabled?: boolean }) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="font-medium text-slate-600">Status</span>
      <select name="status" defaultValue={defaultValue} disabled={disabled} className="rounded border border-slate-300 px-2 py-1.5 text-slate-900">
        <option value="active">active</option>
        <option value="inactive">inactive</option>
        <option value="maintenance">maintenance</option>
      </select>
    </label>
  )
}
