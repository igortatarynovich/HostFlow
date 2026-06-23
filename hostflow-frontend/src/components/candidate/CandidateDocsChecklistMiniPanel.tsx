import { useCallback, useEffect, useMemo, useState } from 'react'
import clsx from 'clsx'
import { useI18n } from '../../i18n'
import { getSummary } from '../../api/documents'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import { extractRuntimeItemsFromSummary, runtimeBadgeFromRuntime } from '../../utils/runtimeBadgePresentation'

type SummaryRequired = {
  total: number
  approved?: number
  ready: number
  in_progress: number
  missing_count: number
  problems: number
  missing: string[]
  problematic: string[]
  ready_types?: string[]
  in_progress_types?: string[]
}

type Summary = {
  status: string
  percent_ready: number
  required: SummaryRequired
  expiring_soon: Array<{ type: string; expires_at: string }>
}

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
  const { t, locale } = useI18n()
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
      const s = (res as any)?.summary as Summary | undefined
      setSummary(s ?? null)
      setLoaded(true)
    } catch (err: any) {
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

  const missing = useMemo(() => summary?.required?.missing ?? [], [summary])
  const problematic = useMemo(() => summary?.required?.problematic ?? [], [summary])
  const expiring = useMemo(() => summary?.expiring_soon ?? [], [summary])

  const runtimeChecklistRows = useMemo(() => {
    const items = extractRuntimeItemsFromSummary(summary as Record<string, unknown> | null)
    return items
      .map((item) => {
        const type = String(item.document_type_code || '').trim()
        if (!type) return null
        const badge = runtimeBadgeFromRuntime(item.document_runtime)
        return { type, badge }
      })
      .filter((row): row is NonNullable<typeof row> => Boolean(row))
  }, [summary])

  const hasRuntimeChecklist = runtimeChecklistRows.length > 0

  const percent = useMemo(() => {
    const p = Number(summary?.percent_ready ?? 0)
    if (!Number.isFinite(p)) return 0
    return Math.max(0, Math.min(100, Math.round(p)))
  }, [summary])

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
            <div className="text-[11px] text-slate-500">{percent}%</div>
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
              {hasRuntimeChecklist ? (
                <ul className="space-y-1 rounded-xl border border-slate-200 bg-slate-50 p-2">
                  {runtimeChecklistRows.map((row) => (
                    <li key={row.type} className="flex items-center justify-between gap-2 text-xs">
                      <span className="font-medium text-slate-800">{labelForType(row.type)}</span>
                      <span className={clsx('rounded-full px-1.5 py-0.5 text-[11px] font-semibold', row.badge.className)}>
                        {t(row.badge.labelKey, { defaultValue: row.badge.badge })}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}

              {!hasRuntimeChecklist && missing.length ? (
                <div className="rounded-xl border border-rose-200 bg-rose-50 p-2">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-rose-700">
                    {t('app.candidate_card.docs_checklist.missing', { defaultValue: 'Missing' })}
                  </div>
                  <ul className="mt-1 space-y-1">
                    {missing.slice(0, 6).map((code) => (
                      <li key={code} className="text-xs text-rose-800">
                        {labelForType(code)}
                      </li>
                    ))}
                    {missing.length > 6 ? (
                      <li className="text-[11px] text-rose-700">
                        {t('common.and_more', { defaultValue: 'and more…' })}
                      </li>
                    ) : null}
                  </ul>
                </div>
              ) : null}

              {!hasRuntimeChecklist && problematic.length ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-2">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-amber-800">
                    {t('app.candidate_card.docs_checklist.problematic', { defaultValue: 'Needs attention' })}
                  </div>
                  <ul className="mt-1 space-y-1">
                    {problematic.slice(0, 6).map((code) => (
                      <li key={code} className="text-xs text-amber-900">
                        {labelForType(code)}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {!hasRuntimeChecklist && expiring.length ? (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-2">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-700">
                    {t('app.candidate_card.docs_checklist.expiring', { defaultValue: 'Expiring soon' })}
                  </div>
                  <ul className="mt-1 space-y-1">
                    {expiring.slice(0, 5).map((x) => (
                      <li key={`${x.type}-${x.expires_at}`} className="text-xs text-slate-700">
                        <span className="font-medium">{labelForType(String(x.type || ''))}</span>
                        <span className="ml-2 text-slate-500" title={x.expires_at}>
                          {new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : undefined, {
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                          }).format(new Date(x.expires_at))}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {hasRuntimeChecklist ? null : !missing.length && !problematic.length && !expiring.length ? (
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
