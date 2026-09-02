import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import clsx from 'clsx'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import { listDocuments } from '../../api/documents'
import {
  fetchHrDocumentsExpiring,
  fetchHrDocumentsMissing,
} from '../../api/hrWorkspace'

const DocumentsRegistryPage = lazy(() => import('../DocumentsRegistryPage'))

type HubTab = 'all' | 'missing' | 'expiring' | 'verification' | 'hr' | 'recruitment' | 'registry'

const TAB_KEYS: HubTab[] = ['all', 'missing', 'expiring', 'verification', 'hr', 'recruitment', 'registry']

function tabClass(active: boolean) {
  return clsx(
    'rounded-md px-2.5 py-1 text-xs font-medium transition',
    active ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
  )
}

export default function DocumentsHubPage() {
  const { t } = useI18n()
  const { can } = usePermissions()
  const canHrDocs = can('workforce.view')
  const canDocsManage = can('documents.manage')
  const [searchParams, setSearchParams] = useSearchParams()
  const hub = (searchParams.get('hub') || 'all').trim().toLowerCase()
  const active: HubTab = (TAB_KEYS as readonly string[]).includes(hub) ? (hub as HubTab) : 'all'

  const setHub = useCallback(
    (next: HubTab) => {
      const nextParams = new URLSearchParams(searchParams)
      if (next === 'all') nextParams.delete('hub')
      else nextParams.set('hub', next)
      setSearchParams(nextParams, { replace: true })
    },
    [searchParams, setSearchParams],
  )

  useEffect(() => {
    if (!canHrDocs || canDocsManage) return
    if (active !== 'all') return
    setHub('missing')
  }, [canHrDocs, canDocsManage, active, setHub])

  const [allDocs, setAllDocs] = useState<any[]>([])
  const [hrMissing, setHrMissing] = useState<any>(null)
  const [hrExpiring, setHrExpiring] = useState<any>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (active === 'registry') return
      setLoading(true)
      setErr(null)
      try {
        if (active === 'all' || active === 'recruitment') {
          const items = await listDocuments({ limit: 200 })
          if (!cancelled) setAllDocs(items || [])
        }
        if ((active === 'missing' || active === 'hr') && canHrDocs) {
          const m = await fetchHrDocumentsMissing({ assignee_scope: 'team', limit: 80, offset: 0 })
          if (!cancelled) setHrMissing(m)
        }
        if ((active === 'expiring' || active === 'hr') && canHrDocs) {
          const e = await fetchHrDocumentsExpiring({ assignee_scope: 'team', horizon_days: 30, limit: 80, offset: 0 })
          if (!cancelled) setHrExpiring(e)
        }
      } catch (e: any) {
        if (!cancelled) setErr(e?.response?.data?.detail || e?.message || t('common.errors.request_failed'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [active, canHrDocs, t])

  const tabLabel = useMemo(
    () => ({
      all: t('app.documents_hub.tabs.all', { defaultValue: 'All documents' }),
      missing: t('app.documents_hub.tabs.missing', { defaultValue: 'Missing' }),
      expiring: t('app.documents_hub.tabs.expiring', { defaultValue: 'Expiring' }),
      verification: t('app.documents_hub.tabs.verification', { defaultValue: 'Verification' }),
      hr: t('app.documents_hub.tabs.hr', { defaultValue: 'HR documents' }),
      recruitment: t('app.documents_hub.tabs.recruitment', { defaultValue: 'Recruitment documents' }),
      registry: t('app.documents_hub.tabs.registry', { defaultValue: 'Process registry' }),
    }),
    [t],
  )

  if (!canDocsManage && !canHrDocs) {
    return (
      <div className="p-6 text-sm text-slate-600">
        {t('common.access_denied')}
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-slate-50/80">
      <header className="border-b border-slate-200 bg-white px-3 py-2 lg:px-4">
        <div className="mx-auto max-w-7xl">
          <h1 className="text-lg font-semibold text-slate-900">
            {t('app.documents_hub.title', { defaultValue: 'Documents hub' })}
          </h1>
          <p className="mt-0.5 truncate text-xs text-slate-500">
            {t('app.documents_hub.subtitle', {
              defaultValue:
                'Unified read-first access. Ownership stays with recruitment, HR, or shared contexts — this screen only aggregates views.',
            })}
          </p>
          <nav className="mt-1.5 flex flex-wrap gap-0.5" aria-label={t('app.documents_hub.nav_aria', { defaultValue: 'Documents hub sections' })}>
            {TAB_KEYS.map((key) => {
              if ((key === 'missing' || key === 'expiring' || key === 'hr') && !canHrDocs) return null
              if (key === 'registry' && !canDocsManage) return null
              if ((key === 'all' || key === 'recruitment') && !canDocsManage) return null
              const isActive = active === key
              return (
                <button key={key} type="button" className={tabClass(isActive)} onClick={() => setHub(key)}>
                  {tabLabel[key]}
                </button>
              )
            })}
          </nav>
        </div>
      </header>

      <div className="mx-auto w-full max-w-7xl flex-1 overflow-auto px-4 py-6 lg:px-6">
        {active === 'registry' && canDocsManage ? (
          <Suspense
            fallback={<div className="text-sm text-slate-500">{t('common.loading')}</div>}
          >
            <DocumentsRegistryPage />
          </Suspense>
        ) : null}

        {active === 'verification' ? (
          <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm">
            {t('app.documents_hub.verification_placeholder', {
              defaultValue: 'Verification queue — connect to review workflows in a follow-up PR.',
            })}
          </div>
        ) : null}

        {active !== 'registry' && active !== 'verification' ? (
          <>
            {loading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
            {err && <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{err}</div>}

            {(active === 'all' || active === 'recruitment') && canDocsManage ? (
              <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-900">
                  {active === 'recruitment'
                    ? t('app.documents_hub.recruitment_heading', { defaultValue: 'Recruitment document processes' })
                    : t('app.documents_hub.all_heading', { defaultValue: 'All document processes (tenant)' })}
                </div>
                <ul className="divide-y divide-slate-100">
                  {allDocs.slice(0, 100).map((d: any) => (
                    <li key={d.id} className="px-4 py-2.5 text-sm text-slate-800">
                      <span className="font-medium">{d.title || d.type || d.id}</span>
                      <span className="text-slate-500"> · {d.status}</span>
                    </li>
                  ))}
                  {!allDocs.length && !loading ? (
                    <li className="px-4 py-8 text-center text-sm text-slate-500">
                      {t('app.documents_hub.empty', { defaultValue: 'No rows.' })}
                    </li>
                  ) : null}
                </ul>
              </section>
            ) : null}

            {active === 'missing' && canHrDocs ? (
              <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-900">
                  {t('app.documents_hub.missing_heading', { defaultValue: 'HR — missing (read-only)' })}
                </div>
                <ul className="divide-y divide-slate-100">
                  {(hrMissing?.items ?? []).map((row: any) => (
                    <li key={`${row.handoff_id}-${row.document_type}`} className="px-4 py-2 text-sm text-slate-800">
                      {row.document_type} · {row.handoff_id}
                    </li>
                  ))}
                  {!(hrMissing?.items ?? []).length && !loading ? (
                    <li className="px-4 py-8 text-center text-sm text-slate-500">{t('app.documents_hub.empty', { defaultValue: 'No rows.' })}</li>
                  ) : null}
                </ul>
              </section>
            ) : null}

            {active === 'expiring' && canHrDocs ? (
              <section className="mt-6 rounded-lg border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-900">
                  {t('app.documents_hub.expiring_heading', { defaultValue: 'HR — expiring (read-only)' })}
                </div>
                <ul className="divide-y divide-slate-100">
                  {(hrExpiring?.items ?? []).map((row: any) => (
                    <li key={`${row.handoff_id}-${row.document_type}-${row.expires_at}`} className="px-4 py-2 text-sm text-slate-800">
                      {row.document_type} · {row.expires_at || row.handoff_id}
                    </li>
                  ))}
                  {!(hrExpiring?.items ?? []).length && !loading ? (
                    <li className="px-4 py-8 text-center text-sm text-slate-500">{t('app.documents_hub.empty', { defaultValue: 'No rows.' })}</li>
                  ) : null}
                </ul>
              </section>
            ) : null}

            {active === 'hr' && canHrDocs ? (
              <div className="space-y-6">
                <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
                  <div className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-900">
                    {t('app.documents_hub.hr_missing', { defaultValue: 'HR missing' })}
                  </div>
                  <ul className="divide-y divide-slate-100">
                    {(hrMissing?.items ?? []).slice(0, 40).map((row: any) => (
                      <li key={`m-${row.handoff_id}-${row.document_type}`} className="px-4 py-2 text-sm text-slate-800">
                        {row.document_type} · {row.handoff_id}
                      </li>
                    ))}
                  </ul>
                </section>
                <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
                  <div className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-900">
                    {t('app.documents_hub.hr_expiring', { defaultValue: 'HR expiring' })}
                  </div>
                  <ul className="divide-y divide-slate-100">
                    {(hrExpiring?.items ?? []).slice(0, 40).map((row: any) => (
                      <li key={`e-${row.handoff_id}-${row.document_type}`} className="px-4 py-2 text-sm text-slate-800">
                        {row.document_type} · {row.expires_at || row.handoff_id}
                      </li>
                    ))}
                  </ul>
                </section>
              </div>
            ) : null}
          </>
        ) : null}

        {canDocsManage ? (
          <p className="mt-6 text-xs text-slate-500">
            {t('app.documents_hub.api_note', {
              defaultValue:
                'MVP uses existing APIs: listDocuments, GET /hr/documents/missing|expiring. Unified /documents/hub API can follow.',
            })}
          </p>
        ) : null}
      </div>
    </div>
  )
}
