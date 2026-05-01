import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  createFleetOperatingLine,
  deleteFleetOperatingLine,
  listFleetOperatingLines,
  patchFleetOperatingLine,
  type FleetOperatingLine,
} from '../../api/fleet'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

type Props = {
  preview?: boolean
}

export default function FleetOperatingLinesSection({ preview }: Props) {
  const { t } = useI18n()
  const [items, setItems] = useState<FleetOperatingLine[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editStatus, setEditStatus] = useState('active')
  const [savingId, setSavingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const load = useCallback(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    listFleetOperatingLines()
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
  }, [])

  useEffect(() => {
    const cleanup = load()
    return cleanup
  }, [load, reloadKey])

  const title = t('app.fleet.operating_lines.title', { defaultValue: 'Operating lines' })

  function beginEdit(row: FleetOperatingLine) {
    if (preview) return
    setEditingId(row.id)
    setEditName(row.name)
    setEditStatus(row.status || 'active')
  }

  function cancelEdit() {
    setEditingId(null)
  }

  async function saveEdit() {
    if (!editingId || preview) return
    const name = editName.trim()
    if (!name) return
    setSavingId(editingId)
    setError(null)
    try {
      await patchFleetOperatingLine(editingId, { name, status: editStatus })
      setEditingId(null)
      setReloadKey((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setSavingId(null)
    }
  }

  async function removeLine(id: string) {
    if (preview) return
    const ok = window.confirm(
      t('app.fleet.operating_lines.delete_confirm', { defaultValue: 'Delete this operating line?' }),
    )
    if (!ok) return
    setDeletingId(id)
    setError(null)
    try {
      await deleteFleetOperatingLine(id)
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

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    const name = newName.trim()
    if (!name || preview) return
    setCreating(true)
    setError(null)
    try {
      await createFleetOperatingLine({ name })
      setNewName('')
      setReloadKey((k) => k + 1)
    } catch (err) {
      setError(getFriendlyErrorInfo(err))
    } finally {
      setCreating(false)
    }
  }

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      {!preview && (
        <form onSubmit={handleCreate} className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <label className="flex min-w-[200px] flex-1 flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">
              {t('app.fleet.operating_lines.new_name', { defaultValue: 'Line name' })}
            </span>
            <input
              className="rounded border border-slate-300 px-3 py-2 text-slate-900"
              value={newName}
              onChange={(ev) => setNewName(ev.target.value)}
              maxLength={255}
              disabled={creating}
            />
          </label>
          <button
            type="submit"
            disabled={creating || !newName.trim()}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {t('app.fleet.operating_lines.create', { defaultValue: 'Add line' })}
          </button>
        </form>
      )}
      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
      ) : displayItems.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-600">
          {t('app.fleet.operating_lines.empty', { defaultValue: 'No operating lines yet.' })}
        </p>
      ) : (
        <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white">
          {displayItems.map((row) => (
            <li key={row.id} className="px-4 py-3 text-sm">
              {editingId === row.id && !preview ? (
                <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                  <label className="flex min-w-[180px] flex-1 flex-col gap-1">
                    <span className="text-xs font-medium text-slate-600">
                      {t('app.fleet.operating_lines.edit_name', { defaultValue: 'Name' })}
                    </span>
                    <input
                      className="rounded border border-slate-300 px-2 py-1.5 text-slate-900"
                      value={editName}
                      onChange={(ev) => setEditName(ev.target.value)}
                      maxLength={255}
                      disabled={savingId === row.id}
                    />
                  </label>
                  <label className="flex w-full flex-col gap-1 sm:w-40">
                    <span className="text-xs font-medium text-slate-600">
                      {t('app.fleet.operating_lines.edit_status', { defaultValue: 'Status' })}
                    </span>
                    <select
                      className="rounded border border-slate-300 px-2 py-1.5 text-slate-900"
                      value={editStatus}
                      onChange={(ev) => setEditStatus(ev.target.value)}
                      disabled={savingId === row.id}
                    >
                      <option value="active">{t('app.fleet.operating_lines.status_active', { defaultValue: 'active' })}</option>
                      <option value="inactive">{t('app.fleet.operating_lines.status_inactive', { defaultValue: 'inactive' })}</option>
                    </select>
                  </label>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
                      disabled={savingId === row.id || !editName.trim()}
                      onClick={() => void saveEdit()}
                    >
                      {t('common.save', { defaultValue: 'Save' })}
                    </button>
                    <button
                      type="button"
                      className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700"
                      disabled={savingId === row.id}
                      onClick={cancelEdit}
                    >
                      {t('common.cancel', { defaultValue: 'Cancel' })}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <span className="font-medium text-slate-900">{row.name}</span>
                    {row.status && row.status !== 'active' ? (
                      <span className="ml-2 rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{row.status}</span>
                    ) : null}
                  </div>
                  {!preview ? (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="text-xs font-medium text-blue-700 hover:underline"
                        disabled={deletingId === row.id}
                        onClick={() => beginEdit(row)}
                      >
                        {t('common.edit', { defaultValue: 'Edit' })}
                      </button>
                      <button
                        type="button"
                        className="text-xs font-medium text-red-600 hover:underline"
                        disabled={deletingId === row.id}
                        onClick={() => void removeLine(row.id)}
                      >
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
