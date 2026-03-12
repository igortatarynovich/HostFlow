import { useEffect, useMemo, useState } from 'react'
import { useI18n } from '../i18n'
import { listDocuments } from '../api/documents'
import { createReminder } from '../api/client'
import type { Document } from '../api/types'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'

const QUICK_FILTERS = ['missing', 'requested', 'in_progress', 'ready'] as const
const PAGE_SIZE = 20

export default function DocumentsRegistryPage() {
  const { t } = useI18n()
  const [query, setQuery] = useState('')
  const [activeFilter, setActiveFilter] = useState<typeof QUICK_FILTERS[number] | null>('missing')
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [docTypeFilter, setDocTypeFilter] = useState('')
  const [ownerKindFilter, setOwnerKindFilter] = useState('')
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table')
  const [page, setPage] = useState(1)
  const [nowTs, setNowTs] = useState(() => Date.now())
  const [reminderDocId, setReminderDocId] = useState('')
  const [reminderTitle, setReminderTitle] = useState('Напомнить по документу')
  const [reminderDueAt, setReminderDueAt] = useState(() => {
    const dt = new Date(Date.now() + 60 * 60 * 1000)
    return dt.toISOString().slice(0, 16)
  })
  const [reminderOffset, setReminderOffset] = useState(15)
  const [reminderStatus, setReminderStatus] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    listDocuments({ limit: 200, signal: controller.signal })
      .then((items) => setDocuments(items))
      .catch((err) => {
        if (controller.signal.aborted) return
        console.error('[DocumentsRegistry] load failed', err)
        setError(t('admin.documents.registry.error'))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [reloadKey, t])

  useEffect(() => {
    // refresh relative time calculations when data changes
    setNowTs(Date.now())
  }, [documents])

  const handleCreateReminder = async () => {
    if (!reminderDocId || !reminderTitle || !reminderDueAt) {
      setReminderStatus('Заполните все поля')
      return
    }
    try {
      const due = new Date(reminderDueAt)
      const remindAt = new Date(due.getTime() - reminderOffset * 60 * 1000)
      await createReminder({
        title: reminderTitle,
        type: 'custom',
        entity_type: 'document',
        entity_id: reminderDocId,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        priority: 'normal',
      })
      setReminderStatus('Создано')
    } catch (err: any) {
      setReminderStatus('Ошибка создания')
    }
  }

  const stats = useMemo(() => {
    if (!documents.length) return { ready: 0, pending: 0, overdue: 0 }
    let ready = 0
    let pending = 0
    let overdue = 0
    documents.forEach((doc) => {
      const readiness = doc.readiness_state?.toLowerCase()
      if (doc.status === 'approved' || readiness === 'ready') {
        ready += 1
      } else if (doc.status === 'expired' || (doc.expires_at && Date.parse(doc.expires_at) < nowTs)) {
        overdue += 1
      } else {
        pending += 1
      }
    })
    return { ready, pending, overdue }
  }, [documents, nowTs])

  const docTypeOptions = useMemo(() => {
    const set = new Set<string>()
    documents.forEach((doc) => {
      if (doc.doc_type) set.add(doc.doc_type)
    })
    return Array.from(set).sort()
  }, [documents])

  const ownerKindOptions = useMemo(() => {
    const set = new Set<string>()
    documents.forEach((doc) => {
      if (doc.kind) set.add(doc.kind)
    })
    return Array.from(set)
  }, [documents])

  const filteredDocs = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    return documents
      .filter((doc) => {
        if (!activeFilter) return true
        const readiness = doc.readiness_state?.toLowerCase()
        if (activeFilter === 'ready') {
          return doc.status === 'approved' || readiness === 'ready'
        }
        return doc.status === activeFilter || readiness === activeFilter
      })
      .filter((doc) => {
        if (!normalizedQuery) return true
        const title = (doc.custom_name || doc.title || doc.meta?.title || doc.doc_type || '').toLowerCase()
        const owner =
          (
            doc.meta?.candidate_name ||
            doc.meta?.company_name ||
            doc.extra?.owner_name ||
            doc.owner_id ||
            ''
          ).toLowerCase()
        return (
          title.includes(normalizedQuery) ||
          owner.includes(normalizedQuery) ||
          doc.id?.toLowerCase().includes(normalizedQuery)
        )
      })
      .filter((doc) => {
        if (docTypeFilter && doc.doc_type !== docTypeFilter) return false
        if (ownerKindFilter && doc.kind !== ownerKindFilter) return false
        return true
      })
      .sort((a, b) => {
        const aTime = Date.parse(a.updated_at || a.created_at || '')
        const bTime = Date.parse(b.updated_at || b.created_at || '')
        return (bTime || 0) - (aTime || 0)
      })
  }, [documents, activeFilter, query, docTypeFilter, ownerKindFilter])

  useEffect(() => {
    setPage(1)
  }, [query, activeFilter, docTypeFilter, ownerKindFilter])

  const totalPages = Math.max(1, Math.ceil(filteredDocs.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const pageStart = (currentPage - 1) * PAGE_SIZE
  const currentDocs = filteredDocs.slice(pageStart, pageStart + PAGE_SIZE)

  return (
    <div className="space-y-4">
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-6 text-white shadow-card">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <p className="text-2xl font-semibold">{t('admin.documents.registry.title')}</p>
            <p className="max-w-3xl text-sm text-white/80">{t('admin.documents.registry.hero')}</p>
          </div>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          {[
            { label: t('admin.documents.registry.stats.ready'), value: stats.ready },
            { label: t('admin.documents.registry.stats.pending'), value: stats.pending },
            { label: t('admin.documents.registry.stats.overdue'), value: stats.overdue },
          ].map((item) => (
            <div key={item.label} className="rounded-2xl border border-white/30 bg-white/10 p-3 text-sm">
              <div className="text-white/70">{item.label}</div>
              <div className="text-2xl font-semibold">{item.value}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="app-surface space-y-4 p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex flex-1 flex-col gap-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('admin.documents.registry.search_label')}
            </label>
            <div className="relative">
              <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                className="input pl-10"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={t('admin.documents.registry.placeholder')}
              />
            </div>
          </div>
          <div className="rounded-2xl border border-dashed border-brand-100/70 bg-brand-50/40 p-4 text-sm text-slate-700">
            {t('admin.documents.registry.note')}
          </div>
          <button
            type="button"
            className="btn-secondary self-start"
            onClick={() => setReloadKey((prev) => prev + 1)}
            disabled={loading}
          >
            {loading ? t('admin.documents.registry.loading') : t('common.actions.refresh')}
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          {QUICK_FILTERS.map((filter) => (
            <button
              key={filter}
              type="button"
              onClick={() => setActiveFilter((prev) => (prev === filter ? null : filter))}
              className={[
                'rounded-lg border px-4 py-2 text-sm font-medium shadow-sm transition',
                activeFilter === filter ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300',
              ].join(' ')}
            >
              {t(`admin.documents.status_labels.${filter}`)}
            </button>
          ))}
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('admin.documents.registry.filter_type')}
            </span>
            <select className="input" value={docTypeFilter} onChange={(event) => setDocTypeFilter(event.target.value)}>
              <option value="">{t('common.actions.reset')}</option>
              {docTypeOptions.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('admin.documents.registry.filter_kind')}
            </span>
            <select
              className="input"
              value={ownerKindFilter}
              onChange={(event) => setOwnerKindFilter(event.target.value)}
            >
              <option value="">{t('common.actions.reset')}</option>
              {ownerKindOptions.map((kind) => (
                <option key={kind} value={kind}>
                  {t(`admin.documents.kinds.${kind}`, { defaultValue: kind })}
                </option>
              ))}
            </select>
          </label>
          <div className="flex flex-col gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('admin.documents.registry.view.label')}
            </span>
            <div className="inline-flex rounded-lg border border-brand-200 bg-white p-1 text-sm font-medium">
              <button
                type="button"
                className={[
                  'rounded-md px-3 py-1.5',
                  viewMode === 'table' ? 'bg-brand-600 text-white shadow' : 'text-brand-700',
                ].join(' ')}
                onClick={() => setViewMode('table')}
              >
                {t('admin.documents.registry.view.table')}
              </button>
              <button
                type="button"
                className={[
                  'rounded-md px-3 py-1.5',
                  viewMode === 'cards' ? 'bg-brand-600 text-white shadow' : 'text-brand-700',
                ].join(' ')}
                onClick={() => setViewMode('cards')}
              >
                {t('admin.documents.registry.view.cards')}
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="card space-y-4 p-5 lg:col-span-2">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-base font-semibold text-slate-900">{t('admin.documents.registry.table.title')}</p>
              <p className="text-sm text-slate-500">{t('admin.documents.registry.table.subtitle')}</p>
            </div>
            <span className="rounded-md bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
              {activeFilter ? t(`admin.documents.status_labels.${activeFilter}`) : t('admin.documents.registry.table.all')}
            </span>
          </div>

          {error && (
            <ErrorRecoveryBanner
              info={{
                title: error,
                hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
              }}
              onRetry={() => setReloadKey((prev) => prev + 1)}
              retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
              compact
            />
          )}
          {loading ? (
            <div className="text-sm text-slate-500">{t('admin.documents.registry.loading')}</div>
          ) : currentDocs.length ? (
            viewMode === 'cards' ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {currentDocs.map((doc) => (
                  <article key={doc.id} className="rounded-2xl border border-slate-100 bg-white/90 p-4 shadow-sm">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-base font-semibold text-slate-900">
                          {doc.custom_name || doc.title || doc.doc_type || t('common.labels.not_available')}
                        </p>
                        <p className="text-xs text-slate-500">{doc.doc_type}</p>
                      </div>
                      <StatusChip
                        tone={doc.status}
                        label={t(`admin.documents.status_labels.${doc.status}`, {
                          defaultValue: doc.status,
                        })}
                      />
                    </div>
                    <dl className="mt-3 space-y-1 text-sm text-slate-600">
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-400">
                          {t('admin.documents.registry.table.owner')}
                        </dt>
                        <dd className="font-medium text-slate-900">
                          {doc.meta?.candidate_name ||
                            doc.meta?.company_name ||
                            doc.extra?.owner_name ||
                            doc.owner_id ||
                            t('common.labels.not_available')}
                        </dd>
                      </div>
                      {doc.readiness_state && (
                        <div>
                          <dt className="text-xs uppercase tracking-wide text-slate-400">
                            {t('admin.documents.registry.table.status')}
                          </dt>
                          <dd>
                            {t(`admin.documents.readiness_labels.${doc.readiness_state}`, {
                              defaultValue: doc.readiness_state,
                            })}
                          </dd>
                        </div>
                      )}
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-400">
                          {t('admin.documents.registry.table.updated')}
                        </dt>
                        <dd>{formatDate(doc.updated_at || doc.created_at)}</dd>
                      </div>
                    </dl>
                  </article>
                ))}
              </div>
            ) : (
              <table className="w-full text-sm text-slate-700">
                <thead>
                  <tr className="bg-slate-50/90 text-left">
                    <th className="border-b border-r border-slate-200 py-2 pl-3 pr-2 text-xs font-semibold text-slate-600">{t('admin.documents.registry.table.doc')}</th>
                    <th className="border-b border-r border-slate-200 py-2 px-2 text-xs font-semibold text-slate-600">{t('admin.documents.registry.table.owner')}</th>
                    <th className="border-b border-r border-slate-200 py-2 px-2 text-xs font-semibold text-slate-600">{t('admin.documents.registry.table.status')}</th>
                    <th className="border-b border-slate-200 py-2 pl-2 pr-3 text-right text-xs font-semibold text-slate-600">{t('admin.documents.registry.table.updated')}</th>
                  </tr>
                </thead>
                <tbody>
                  {currentDocs.map((doc) => (
                    <tr key={doc.id} className="border-t border-slate-100">
                      <td className="border-r border-slate-200 py-3 pl-3 pr-2">
                        <p className="font-semibold text-slate-900">
                          {doc.custom_name || doc.title || doc.doc_type || t('common.labels.not_available')}
                        </p>
                        <p className="text-xs text-slate-500">{doc.doc_type}</p>
                      </td>
                      <td className="border-r border-slate-200 py-3 px-2">
                        <p className="font-medium text-slate-900">
                          {doc.meta?.candidate_name ||
                            doc.meta?.company_name ||
                            doc.extra?.owner_name ||
                            doc.owner_id ||
                            t('common.labels.not_available')}
                        </p>
                        <p className="text-xs text-slate-500">
                          {doc.kind ? t(`admin.documents.kinds.${doc.kind}`) : doc.owner_type || '—'}
                        </p>
                      </td>
                      <td className="border-r border-slate-200 py-3 px-2">
                        <StatusChip
                          tone={doc.status}
                          label={t(`admin.documents.status_labels.${doc.status}`, {
                            defaultValue: doc.status,
                          })}
                        />
                        {doc.readiness_state && (
                          <div className="mt-1 text-xs text-slate-500">
                            {t(`admin.documents.readiness_labels.${doc.readiness_state}`, {
                              defaultValue: doc.readiness_state,
                            })}
                          </div>
                        )}
                      </td>
                      <td className="py-3 pl-2 pr-3 text-right text-slate-600">
                        {formatDate(doc.updated_at || doc.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-center text-sm text-slate-500">
              {t('admin.documents.registry.table.empty')}
            </div>
          )}

          {!loading && filteredDocs.length > 0 && (
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4 text-sm text-slate-600">
              <span>
                {t('admin.documents.registry.pagination', {
                  values: {
                    from: filteredDocs.length ? pageStart + 1 : 0,
                    to: Math.min(pageStart + currentDocs.length, filteredDocs.length),
                    total: filteredDocs.length,
                  },
                })}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                >
                  {t('common.actions.back')}
                </button>
                <span className="text-xs text-slate-500">
                  {currentPage} / {totalPages}
                </span>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                >
                  {t('common.actions.next')}
                </button>
              </div>
            </div>
          )}
        </div>
        <div className="card space-y-3 p-5">
          <p className="text-base font-semibold text-slate-900">{t('admin.documents.registry.automation.title')}</p>
          <p className="text-sm text-slate-600">{t('admin.documents.registry.automation.description')}</p>
          <button type="button" className="btn-primary w-full">
            {t('admin.documents.registry.automation.action')}
          </button>
        </div>

        <div className="card space-y-3 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-base font-semibold text-slate-900">Быстрое напоминание</p>
              <p className="text-sm text-slate-500">По выбранному документу</p>
            </div>
          </div>
          <label className="text-sm text-slate-700">
            Документ
            <select
              className="input mt-1"
              value={reminderDocId}
              onChange={(e) => setReminderDocId(e.target.value)}
            >
              <option value="">Выберите документ</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id || ''}>
                  {(doc.custom_name || doc.title || doc.doc_type || 'Документ') +
                    (doc.meta?.candidate_name ? ` — ${doc.meta.candidate_name}` : '')}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-slate-700">
            Заголовок
            <input
              className="input mt-1"
              value={reminderTitle}
              onChange={(e) => setReminderTitle(e.target.value)}
              placeholder="Позвонить, отправить письмо..."
            />
          </label>
          <label className="text-sm text-slate-700">
            Срок
            <input
              type="datetime-local"
              className="input mt-1"
              value={reminderDueAt}
              onChange={(e) => setReminderDueAt(e.target.value)}
            />
          </label>
          <label className="text-sm text-slate-700">
            Напомнить за
            <select
              className="input mt-1"
              value={reminderOffset}
              onChange={(e) => setReminderOffset(Number(e.target.value))}
            >
              <option value={5}>5 мин</option>
              <option value={15}>15 мин</option>
              <option value={30}>30 мин</option>
              <option value={60}>1 час</option>
            </select>
          </label>
          <button type="button" className="btn-primary" onClick={handleCreateReminder}>
            Создать напоминание
          </button>
          {reminderStatus && <p className="text-xs text-slate-600">{reminderStatus}</p>}
        </div>
      </section>
    </div>
  )
}

const SearchIcon = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M12.9 14.32a7 7 0 1 1 1.414-1.414l3.396 3.397a1 1 0 0 1-1.414 1.414l-3.396-3.397ZM14 9a5 5 0 1 1-10 0 5 5 0 0 1 10 0Z"
      clipRule="evenodd"
    />
  </svg>
)

const STATUS_TONES: Record<string, string> = {
  missing: 'bg-slate-100 text-slate-700',
  requested: 'bg-sky-100 text-sky-700',
  in_progress: 'bg-sky-100 text-sky-700',
  received: 'bg-indigo-100 text-indigo-700',
  approved: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-rose-100 text-rose-700',
  expired: 'bg-amber-100 text-amber-800',
}

function StatusChip({ label, tone }: { label: string; tone: string }) {
  const toneClass = STATUS_TONES[tone] ?? 'bg-slate-100 text-slate-700'
  return (
    <span className={`inline-flex items-center rounded-md px-3 py-1 text-xs font-medium ${toneClass}`}>
      {label}
    </span>
  )
}

function formatDate(value?: string | null) {
  if (!value) return '—'
  const ts = Date.parse(value)
  if (Number.isNaN(ts)) return value
  return new Date(ts).toLocaleString()
}
