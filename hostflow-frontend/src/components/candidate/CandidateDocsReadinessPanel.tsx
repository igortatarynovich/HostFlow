import { useMemo } from 'react'
import clsx from 'clsx'
import { useI18n } from '../../i18n'
import { DOC_READINESS_META } from '../../modules/candidates/constants'
import { deriveDocsMeta } from '../../modules/candidates/utils'
import { sanitizeDocsProgress } from '../../modules/candidates/candidateUtils'

export default function CandidateDocsReadinessPanel({
  candidate,
  onOpenDocs,
}: {
  candidate: any
  onOpenDocs?: () => void
}) {
  const { t } = useI18n()

  const docsMeta = useMemo(() => {
    // `deriveDocsMeta` expects a UICandidate-like shape; CandidateCard model is close enough.
    return deriveDocsMeta(candidate as any)
  }, [candidate])

  const counts = useMemo(() => {
    const p = sanitizeDocsProgress((candidate as any)?.docs_progress)
    const total = Number(p.total ?? p.count ?? 0) || 0
    const ready = Number(p.ready ?? p.verified ?? p.approved ?? 0) || 0
    const problem = Number(p.problem ?? p.invalid ?? p.expired ?? p.overdue ?? 0) || 0
    const inProgress = Number(p.in_progress ?? p.submitted ?? p.pending_validation ?? 0) || 0
    const ordered = Number(p.ordered ?? p.requested ?? p.pending ?? p.ordered_count ?? 0) || 0
    const withFiles = Number(p.with_files ?? p.uploaded ?? p.files ?? p.files_count ?? 0) || 0
    return { total, ready, problem, inProgress, ordered, withFiles }
  }, [candidate])

  const badge = DOC_READINESS_META[docsMeta.readinessKey] ?? DOC_READINESS_META.pending
  const readinessLabel = t(docsMeta.readinessLabelKey, { defaultValue: docsMeta.readinessKey })

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold text-slate-700">
            {t('app.candidate_card.docs_readiness.title', { defaultValue: 'Docs readiness' })}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className={clsx('inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold', badge.className)}>
              {readinessLabel}
            </span>
            {counts.total > 0 ? (
              <span className="text-[11px] text-slate-500">
                {t('app.candidate_card.docs_readiness.counts', {
                  defaultValue: '{ready}/{total} ready',
                  values: { ready: counts.ready, total: counts.total },
                })}
              </span>
            ) : (
              <span className="text-[11px] text-slate-500">{t('common.labels.not_available')}</span>
            )}
          </div>
        </div>

        {onOpenDocs ? (
          <button type="button" className="btn-secondary btn-sm" onClick={onOpenDocs}>
            {t('app.candidate_card.docs_readiness.open', { defaultValue: 'Open checklist' })}
          </button>
        ) : null}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-2 py-1.5">
          <div className="text-[10px] uppercase tracking-wide text-slate-500">
            {t('app.candidate_card.docs_readiness.ready', { defaultValue: 'Ready' })}
          </div>
          <div className="text-lg font-semibold leading-tight text-slate-900">{counts.ready}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-2 py-1.5">
          <div className="text-[10px] uppercase tracking-wide text-slate-500">
            {t('app.candidate_card.docs_readiness.in_progress', { defaultValue: 'In progress' })}
          </div>
          <div className="text-lg font-semibold leading-tight text-slate-900">{counts.inProgress}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-2 py-1.5">
          <div className="text-[10px] uppercase tracking-wide text-slate-500">
            {t('app.candidate_card.docs_readiness.problem', { defaultValue: 'Problems' })}
          </div>
          <div className="text-lg font-semibold leading-tight text-slate-900">{counts.problem}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-2 py-1.5">
          <div className="text-[10px] uppercase tracking-wide text-slate-500">
            {t('app.candidate_card.docs_readiness.files', { defaultValue: 'Files' })}
          </div>
          <div className="text-lg font-semibold leading-tight text-slate-900">{counts.withFiles}</div>
        </div>
      </div>
    </section>
  )
}

