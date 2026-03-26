import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconRefresh, IconSearch } from '@tabler/icons-react'

import { createReminder, listCandidatesNoNextAction } from '../api/client'
import { useI18n } from '../i18n'
import { useToast } from '../components/Toast'
import { CRM_APP_PATHS } from '../app/crmAppPaths'

type NoNextActionCandidate = {
  id: string
  short_id?: string | null
  first_name?: string | null
  last_name?: string | null
  stage?: string | null
  manager?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export default function CandidatesNoNextActionPage() {
  const { t } = useI18n()
  const { notify } = useToast()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [items, setItems] = useState<NoNextActionCandidate[]>([])
  const [q, setQ] = useState('')
  const [creatingForId, setCreatingForId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listCandidatesNoNextAction({ limit: 200, offset: 0 })
      const list = Array.isArray(res?.items) ? (res.items as NoNextActionCandidate[]) : []
      setItems(list)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? err?.message ?? t('common.errors.unknown'))
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  const filtered = useMemo(() => {
    const needle = (q || '').trim().toLowerCase()
    if (!needle) return items
    return items.filter((c) => {
      const label = `${c.short_id || ''} ${c.first_name || ''} ${c.last_name || ''}`.trim().toLowerCase()
      return label.includes(needle) || String(c.id || '').toLowerCase().includes(needle)
    })
  }, [items, q])

  const handleCreateFollowUp = useCallback(
    async (candidateId: string) => {
      setCreatingForId(candidateId)
      try {
        const due = new Date(Date.now() + 24 * 60 * 60 * 1000)
        const remindAt = new Date(due.getTime() - 15 * 60 * 1000)
        await createReminder({
          title: t('app.candidates.no_next_action.default_title'),
          description: '',
          type: 'custom',
          entity_type: 'candidate',
          entity_id: candidateId,
          due_at: due.toISOString(),
          remind_at: remindAt.toISOString(),
          priority: 'normal',
        })
        notify({ title: t('app.reminders.messages.created'), variant: 'success' })
        await load()
      } catch (err: any) {
        const detail = err?.response?.data?.detail ?? err?.message ?? t('app.reminders.errors.create')
        notify({ title: typeof detail === 'string' ? detail : t('app.reminders.errors.create'), variant: 'error' })
      } finally {
        setCreatingForId(null)
      }
    },
    [load, notify, t],
  )

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col space-y-0 gap-0">
      <header className="rounded-none border-x-0 border-t-0 border-b border-slate-200 bg-white px-3 py-2.5 shadow-none">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">
              {t('app.candidates.no_next_action.title')}
            </h1>
            <p className="text-xs text-slate-500">
              {t('app.candidates.no_next_action.subtitle')}
            </p>
          </div>
          <button type="button" className="btn-secondary h-9 rounded-lg px-3 text-xs" onClick={() => void load()} disabled={loading}>
            <IconRefresh size={14} />
            {t('common.actions.refresh')}
          </button>
        </div>

        <div className="mt-3 flex flex-wrap items-end gap-2">
          <label className="min-w-[260px] text-xs font-medium text-slate-600">
            <span className="mb-1 inline-flex items-center gap-1">
              <IconSearch size={12} />
              {t('common.search')}
            </span>
            <input
              className="input h-9 w-full rounded-lg border-slate-300 bg-white px-2.5 py-1.5 text-sm"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t('app.candidates.no_next_action.search_placeholder')}
            />
          </label>
        </div>
      </header>

      <section className="overflow-hidden rounded-none border-x-0 border-t-0 border-b border-slate-200 bg-white shadow-none">
        {error ? <div className="border-b border-slate-200 p-3 text-sm text-red-600">{error}</div> : null}
        <div className="overflow-x-auto">
          <table className="table min-w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th>{t('app.candidates.no_next_action.columns.candidate')}</th>
                <th>{t('app.candidates.no_next_action.columns.stage')}</th>
                <th>{t('app.candidates.no_next_action.columns.updated')}</th>
                <th className="text-right">{t('common.actions.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-slate-500">
                    {t('common.loading')}
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-slate-500">
                    {t('app.candidates.no_next_action.empty')}
                  </td>
                </tr>
              ) : (
                filtered.map((c) => {
                  const label =
                    `${c.first_name || ''} ${c.last_name || ''}`.trim() ||
                    (c.short_id ? `ID ${c.short_id}` : c.id.slice(0, 8))
                  return (
                    <tr key={c.id} className="hover:bg-slate-50">
                      <td className="text-slate-900">
                        <Link
                          className="font-medium text-brand-600 hover:text-brand-700 hover:underline"
                          to={`${CRM_APP_PATHS.candidates}/${c.id}`}
                        >
                          {label}
                        </Link>
                        <div className="text-xs text-slate-500">{c.short_id ? `ID ${c.short_id}` : `ID ${c.id.slice(0, 8)}`}</div>
                      </td>
                      <td className="text-slate-700">{c.stage || '—'}</td>
                      <td className="text-slate-600">{c.updated_at || c.created_at || '—'}</td>
                      <td className="text-right">
                        <button
                          type="button"
                          className="btn-primary btn-xs"
                          disabled={creatingForId === c.id}
                          onClick={() => void handleCreateFollowUp(c.id)}
                        >
                          {creatingForId === c.id ? t('common.loading') : t('app.candidates.no_next_action.actions.add_next')}
                        </button>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

