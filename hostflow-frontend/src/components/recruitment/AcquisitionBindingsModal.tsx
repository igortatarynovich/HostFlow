import { useCallback, useEffect, useState } from 'react'
import { listVacancies, type Vacancy } from '../../api/vacancies'
import { useI18n } from '../../i18n'

type AcquisitionBindingsModalProps = {
  open: boolean
  currentSearchId: string
  selectedIds: string[]
  onClose: () => void
  onSave: (searchIds: string[]) => Promise<void>
}

function isLaunchSearch(row: Vacancy): boolean {
  try {
    const extra = typeof row.extra === 'string' ? JSON.parse(row.extra) : row.extra
    return Boolean(extra?.launch_search)
  } catch {
    return false
  }
}

export function AcquisitionBindingsModal({
  open,
  currentSearchId,
  selectedIds,
  onClose,
  onSave,
}: AcquisitionBindingsModalProps) {
  const { t } = useI18n()
  const [rows, setRows] = useState<Vacancy[]>([])
  const [picked, setPicked] = useState<string[]>(selectedIds)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const vacancies = await listVacancies({ limit: 100, order_by: 'updated_at', desc: true, is_archived: false })
      const launch = vacancies.filter(isLaunchSearch)
      setRows(launch.length > 0 ? launch : vacancies)
    } catch {
      setRows([])
    }
  }, [])

  useEffect(() => {
    if (open) {
      setPicked(selectedIds.length > 0 ? selectedIds : [currentSearchId])
      void load()
    }
  }, [currentSearchId, load, open, selectedIds])

  if (!open) return null

  function toggle(id: string) {
    setPicked((prev) => {
      if (prev.includes(id)) {
        if (id === currentSearchId) return prev
        return prev.filter((x) => x !== id)
      }
      return [...prev, id]
    })
  }

  async function handleSave() {
    setBusy(true)
    try {
      const ids = picked.includes(currentSearchId) ? picked : [currentSearchId, ...picked]
      await onSave(ids)
      onClose()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-5 shadow-xl">
        <h3 className="text-base font-semibold text-slate-900">
          {t('app.acquisition.bindings_title', { defaultValue: 'Привязка к подборам' })}
        </h3>
        <p className="mt-1 text-sm text-slate-600">
          {t('app.acquisition.bindings_hint', {
            defaultValue: 'Выберите подборы, на которые работает эта активность.',
          })}
        </p>
        <ul className="mt-4 max-h-64 space-y-2 overflow-y-auto">
          {rows.map((row) => {
            const id = String(row.id)
            const checked = picked.includes(id)
            const locked = id === currentSearchId
            return (
              <li key={id}>
                <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-100 px-3 py-2 hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={locked}
                    onChange={() => toggle(id)}
                  />
                  <span className="text-sm text-slate-800">{row.title || id}</span>
                  {locked ? (
                    <span className="ml-auto text-xs text-slate-400">
                      {t('app.acquisition.bindings_current', { defaultValue: 'текущий' })}
                    </span>
                  ) : null}
                </label>
              </li>
            )
          })}
        </ul>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {t('common.cancel', { defaultValue: 'Отмена' })}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void handleSave()}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {t('common.save', { defaultValue: 'Сохранить' })}
          </button>
        </div>
      </div>
    </div>
  )
}
