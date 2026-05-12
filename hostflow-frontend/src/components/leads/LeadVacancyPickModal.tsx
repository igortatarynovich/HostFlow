import { useCallback, useEffect, useState } from 'react'

import { listVacancies } from '../../api/client'
import { useI18n } from '../../i18n'

type Props = {
  open: boolean
  onClose: () => void
  onConfirm: (vacancyId: string, thenProcess: boolean) => void | Promise<void>
  confirming?: boolean
}

export default function LeadVacancyPickModal({ open, onClose, onConfirm, confirming }: Props) {
  const { t } = useI18n()
  const [vacancies, setVacancies] = useState<Array<{ id: string; title: string }>>([])
  const [loading, setLoading] = useState(false)
  const [selectedId, setSelectedId] = useState('')
  const [thenProcess, setThenProcess] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await listVacancies({ limit: 200, offset: 0 })
      const rows = Array.isArray(res?.items) ? res.items : Array.isArray(res) ? res : []
      setVacancies(
        rows
          .map((row: { id?: string; title?: string; vacancy_title?: string }) => ({
            id: String(row?.id ?? ''),
            title: String(row?.title ?? row?.vacancy_title ?? row?.id ?? ''),
          }))
          .filter((x) => x.id),
      )
    } catch {
      setVacancies([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!open) return
    setSelectedId('')
    setThenProcess(true)
    void load()
  }, [open, load])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="presentation"
      onClick={() => {
        if (!confirming) onClose()
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="lead-vacancy-pick-title"
        className="max-h-[90vh] w-full max-w-md overflow-auto rounded-2xl bg-white p-5 shadow-2xl shadow-slate-900/15 ring-1 ring-slate-900/[0.06] sm:p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="lead-vacancy-pick-title" className="text-lg font-semibold tracking-tight text-slate-900">
          {t('app.leads.routing.pick_modal_title')}
        </h2>
        <p className="mt-1 text-xs text-slate-600">{t('app.leads.routing.pick_modal_hint')}</p>

        <label className="mt-4 flex flex-col gap-1 text-xs text-slate-600">
          <span>{t('app.leads.detail.intake_resolution.select_label')}</span>
          <select
            className="input h-10 rounded-lg border-slate-300 bg-white px-2 text-sm"
            value={selectedId}
            disabled={loading || confirming}
            onChange={(e) => setSelectedId(e.target.value)}
          >
            <option value="">{loading ? t('common.loading') : t('app.leads.detail.intake_resolution.select_placeholder')}</option>
            {vacancies.map((v) => (
              <option key={v.id} value={v.id}>
                {v.title || v.id}
              </option>
            ))}
          </select>
        </label>

        <label className="mt-3 flex cursor-pointer items-center gap-2 text-xs text-slate-700">
          <input
            type="checkbox"
            className="rounded border-slate-300"
            checked={thenProcess}
            disabled={Boolean(confirming)}
            onChange={(e) => setThenProcess(e.target.checked)}
          />
          <span>{t('app.leads.routing.confirm_then_process')}</span>
        </label>

        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            className="btn-secondary h-9 rounded-lg px-3 text-sm"
            disabled={Boolean(confirming)}
            onClick={onClose}
          >
            {t('common.actions.cancel')}
          </button>
          <button
            type="button"
            className="btn-primary h-9 rounded-lg px-3 text-sm disabled:opacity-50"
            disabled={!selectedId.trim() || Boolean(confirming)}
            onClick={() => void onConfirm(selectedId.trim(), thenProcess)}
          >
            {confirming ? t('common.loading') : t('app.leads.routing.pick_modal_confirm')}
          </button>
        </div>
      </div>
    </div>
  )
}
