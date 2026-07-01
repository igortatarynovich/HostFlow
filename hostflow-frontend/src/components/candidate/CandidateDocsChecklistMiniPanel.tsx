import { useCallback, useEffect, useMemo, useState } from 'react'
import clsx from 'clsx'
import { useI18n } from '../../i18n'
import { getSummary } from '../../api/documents'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import { buildRuntimeWorkspaceFromSummary } from '../../utils/runtimeWorkspacePresentation'
import { RUNTIME_FILTER_LABEL_KEYS } from '../../utils/runtimeDocumentFilters'

type Summary = Record<string, unknown>

export default function CandidateDocsChecklistMiniPanel({
  candidateId,
  ownerContext,
  onOpenDocs,
  alwaysOpen = false,
}: {
  candidateId: string
  ownerContext?: Record<string, any> | null
  onOpenDocs?: () => void
  alwaysOpen?: boolean
}) {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const [open, setOpen] = useState(alwaysOpen)
  const [loaded, setLoaded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [documentsError, setDocumentsError] = useState<FriendlyErrorInfo | null>(null)
  const [summary, setSummary] = useState<Summary | null>(null)

  const load = useCallback(async () => {
    if (!candidateId) return
    setLoading(true)
    setDocumentsError(null)
    try {
      const res = await getSummary(candidateId, { context: ownerContext || null, fillMissing: true })
      const s = (res as { summary?: Summary })?.summary
      setSummary(s ?? null)
      setLoaded(true)
    } catch (err: unknown) {
      const fb = t('common.errors.request_failed', { defaultValue: 'Request failed' })
      if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
        setDocumentsError(getFriendlyErrorInfo(err, fb, t))
      }
      setSummary(null)
      setLoaded(true)
    } finally {
      setLoading(false)
    }
  }, [candidateId, ownerContext, planLimitModal, t])

  useEffect(() => {
    if (!open) return
    if (loaded) return
    void load()
  }, [loaded, load, open])

  const labelForType = useCallback(
    (code: string) => {
      const byTypeCode = t(`admin.documents.type_codes.${code}`, { defaultValue: '' }).trim()
      if (byTypeCode) return byTypeCode
      const byProcessType = t(`admin.documents.process_types.${code}`, { defaultValue: '' }).trim()
      if (byProcessType) return byProcessType
      const normalized = String(code || '').replace(/[_-]+/g, ' ').trim()
      return normalized || code
    },
    [t],
  )

  const workspace = useMemo(() => buildRuntimeWorkspaceFromSummary(summary), [summary])

  const legacyMissing = useMemo(() => {
    const required = summary?.required as { missing?: string[] } | undefined
    return required?.missing ?? []
  }, [summary])
  const legacyProblematic = useMemo(() => {
    const required = summary?.required as { problematic?: string[] } | undefined
    return required?.problematic ?? []
  }, [summary])
  const legacyExpiring = useMemo(() => {
    const rows = summary?.expiring_soon
    return Array.isArray(rows) ? rows : []
  }, [summary])

  const percent = workspace?.percentReady ?? Math.max(0, Math.min(100, Math.round(Number(summary?.percent_ready ?? 0) || 0)))

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold text-slate-700">
            {t('app.candidate_card.docs_checklist.title', { defaultValue: 'Required docs checklist' })}
          </div>
          <div className="mt-1 flex items-center gap-2">
            <div className="h-2 w-full max-w-[160px] rounded-full bg-slate-100 overflow-hidden">
              <div
                className={clsx('h-full rounded-full', percent >= 90 ? 'bg-emerald-500' : percent >= 50 ? 'bg-amber-500' : 'bg-rose-500')}
                style={{ width: `${percent}%` }}
              />
            </div>
            <div className="text-[11px] text-slate-500">
              {workspace
                ? t('app.candidate_card.documents.runtime_kpi', {
                    defaultValue: '{ready}/{total} · {percent}%',
                    values: {
                      ready: workspace.satisfiedCount,
                      total: workspace.totalRequired,
                      percent: workspace.percentReady,
                    },
                  })
                : `${percent}%`}
            </div>
          </div>
        </div>

        <div className="shrink-0 flex items-center gap-2">
          {!alwaysOpen ? (
            <>
              {onOpenDocs ? (
                <button type="button" className="btn-secondary btn-sm" onClick={onOpenDocs}>
                  {t('app.candidate_card.docs_checklist.open', { defaultValue: 'Open' })}
                </button>
              ) : null}
              <button
                type="button"
                className="text-[11px] text-slate-500 hover:text-slate-700"
                onClick={() => setOpen((v) => !v)}
              >
                {open ? t('common.actions.collapse') : t('common.actions.expand')}
              </button>
            </>
          ) : null}
        </div>
      </div>

      {open ? (
        <div className="mt-3 space-y-3">
          {loading ? <div className="text-xs text-slate-500">{t('common.loading')}</div> : null}
          {documentsError ? (
            <div className="text-xs text-red-600">
              <div>{documentsError.title}</div>
              {documentsError.detail ? <div className="mt-0.5 text-[11px] text-red-700/90">{documentsError.detail}</div> : null}
            </div>
          ) : null}

          {!loading && !documentsError && (
            <>
              {workspace ? (
                <>
                  <ul className="space-y-1 rounded-xl border border-slate-200 bg-slate-50 p-2">
                    {workspace.items.map((item) => (
                      <li key={item.documentTypeCode} className="flex items-center justify-between gap-2 text-xs">
                        <span className="font-medium text-slate-800">{labelForType(item.documentTypeCode)}</span>
                        <span className={clsx('rounded-full px-1.5 py-0.5 text-[11px] font-semibold', item.badge.className)}>
                          {t(item.badge.labelKey, { defaultValue: item.badge.badge })}
                        </span>
                      </li>
                    ))}
                  </ul>

                  {workspace.blockingItems.length ? (
                    <div className="rounded-xl border border-rose-200 bg-rose-50 p-2">
                      <div className="text-[10px] font-semibold uppercase tracking-wide text-rose-700">
                        {t('app.candidate_card.docs_checklist.blockers', { defaultValue: 'Blockers' })}
                      </div>
                      <ul className="mt-1 space-y-1">
                        {workspace.blockingItems.slice(0, 6).map((item) => (
                          <li key={item.documentTypeCode} className="text-xs text-rose-800">
                            <span className="font-medium">{labelForType(item.documentTypeCode)}</span>
                            {item.blockers[0]?.message ? (
                              <span className="ml-1 text-rose-700/90">— {item.blockers[0].message}</span>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  {workspace.warningOnlyItems.length ? (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-2">
                      <div className="text-[10px] font-semibold uppercase tracking-wide text-amber-800">
                        {t('app.candidate_card.docs_checklist.warnings', { defaultValue: 'Warnings' })}
                      </div>
                      <ul className="mt-1 space-y-1">
                        {workspace.warningOnlyItems.slice(0, 6).map((item) => (
                          <li key={item.documentTypeCode} className="text-xs text-amber-900">
                            <span className="font-medium">{labelForType(item.documentTypeCode)}</span>
                            <span className="ml-1 text-amber-800/90">
                              — {t(RUNTIME_FILTER_LABEL_KEYS.expiring_soon, { defaultValue: 'Expiring soon' })}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  {!workspace.blockingItems.length && !workspace.warningOnlyItems.length ? (
                    <div className="text-xs text-slate-500">
                      {t('app.candidate_card.docs_checklist.ok', { defaultValue: 'No blockers detected.' })}
                    </div>
                  ) : null}
                </>
              ) : null}

              {!workspace && legacyMissing.length ? (
                <div className="rounded-xl border border-rose-200 bg-rose-50 p-2">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-rose-700">
                    {t('app.candidate_card.docs_checklist.missing', { defaultValue: 'Missing' })}
                  </div>
                  <ul className="mt-1 space-y-1">
                    {legacyMissing.slice(0, 6).map((code) => (
                      <li key={code} className="text-xs text-rose-800">
                        {labelForType(code)}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {!workspace && legacyProblematic.length ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-2">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-amber-800">
                    {t('app.candidate_card.docs_checklist.problematic', { defaultValue: 'Needs attention' })}
                  </div>
                  <ul className="mt-1 space-y-1">
                    {legacyProblematic.slice(0, 6).map((code) => (
                      <li key={code} className="text-xs text-amber-900">
                        {labelForType(code)}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {!workspace && legacyExpiring.length ? (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-2">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-700">
                    {t('app.candidate_card.docs_checklist.expiring', { defaultValue: 'Expiring soon' })}
                  </div>
                  <ul className="mt-1 space-y-1">
                    {legacyExpiring.slice(0, 5).map((x) => (
                      <li key={`${String(x.type)}-${String(x.expires_at)}`} className="text-xs text-slate-700">
                        {labelForType(String(x.type || ''))}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {!workspace && !legacyMissing.length && !legacyProblematic.length && !legacyExpiring.length ? (
                <div className="text-xs text-slate-500">
                  {t('app.candidate_card.docs_checklist.ok', { defaultValue: 'No blockers detected.' })}
                </div>
              ) : null}
            </>
          )}
        </div>
      ) : null}
    </section>
  )
}
