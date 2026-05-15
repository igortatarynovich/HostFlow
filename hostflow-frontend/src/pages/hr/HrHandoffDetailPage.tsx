import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { fetchHandoffSnapshot } from '../../api/hrWorkspace'
import { useI18n } from '../../i18n'

export default function HrHandoffDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { t } = useI18n()
  const [snap, setSnap] = useState<any>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setErr(null)
    try {
      const d = await fetchHandoffSnapshot(id)
      setSnap(d)
    } catch (e: any) {
      setErr(e?.response?.data?.detail || e?.message || t('common.errors.request_failed'))
    } finally {
      setLoading(false)
    }
  }, [id, t])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Link to={CRM_APP_PATHS.hrInbox} className="text-sm font-medium text-brand-700 hover:text-brand-900">
          ← {t('app.nav.hr.handoff.back_inbox', { defaultValue: 'Back to inbox' })}
        </Link>
      </div>
      <h2 className="text-base font-semibold text-slate-900">
        {t('app.nav.hr.handoff.title', { defaultValue: 'Handoff snapshot' })} · {id}
      </h2>
      <p className="text-sm text-slate-600">
        {t('app.nav.hr.handoff.hint', {
          defaultValue: 'Read-only payload from GET /api/v1/handoffs/{id}/snapshot. No Candidates list API.',
        })}
      </p>
      {loading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
      {err && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{err}</div>
      )}
      {snap && !loading && (
        <pre className="max-h-[60vh] overflow-auto rounded-lg border border-slate-200 bg-slate-900 p-4 text-xs text-slate-100">
          {JSON.stringify(snap, null, 2)}
        </pre>
      )}
    </div>
  )
}
