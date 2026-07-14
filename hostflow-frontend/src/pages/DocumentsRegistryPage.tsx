import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useI18n } from '../i18n'
import { listDocuments } from '../api/documents'
import type { Document } from '../api/types'
import type { DocumentProcessType } from '../api/types/document'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader, Toolbar } from '../components/layout'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { QuotaNearLimitBanner } from '../components/billing/QuotaNearLimitBanner'
import { useBillingQuotaWarnings } from '../hooks/useBillingQuotaWarnings'
import type { FriendlyErrorInfo } from '../utils/friendlyError'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo } from '../utils/friendlyError'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { useAuth } from '../store/auth'
import { RegistryDocumentPreview } from '../modules/documents/RegistryDocumentPreview'
import { PROCESS_LABEL_KEYS } from '../modules/documents/constants'
import {
  documentProcessNeedsAttention,
  hasWorkflowOverdueStep,
  isProcessAssignedToUser,
  isProcessDocument,
} from '../modules/documents/workflowUtils'
import {
  documentMatchesRuntimeFilter,
  resolveRuntimeDocumentFilter,
  RUNTIME_DOCUMENT_FILTERS,
  RUNTIME_FILTER_LABEL_KEYS,
  type RuntimeDocumentFilter,
} from '../utils/runtimeDocumentFilters'

const QUEUE_FILTERS = ['all', 'process', 'my_process', 'wf_overdue'] as const
type QueueFilter = (typeof QUEUE_FILTERS)[number]
const PAGE_SIZE = 20

export default function DocumentsRegistryPage() {
  const { t } = useI18n()
  const { me } = useAuth()
  const planLimitModal = usePlanLimitModal()
  const { warningFor: quotaWarningFor } = useBillingQuotaWarnings()
  const storageQuotaWarning = quotaWarningFor('storage')
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState(() => (searchParams.get('q') || '').trim())
  const [activeFilter, setActiveFilter] = useState<RuntimeDocumentFilter | null>(() => {
    const quick = (searchParams.get('quick') || '').trim()
    const resolved = resolveRuntimeDocumentFilter(quick)
    if (resolved) return resolved
    if ((searchParams.get('status') || '').trim()) return null
    return 'missing'
  })
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [docTypeFilter, setDocTypeFilter] = useState(() => (searchParams.get('doc_type') || '').trim())
  const [ownerKindFilter, setOwnerKindFilter] = useState(() => (searchParams.get('owner_kind') || '').trim())
  const [statusFilter, setStatusFilter] = useState(() => (searchParams.get('status') || '').trim())
  const [mineOnly, setMineOnly] = useState(() => searchParams.get('mine') === '1')
  const [queueFilter, setQueueFilter] = useState<QueueFilter>(() => {
    const q = (searchParams.get('queue') || 'all').trim()
    return (QUEUE_FILTERS as readonly string[]).includes(q) ? (q as QueueFilter) : 'all'
  })
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table')
  const [page, setPage] = useState(1)
  const [nowTs, setNowTs] = useState(() => Date.now())
  const registryMode = searchParams.get('view') === 'registry'
  const workTab = searchParams.get('tab') === 'mine' ? 'mine' : 'attention'
  const listViewMode: 'table' | 'cards' = registryMode ? viewMode : 'table'

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    const isRegistry = searchParams.get('view') === 'registry'
    const kind =
      !isRegistry ? 'process' : queueFilter === 'all' ? undefined : ('process' as const)
    listDocuments({
      limit: 300,
      kind,
      signal: controller.signal,
    })
      .then((items) => setDocuments(items))
      .catch((err) => {
        if (controller.signal.aborted) return
        console.error('[DocumentsRegistry] load failed', err)
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.documents.registry.error'))) {
          setError(null)
        } else {
          setError(getFriendlyErrorInfo(err, t('admin.documents.registry.error'), t))
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [reloadKey, queueFilter, searchParams, planLimitModal, t])

  useEffect(() => {
    // refresh relative time calculations when data changes
    setNowTs(Date.now())
  }, [documents])

  useEffect(() => {
    if (searchParams.get('view') === 'registry') return
    const legacyRegistryIntent =
      Boolean(searchParams.get('quick')) ||
      Boolean(searchParams.get('status')) ||
      Boolean(searchParams.get('doc_type')) ||
      Boolean(searchParams.get('owner_kind')) ||
      searchParams.get('mine') === '1' ||
      Boolean(searchParams.get('queue'))
    if (!legacyRegistryIntent) return
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.set('view', 'registry')
        return next
      },
      { replace: true },
    )
  }, [searchParams, setSearchParams])

  useEffect(() => {
    const quick = (searchParams.get('quick') || '').trim()
    const status = (searchParams.get('status') || '').trim()
    const docType = (searchParams.get('doc_type') || '').trim()
    const ownerKind = (searchParams.get('owner_kind') || '').trim()
    const q = (searchParams.get('q') || '').trim()

    setQuery(q)
    setDocTypeFilter(docType)
    setOwnerKindFilter(ownerKind)
    setStatusFilter(status)
    setMineOnly(searchParams.get('mine') === '1')
    const queueRaw = (searchParams.get('queue') || 'all').trim()
    if ((QUEUE_FILTERS as readonly string[]).includes(queueRaw)) {
      setQueueFilter(queueRaw as QueueFilter)
    } else {
      setQueueFilter('all')
    }
    if (quick) {
      const resolved = resolveRuntimeDocumentFilter(quick)
      setActiveFilter(resolved)
    } else if (status) {
      const resolvedStatus = resolveRuntimeDocumentFilter(status)
      setActiveFilter(resolvedStatus)
    } else {
      setActiveFilter(null)
    }
  }, [searchParams])

  useEffect(() => {
    const isRegistry = searchParams.get('view') === 'registry'
    const q = query.trim()
    const st = statusFilter.trim()
    const nextQuick = activeFilter || ''
    const sel = (searchParams.get('sel') || '').trim()
    const queueNorm = (queueFilter || 'all') as QueueFilter
    const tabMine = searchParams.get('tab') === 'mine'

    const registryNoise =
      Boolean(searchParams.get('quick')) ||
      Boolean(searchParams.get('status')) ||
      Boolean(searchParams.get('doc_type')) ||
      Boolean(searchParams.get('owner_kind')) ||
      searchParams.get('mine') === '1' ||
      Boolean(searchParams.get('queue'))

    let same =
      (searchParams.get('q') || '') === q &&
      (searchParams.get('sel') || '') === sel

    if (isRegistry) {
      const queueInUrl = ((searchParams.get('queue') || 'all').trim() || 'all') as QueueFilter
      same =
        same &&
        searchParams.get('view') === 'registry' &&
        (searchParams.get('quick') || '') === nextQuick &&
        (searchParams.get('status') || '') === st &&
        (searchParams.get('doc_type') || '') === docTypeFilter &&
        (searchParams.get('owner_kind') || '') === ownerKindFilter &&
        (searchParams.get('mine') || '') === (mineOnly ? '1' : '') &&
        queueInUrl === queueNorm &&
        !tabMine
    } else {
      same =
        same &&
        searchParams.get('view') !== 'registry' &&
        !registryNoise &&
        (tabMine ? searchParams.get('tab') === 'mine' : !searchParams.get('tab'))
    }

    if (same) return

    const next = new URLSearchParams()
    if (q) next.set('q', q)
    if (sel) next.set('sel', sel)

    if (isRegistry) {
      next.set('view', 'registry')
      if (activeFilter) next.set('quick', activeFilter)
      if (st) next.set('status', st)
      if (docTypeFilter) next.set('doc_type', docTypeFilter)
      if (ownerKindFilter) next.set('owner_kind', ownerKindFilter)
      if (mineOnly) next.set('mine', '1')
      if (queueFilter && queueFilter !== 'all') next.set('queue', queueFilter)
    } else if (tabMine) {
      next.set('tab', 'mine')
    }

    setSearchParams(next, { replace: true })
  }, [
    query,
    activeFilter,
    docTypeFilter,
    ownerKindFilter,
    statusFilter,
    mineOnly,
    queueFilter,
    searchParams,
    setSearchParams,
  ])

  const processQueueStats = useMemo(() => {
    let process = 0
    let my = 0
    let od = 0
    documents.forEach((doc) => {
      if (!isProcessDocument(doc)) return
      process += 1
      if (me?.id && String(doc.owner_id) === String(me.id)) my += 1
      if (hasWorkflowOverdueStep(doc, nowTs)) od += 1
    })
    return { process, my, overdue: od }
  }, [documents, me?.id, nowTs])

  const workQueueStats = useMemo(() => {
    if (!me?.id) return { attention: 0, mine: 0 }
    let mine = 0
    let attention = 0
    documents.forEach((doc) => {
      if (!isProcessAssignedToUser(doc, me.id)) return
      mine += 1
      if (documentProcessNeedsAttention(doc, nowTs)) attention += 1
    })
    return { attention, mine }
  }, [documents, me?.id, nowTs])

  const translateStatus = useCallback(
    (s: string) => t(`admin.documents.status_labels.${s}`, { defaultValue: s }),
    [t],
  )
  const translateProcess = useCallback(
    (v: string | null | undefined) => {
      if (!v) return null
      const key = PROCESS_LABEL_KEYS[v as DocumentProcessType]
      return key ? t(key) : v
    },
    [t],
  )
  const handleDocPatched = useCallback((next: Document) => {
    setDocuments((prev) => prev.map((d) => (String(d.id) === String(next.id) ? next : d)))
  }, [])

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

    const matchesSearch = (doc: Document) => {
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
      const processQ = (documentProcessListLabel(doc, translateProcess) || '').toLowerCase()
      if (
        title.includes(normalizedQuery) ||
        owner.includes(normalizedQuery) ||
        processQ.includes(normalizedQuery)
      ) {
        return true
      }
      if (registryMode && doc.id?.toLowerCase().includes(normalizedQuery)) return true
      return false
    }

    const sortByUpdated = (a: Document, b: Document) => {
      const aTime = Date.parse(a.updated_at || a.created_at || '')
      const bTime = Date.parse(b.updated_at || b.created_at || '')
      return (bTime || 0) - (aTime || 0)
    }

    if (!registryMode) {
      return documents
        .filter((doc) => {
          if (!me?.id) return false
          if (!isProcessAssignedToUser(doc, me.id)) return false
          if (workTab === 'attention' && !documentProcessNeedsAttention(doc, nowTs)) return false
          return true
        })
        .filter(matchesSearch)
        .sort(sortByUpdated)
    }

    return documents
      .filter((doc) => {
        if (!activeFilter) return true
        return documentMatchesRuntimeFilter(doc, activeFilter)
      })
      .filter(matchesSearch)
      .filter((doc) => {
        if (docTypeFilter && doc.doc_type !== docTypeFilter) return false
        if (ownerKindFilter && doc.kind !== ownerKindFilter) return false
        const runtimeStatus = resolveRuntimeDocumentFilter(statusFilter)
        if (runtimeStatus && !documentMatchesRuntimeFilter(doc, runtimeStatus)) return false
        if (mineOnly && me?.id && doc.responsible_user_id !== me.id) return false
        if (queueFilter === 'process') {
          if (!isProcessDocument(doc)) return false
        } else if (queueFilter === 'my_process') {
          if (!isProcessDocument(doc) || !me?.id || String(doc.owner_id) !== String(me.id)) return false
        } else if (queueFilter === 'wf_overdue') {
          if (!hasWorkflowOverdueStep(doc, nowTs)) return false
        }
        return true
      })
      .sort(sortByUpdated)
  }, [
    documents,
    registryMode,
    workTab,
    activeFilter,
    query,
    docTypeFilter,
    ownerKindFilter,
    statusFilter,
    mineOnly,
    me,
    queueFilter,
    nowTs,
    translateProcess,
  ])

  const selectedId = (searchParams.get('sel') || '').trim()
  const selectedDoc = useMemo(
    () => filteredDocs.find((d) => String(d.id) === selectedId) ?? null,
    [filteredDocs, selectedId],
  )

  const selectDocument = useCallback(
    (id: string | null) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          if (id) next.set('sel', id)
          else next.delete('sel')
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  const setWorkTabParam = useCallback(
    (tab: 'attention' | 'mine') => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          if (tab === 'mine') next.set('tab', 'mine')
          else next.delete('tab')
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  const openFullRegistry = useCallback(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.set('view', 'registry')
        next.delete('tab')
        return next
      },
      { replace: true },
    )
  }, [setSearchParams])

  const openMyWork = useCallback(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.delete('view')
        next.delete('quick')
        next.delete('status')
        next.delete('doc_type')
        next.delete('owner_kind')
        next.delete('mine')
        next.delete('queue')
        return next
      },
      { replace: true },
    )
  }, [setSearchParams])

  useEffect(() => {
    if (!selectedId) return
    if (!filteredDocs.some((d) => String(d.id) === selectedId)) {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          next.delete('sel')
          return next
        },
        { replace: true },
      )
    }
  }, [filteredDocs, selectedId, setSearchParams])

  useEffect(() => {
    setPage(1)
  }, [query, activeFilter, docTypeFilter, ownerKindFilter, statusFilter, mineOnly, queueFilter, workTab, registryMode])

  const totalPages = Math.max(1, Math.ceil(filteredDocs.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const pageStart = (currentPage - 1) * PAGE_SIZE
  const currentDocs = filteredDocs.slice(pageStart, pageStart + PAGE_SIZE)

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={
            registryMode ? t('admin.documents.registry.title') : t('admin.documents.registry.work.title')
          }
          kind="action"
          primaryAction={
            registryMode ? (
              <button type="button" className="btn-secondary btn-sm" onClick={openMyWork}>
                {t('admin.documents.registry.work.back_to_my_work')}
              </button>
            ) : (
              <button type="button" className="btn-primary btn-sm" onClick={openFullRegistry}>
                {t('admin.documents.registry.work.open_full_registry')}
              </button>
            )
          }
          secondaryActions={
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => setReloadKey((prev) => prev + 1)}
              disabled={loading}
            >
              {loading ? t('admin.documents.registry.loading') : t('common.actions.refresh')}
            </button>
          }
        />
        {storageQuotaWarning ? (
          <div className="mt-2">
            <QuotaNearLimitBanner kind="storage" percentUsed={storageQuotaWarning.percentUsed} />
          </div>
        ) : null}
        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          {(registryMode
            ? [
                { label: t('admin.documents.registry.stats.process_all'), value: processQueueStats.process },
                { label: t('admin.documents.registry.stats.process_mine'), value: processQueueStats.my },
                { label: t('admin.documents.registry.stats.process_sla_due'), value: processQueueStats.overdue },
              ]
            : [
                { label: t('admin.documents.registry.work.stats.attention'), value: workQueueStats.attention },
                { label: t('admin.documents.registry.work.stats.mine_total'), value: workQueueStats.mine },
              ]
          ).map((item) => (
            <div
              key={item.label}
              className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs sm:text-sm"
            >
              <div className="text-slate-500">{item.label}</div>
              <div className="text-xl font-semibold tabular-nums text-slate-900">{item.value}</div>
            </div>
          ))}
        </div>
      </PageShellHeader>

      <Toolbar>
        <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="relative min-w-0 flex-1">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              className="input w-full pl-10 text-sm"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={
                registryMode
                  ? t('admin.documents.registry.placeholder')
                  : t('admin.documents.registry.work.search_placeholder')
              }
              aria-label={t('admin.documents.registry.search_label')}
            />
          </div>
        </div>

        {registryMode ? (
          <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
            <select
              className="input max-w-[200px] text-sm"
              aria-label={t('admin.documents.registry.preset_filter')}
              value={activeFilter ?? ''}
              onChange={(event) => {
                const v = event.target.value
                setActiveFilter(v === '' ? null : (v as RuntimeDocumentFilter))
              }}
            >
              <option value="">{t('admin.documents.registry.table.all')}</option>
              {RUNTIME_DOCUMENT_FILTERS.map((filter) => (
                <option key={filter} value={filter}>
                  {t(RUNTIME_FILTER_LABEL_KEYS[filter], { defaultValue: filter })}
                </option>
              ))}
            </select>
            <div className="flex flex-wrap gap-1" role="group" aria-label={t('admin.documents.registry.queue_filter')}>
              {QUEUE_FILTERS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => setQueueFilter(q)}
                  className={[
                    'rounded border px-2 py-1 text-xs font-medium transition',
                    queueFilter === q
                      ? 'border-teal-600 bg-teal-600 text-white'
                      : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300',
                  ].join(' ')}
                >
                  {t(`admin.documents.registry.queue.${q}`)}
                </button>
              ))}
            </div>
            <select
              className="input max-w-[180px] text-sm"
              aria-label={t('admin.documents.registry.filter_type')}
              value={docTypeFilter}
              onChange={(event) => setDocTypeFilter(event.target.value)}
            >
              <option value="">{t('admin.documents.registry.filter_type')}</option>
              {docTypeOptions.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
            <select
              className="input max-w-[160px] text-sm"
              aria-label={t('admin.documents.registry.filter_kind')}
              value={ownerKindFilter}
              onChange={(event) => setOwnerKindFilter(event.target.value)}
            >
              <option value="">{t('admin.documents.registry.filter_kind')}</option>
              {ownerKindOptions.map((kind) => (
                <option key={kind} value={kind}>
                  {t(`admin.documents.kinds.${kind}`, { defaultValue: kind })}
                </option>
              ))}
            </select>
            <label className="flex cursor-pointer items-center gap-1.5 whitespace-nowrap text-xs text-slate-700">
              <input
                type="checkbox"
                className="rounded border-slate-300"
                checked={mineOnly}
                onChange={(event) => setMineOnly(event.target.checked)}
              />
              {t('admin.documents.registry.mine_only')}
            </label>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-3">
            <button
              type="button"
              onClick={() => setWorkTabParam('attention')}
              className={[
                'rounded-lg border px-2.5 py-1 text-sm font-medium transition',
                workTab === 'attention'
                  ? 'border-teal-600 bg-teal-600 text-white'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300',
              ].join(' ')}
            >
              {t('admin.documents.registry.work.tab.attention')}
            </button>
            <button
              type="button"
              onClick={() => setWorkTabParam('mine')}
              className={[
                'rounded-lg border px-2.5 py-1 text-sm font-medium transition',
                workTab === 'mine'
                  ? 'border-teal-600 bg-teal-600 text-white'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300',
              ].join(' ')}
            >
              {t('admin.documents.registry.work.tab.mine')}
            </button>
          </div>
        )}
        </div>
      </Toolbar>

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pb-4">
      <section className="flex flex-col gap-4 lg:flex-row lg:items-start lg:gap-6">
        <div className="order-1 min-w-0 flex-1 space-y-4">
        <div className="card space-y-3 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0">
              <p className="text-base font-semibold text-slate-900">{t('admin.documents.registry.table.title')}</p>
              <span className="text-xs tabular-nums text-slate-500">{filteredDocs.length}</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {registryMode ? (
                <div className="inline-flex rounded-md border border-slate-200 bg-white p-0.5 text-xs font-medium">
                  <button
                    type="button"
                    className={[
                      'rounded px-2 py-1',
                      viewMode === 'table' ? 'bg-slate-800 text-white' : 'text-slate-600',
                    ].join(' ')}
                    onClick={() => setViewMode('table')}
                  >
                    {t('admin.documents.registry.view.table')}
                  </button>
                  <button
                    type="button"
                    className={[
                      'rounded px-2 py-1',
                      viewMode === 'cards' ? 'bg-slate-800 text-white' : 'text-slate-600',
                    ].join(' ')}
                    onClick={() => setViewMode('cards')}
                  >
                    {t('admin.documents.registry.view.cards')}
                  </button>
                </div>
              ) : null}
            </div>
          </div>

          {error && (
            <ErrorRecoveryBanner
              info={error}
              onRetry={() => setReloadKey((prev) => prev + 1)}
              retryLabel={t('common.actions.retry')}
              {...friendlyErrorBannerSecondary(error, CRM_APP_PATHS.documents, t('app.nav.items.documents'))}
              compact
            />
          )}
          {loading ? (
            <div className="text-sm text-slate-500">{t('admin.documents.registry.loading')}</div>
          ) : currentDocs.length ? (
            listViewMode === 'cards' ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {currentDocs.map((doc) => {
                  const deadline = documentDeadlineParts(doc, nowTs)
                  const isSel = String(doc.id) === selectedId
                  return (
                    <article
                      key={doc.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => selectDocument(doc.id ? String(doc.id) : null)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          selectDocument(doc.id ? String(doc.id) : null)
                        }
                      }}
                      className={[
                        'rounded-2xl border bg-white/90 p-4 text-left shadow-sm outline-none transition',
                        isSel ? 'border-brand-400 ring-1 ring-brand-200' : 'border-slate-100',
                      ].join(' ')}
                    >
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
                              (registryMode ? doc.owner_id : null) ||
                              t('common.labels.not_available')}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-xs uppercase tracking-wide text-slate-400">
                            {t('admin.documents.registry.table.responsible')}
                          </dt>
                          <dd className="font-medium text-slate-900">{documentResponsibleLabel(doc)}</dd>
                        </div>
                        <div>
                          <dt className="text-xs uppercase tracking-wide text-slate-400">
                            {t('admin.documents.registry.table.process')}
                          </dt>
                          <dd className="font-medium text-slate-800">
                            {documentProcessListLabel(doc, translateProcess)}
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
                        <div>
                          <dt className="text-xs uppercase tracking-wide text-slate-400">
                            {t('admin.documents.registry.table.deadline')}
                          </dt>
                          <dd className={deadline.overdue ? 'font-medium text-amber-800' : 'text-slate-900'}>
                            {deadline.text}
                            {deadline.overdue ? (
                              <span className="ml-1 text-[11px] text-amber-700">
                                ({t('admin.documents.registry.table.deadline_overdue')})
                              </span>
                            ) : null}
                          </dd>
                        </div>
                      </dl>
                    </article>
                  )
                })}
              </div>
            ) : (
              <table className="w-full text-sm text-slate-700">
                <thead>
                  <tr className="bg-slate-50/90 text-left">
                    <th className="border-b border-r border-slate-200 py-2 pl-3 pr-2 text-xs font-semibold text-slate-600">{t('admin.documents.registry.table.doc')}</th>
                    <th className="border-b border-r border-slate-200 py-2 px-2 text-xs font-semibold text-slate-600">{t('admin.documents.registry.table.owner')}</th>
                    <th className="border-b border-r border-slate-200 py-2 px-2 text-xs font-semibold text-slate-600">{t('admin.documents.registry.table.responsible')}</th>
                    <th className="border-b border-r border-slate-200 py-2 px-2 text-xs font-semibold text-slate-600">{t('admin.documents.registry.table.process')}</th>
                    <th className="border-b border-r border-slate-200 py-2 px-2 text-xs font-semibold text-slate-600">{t('admin.documents.registry.table.status')}</th>
                    <th className="border-b border-r border-slate-200 py-2 px-2 text-xs font-semibold text-slate-600">{t('admin.documents.registry.table.deadline')}</th>
                    <th className="border-b border-slate-200 py-2 pl-2 pr-3 text-right text-xs font-semibold text-slate-600">{t('admin.documents.registry.table.updated')}</th>
                  </tr>
                </thead>
                <tbody>
                  {currentDocs.map((doc) => {
                    const deadline = documentDeadlineParts(doc, nowTs)
                    const isSel = String(doc.id) === selectedId
                    return (
                      <tr
                        key={doc.id}
                        className={[
                          'cursor-pointer border-t border-slate-100 transition',
                          isSel ? 'bg-brand-50/90' : 'hover:bg-slate-50/80',
                        ].join(' ')}
                        onClick={() => selectDocument(doc.id ? String(doc.id) : null)}
                      >
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
                              (registryMode ? doc.owner_id : null) ||
                              t('common.labels.not_available')}
                          </p>
                          <p className="text-xs text-slate-500">
                            {doc.kind ? t(`admin.documents.kinds.${doc.kind}`) : doc.owner_type || '—'}
                          </p>
                        </td>
                        <td className="border-r border-slate-200 py-3 px-2 text-slate-800">
                          {documentResponsibleLabel(doc)}
                        </td>
                        <td className="border-r border-slate-200 py-3 px-2 text-slate-700">
                          {documentProcessListLabel(doc, translateProcess)}
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
                        <td className="border-r border-slate-200 py-3 px-2 text-slate-600">
                          <span className={deadline.overdue ? 'font-medium text-amber-800' : ''}>{deadline.text}</span>
                          {deadline.overdue ? (
                            <span className="ml-1 text-[11px] text-amber-700">
                              ({t('admin.documents.registry.table.deadline_overdue')})
                            </span>
                          ) : null}
                        </td>
                        <td className="py-3 pl-2 pr-3 text-right text-slate-600">
                          {formatDate(doc.updated_at || doc.created_at)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-center text-sm text-slate-500">
              {!registryMode && !me?.id
                ? t('admin.documents.registry.work.empty.no_session')
                : !registryMode && workTab === 'attention'
                  ? t('admin.documents.registry.work.empty.attention')
                  : !registryMode
                    ? t('admin.documents.registry.work.empty.mine')
                    : t('admin.documents.registry.table.empty')}
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
                  className="btn-secondary btn-sm"
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
                  className="btn-secondary btn-sm"
                  onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                >
                  {t('common.actions.next')}
                </button>
              </div>
            </div>
          )}
        </div>

        </div>

        <aside className="order-2 w-full shrink-0 lg:order-2 lg:w-[min(100%,380px)] lg:sticky lg:top-6">
          <div className="card space-y-3 border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-slate-900">{t('admin.documents.registry.preview.title')}</p>
              </div>
              {selectedId ? (
                <button
                  type="button"
                  className="text-xs font-medium text-brand-700 hover:underline"
                  onClick={() => selectDocument(null)}
                >
                  {t('admin.documents.registry.preview.clear')}
                </button>
              ) : null}
            </div>
            {selectedDoc ? (
              <RegistryDocumentPreview
                doc={selectedDoc}
                nowTs={nowTs}
                meId={me?.id ? String(me.id) : null}
                onPatched={handleDocPatched}
                planLimitError={(err, fb) => planLimitModal?.showPlanLimitIfNeeded(err, fb) ?? false}
                translateStatus={translateStatus}
                translateProcess={translateProcess}
              />
            ) : (
              <p className="text-sm text-slate-500">{t('admin.documents.registry.preview.empty')}</p>
            )}
          </div>
        </aside>
      </section>
      </div>
    </PageShell>
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
    <span className={`inline-flex shrink-0 items-center rounded-md px-2 py-0.5 text-[11px] font-medium ${toneClass}`}>
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

function documentResponsibleLabel(doc: Document): string {
  const n = doc.responsible_name?.trim()
  if (n) return n
  return '—'
}

function documentProcessListLabel(
  doc: Document,
  translateProcess: (v: string | null | undefined) => string | null,
): string {
  if (!isProcessDocument(doc)) return '—'
  const raw = doc.workflow?.process_type ?? doc.process_type
  if (!raw || raw === 'none') return '—'
  return translateProcess(raw) || String(raw)
}

function documentDeadlineParts(doc: Document, nowTs: number): { text: string; overdue: boolean } {
  const raw = doc.expires_at || doc.expire_date
  if (!raw) return { text: '—', overdue: false }
  const ts = Date.parse(raw)
  const text = formatDate(raw)
  if (Number.isNaN(ts)) return { text, overdue: false }
  const overdue = ts < nowTs || doc.status === 'expired'
  return { text, overdue }
}
