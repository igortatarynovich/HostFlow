import { useCallback, useEffect, useMemo, useState } from 'react'
import { Modal } from '../Modal'
import { useI18n } from '../../i18n'
import { formatDateSafe } from '../../modules/candidates/candidateUtils'
import { getCandidateChangeLog } from '../../api/client'

type ChangeLogItem = {
  at: string
  actor_id?: string | null
  actor_name?: string | null
  action: string
  payload?: any
}

export default function CandidateChangeLogModal({
  open,
  onClose,
  candidateId,
  locale,
}: {
  open: boolean
  onClose: () => void
  candidateId: string
  locale: string
}) {
  const { t } = useI18n()
  const [loading, setLoading] = useState(false)
  const [errorText, setErrorText] = useState<string | null>(null)
  const [items, setItems] = useState<ChangeLogItem[]>([])

  const load = useCallback(async () => {
    if (!candidateId) return
    setLoading(true)
    setErrorText(null)
    try {
      const data = await getCandidateChangeLog(candidateId, { limit: 200 })
      const raw = Array.isArray(data?.items) ? data.items : []
      setItems(raw)
    } catch (err: any) {
      setErrorText(err?.response?.data?.detail ?? err?.message ?? 'Request failed')
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [candidateId])

  useEffect(() => {
    if (!open) return
    void load()
  }, [open, load])

  const title = useMemo(
    () => t('app.candidate_card.change_log.title', { defaultValue: 'Change log' }),
    [t],
  )

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <div className="space-y-3">
        {loading ? <div className="text-sm text-slate-500">{t('common.loading')}</div> : null}
        {errorText ? <div className="text-sm text-red-600">{errorText}</div> : null}

        {!loading && !errorText && items.length === 0 ? (
          <div className="text-sm text-slate-500">
            {t('app.candidate_card.change_log.empty', { defaultValue: 'No changes yet.' })}
          </div>
        ) : null}

        <div className="max-h-[70vh] overflow-auto rounded-xl border border-slate-200 bg-white">
          <div className="divide-y divide-slate-200">
            {items.map((it, idx) => {
              const at = (it as any)?.at || ''
              const payload = (it as any)?.payload || {}
              const keys: string[] = Array.isArray(payload?.changed_keys) ? payload.changed_keys : []
              const actor = (it as any)?.actor_name || (it as any)?.actor_id || t('common.labels.not_available')
              const when = formatDateSafe(at, locale) || at
              return (
                <div key={`${at}-${idx}`} className="p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-slate-900 truncate">{actor}</div>
                      <div className="mt-0.5 text-xs text-slate-600">
                        {keys.length
                          ? t('app.candidate_card.change_log.changed', {
                              defaultValue: 'Changed: {keys}',
                              values: { keys: keys.slice(0, 12).join(', ') + (keys.length > 12 ? '…' : '') },
                            })
                          : t('app.candidate_card.change_log.updated', { defaultValue: 'Updated candidate' })}
                      </div>
                    </div>
                    <div className="shrink-0 text-[11px] text-slate-500" title={at}>
                      {when}
                    </div>
                  </div>

                  {Array.isArray(payload?.diff) && payload.diff.length ? (
                    <details className="mt-2">
                      <summary className="cursor-pointer text-xs text-slate-600 hover:text-slate-800">
                        {t('app.candidate_card.change_log.details', { defaultValue: 'Details' })}
                      </summary>
                      <div className="mt-2 space-y-1">
                        {payload.diff.slice(0, 40).map((d: any, j: number) => (
                          <div key={`${d?.field ?? 'field'}-${j}`} className="text-xs text-slate-700">
                            <span className="font-mono text-slate-500">{String(d?.field || 'field')}</span>
                            {d?.changed_keys_count ? (
                              <span className="ml-2 text-slate-600">
                                {t('app.candidate_card.change_log.diff_keys', {
                                  defaultValue: '{n} keys changed',
                                  values: { n: Number(d.changed_keys_count) || 0 },
                                })}
                              </span>
                            ) : (
                              <span className="ml-2 text-slate-600">
                                {String(d?.from ?? '—')} → {String(d?.to ?? '—')}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </details>
                  ) : null}
                </div>
              )
            })}
          </div>
        </div>

        <div className="flex justify-end">
          <button type="button" className="btn-secondary" onClick={onClose}>
            {t('common.actions.close')}
          </button>
        </div>
      </div>
    </Modal>
  )
}

