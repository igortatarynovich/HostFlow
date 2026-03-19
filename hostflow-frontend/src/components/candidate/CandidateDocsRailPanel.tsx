import { useCallback, useEffect, useMemo, useState } from 'react'
import clsx from 'clsx'
import { useI18n } from '../../i18n'
import { getSummary } from '../../api/documents'

type RequiredState = {
  missing: string[]
  problematic: string[]
  ready_types?: string[]
  in_progress_types?: string[]
}

type SummaryResponse = {
  percent_ready: number
  required?: RequiredState
  expiring_soon?: Array<{ type: string; expires_at: string }>
}

type Props = {
  candidateId: string
  ownerContext?: Record<string, any> | null
  uploadBusy?: boolean
  onUpload?: () => void
  refreshTrigger?: number
  // For pipeline gating + next action overriding
  onLoadedBlockers?: (blockers: { missing: string[]; problematic: string[]; inProgress: string[] }) => void
  onLoadingChange?: (loading: boolean) => void
  onOpenDocs?: () => void
  onSelectType?: (typeCode: string) => void
  pollingEnabled?: boolean
  pollingIntervalMs?: number
}

type RowStatus = 'missing' | 'expiring' | 'valid' | 'in_progress'

export default function CandidateDocsRailPanel({
  candidateId,
  ownerContext,
  uploadBusy,
  onUpload,
  refreshTrigger = 0,
  onLoadedBlockers,
  onLoadingChange,
  onOpenDocs,
  onSelectType,
  pollingEnabled = false,
  pollingIntervalMs = 30_000,
}: Props) {
  const { t, locale } = useI18n()
  const [loading, setLoading] = useState(false)
  const [errorText, setErrorText] = useState<string | null>(null)
  const [summary, setSummary] = useState<SummaryResponse | null>(null)

  const load = useCallback(async () => {
    if (!candidateId) return
    setLoading(true)
    setErrorText(null)
    try {
      const res = await getSummary(candidateId, { context: ownerContext || null, fillMissing: true })
      const s = (res as any)?.summary as SummaryResponse | undefined
      setSummary(s ?? null)
    } catch (err: any) {
      setErrorText(err?.response?.data?.detail ?? err?.message ?? 'Request failed')
      setSummary(null)
    } finally {
      setLoading(false)
    }
  }, [candidateId, ownerContext])

  useEffect(() => {
    void load()
  }, [load, refreshTrigger])

  useEffect(() => {
    onLoadingChange?.(loading)
  }, [loading, onLoadingChange])

  const missing = useMemo(() => summary?.required?.missing ?? [], [summary])
  const problematic = useMemo(() => summary?.required?.problematic ?? [], [summary])
  const readyTypes = useMemo(() => summary?.required?.ready_types ?? [], [summary])
  const inProgressTypes = useMemo(() => summary?.required?.in_progress_types ?? [], [summary])
  const expiringSoon = useMemo(() => summary?.expiring_soon ?? [], [summary])

  const hasBlockers = missing.length > 0 || problematic.length > 0

  useEffect(() => {
    onLoadedBlockers?.({ missing, problematic, inProgress: inProgressTypes })
  }, [missing, problematic, inProgressTypes, onLoadedBlockers])

  // NOTE: we intentionally do NOT poll repeatedly here.
  // Polling can cause request storms (browser "ERR_INSUFFICIENT_RESOURCES")
  // and unnecessary load. The blockers state is refreshed via `refreshTrigger`
  // after upload actions.

  const labelForType = useCallback(
    (code: string) => t(`admin.documents.types.${code}`, { defaultValue: code }),
    [t],
  )

  const rows = useMemo(() => {
    const expMap = new Map<string, string>()
    for (const x of expiringSoon) {
      if (!x?.type) continue
      if (!expMap.has(String(x.type))) expMap.set(String(x.type), String(x.expires_at || ''))
    }

    const out: Array<{ type: string; status: RowStatus; meta?: string }> = []

    // Blockers first
    for (const code of missing) out.push({ type: code, status: 'missing' })
    for (const code of problematic) out.push({ type: code, status: 'missing', meta: 'needs_attention' })

    for (const code of readyTypes) out.push({ type: code, status: 'valid' })
    for (const code of inProgressTypes) out.push({ type: code, status: 'in_progress' })

    for (const code of expiringSoon.map((x) => String(x.type || '')).filter(Boolean)) {
      const expiresAt = expMap.get(code) || ''
      out.push({
        type: code,
        status: 'expiring',
        meta: expiresAt,
      })
    }

    // Deduplicate by type+status
    const seen = new Set<string>()
    return out.filter((r) => {
      const k = `${r.type}::${r.status}`
      if (seen.has(k)) return false
      seen.add(k)
      return true
    })
  }, [expiringSoon, inProgressTypes, missing, problematic, readyTypes])

  const statusPill = useCallback(
    (s: RowStatus) => {
      switch (s) {
        case 'missing':
          return 'bg-rose-50 text-rose-800 border-rose-200'
        case 'expiring':
          return 'bg-amber-50 text-amber-800 border-amber-200'
        case 'valid':
          return 'bg-emerald-50 text-emerald-800 border-emerald-200'
        case 'in_progress':
          return 'bg-slate-50 text-slate-700 border-slate-200'
      }
    },
    [],
  )

  const formatExpDate = useCallback(
    (iso: string) => {
      if (!iso) return null
      try {
        return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : undefined, {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
        }).format(new Date(iso))
      } catch {
        return iso
      }
    },
    [locale],
  )

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold text-slate-800">{t('app.candidate_card.documents.title', { defaultValue: 'Documents' })}</div>

          <div className="mt-1 text-[11px] text-slate-600">
            {hasBlockers
              ? t('app.candidate_card.documents.blockers_subtitle', { defaultValue: 'Blockers stop the pipeline' })
              : t('app.candidate_card.documents.ok_subtitle', { defaultValue: 'Ready to move forward' })}
          </div>
        </div>

        {onUpload ? (
          <button type="button" className="btn-primary btn-sm" onClick={onUpload} disabled={uploadBusy}>
            {uploadBusy ? t('common.saving', { defaultValue: 'Working...' }) : t('app.candidate_card.documents.upload_btn', { defaultValue: 'Upload' })}
          </button>
        ) : null}
      </div>

      <div className="mt-3">
        {loading ? (
          <div className="text-xs text-slate-500">{t('common.loading')}</div>
        ) : errorText ? (
          <div className="text-xs text-rose-600">{errorText}</div>
        ) : (
          <div className="space-y-1">
            {rows.length ? (
              rows.map((r, idx) => (
                <button
                  key={`${r.type}-${r.status}-${idx}`}
                  type="button"
                  className={clsx(
                    'w-full rounded-xl border px-2 py-1.5 text-left transition hover:shadow-sm',
                    statusPill(r.status),
                  )}
                  onClick={() => {
                    if (r.type) onSelectType?.(r.type)
                    onOpenDocs?.()
                  }}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0 text-xs font-semibold text-slate-900 truncate">
                      {labelForType(r.type)}
                    </div>
                    <div className="shrink-0 text-[11px] font-semibold">
                      {r.status === 'missing'
                        ? `→ ${t('app.candidate_card.documents.status.missing', { defaultValue: 'missing' })}`
                        : r.status === 'valid'
                          ? `→ ${t('app.candidate_card.documents.status.valid', { defaultValue: 'valid' })}`
                          : r.status === 'expiring'
                            ? `→ ${t('app.candidate_card.documents.status.expiring', { defaultValue: 'expiring' })}${r.meta ? ` · ${formatExpDate(r.meta)}` : ''}`
                            : `→ ${t('app.candidate_card.documents.status.in_progress', { defaultValue: 'in progress' })}`}
                    </div>
                  </div>
                </button>
              ))
            ) : (
              <div className="text-xs text-slate-500">{t('app.candidate_card.documents.empty', { defaultValue: 'No document data.' })}</div>
            )}
          </div>
        )}
      </div>

      {onOpenDocs ? (
        <div className="mt-2">
          <button type="button" className="btn-secondary btn-sm w-full" onClick={onOpenDocs}>
            {t('app.candidate_card.docs_panel.open_full', { defaultValue: 'Open full' })}
          </button>
        </div>
      ) : null}

      {/* WHAT BLOCKS THIS CANDIDATE */}
      <div className={clsx('mt-3 rounded-xl border p-3', hasBlockers ? 'border-rose-200 bg-rose-50' : 'border-slate-200 bg-slate-50')}>
        <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-700">
          {t('app.candidate_card.documents.what_blocks_title', { defaultValue: 'What blocks this candidate' })}
        </div>

        {hasBlockers ? (
          <div className="mt-2 space-y-2">
            <div>
              <div className="text-xs font-semibold text-rose-800">
                {t('app.candidate_card.documents.missing_label', { defaultValue: 'Missing' })}
              </div>
              <ul className="mt-1 space-y-1">
                {[...missing, ...problematic].slice(0, 8).map((code) => (
                  <li key={code} className="text-xs text-rose-800">
                    {labelForType(code)}
                  </li>
                ))}
              </ul>
            </div>

            <div className="text-xs text-rose-900">
              {t('app.candidate_card.documents.next_step', { defaultValue: 'Next step: → Request documents' })}
            </div>
          </div>
        ) : (
          <div className="mt-2 text-xs text-slate-700">
            {t('app.candidate_card.documents.no_blocks', { defaultValue: 'No missing/problematic documents.' })}
          </div>
        )}
      </div>
    </section>
  )
}

