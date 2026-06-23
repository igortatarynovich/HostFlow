import { useMemo, useState } from 'react'
import clsx from 'clsx'
import { useI18n } from '../../i18n'
import { DOC_READINESS_META } from '../../modules/candidates/constants'
import { deriveDocsMeta } from '../../modules/candidates/utils'
import { sanitizeDocsProgress } from '../../modules/candidates/candidateUtils'
import CandidateDocsChecklistMiniPanel from './CandidateDocsChecklistMiniPanel'
import CandidateDocsWorkspacePanel from './CandidateDocsWorkspacePanel'
import type { CandidateProfile } from '../../api/candidate_profiles'
import { useCandidateRuntimeWorkspace } from '../../hooks/useCandidateRuntimeWorkspace'

export default function CandidateDocsPanel({
  candidate,
  candidateProfile,
  isNew,
  isMasked,
  variant = 'full',
  ownerContext,
  uploadingBusy,
  exportingBusy,
  onCreateUploadLink,
  onExportBundle,
  onOpenDocsTab,
}: {
  candidate: any
  candidateProfile?: CandidateProfile | null
  isNew: boolean
  isMasked: boolean
  variant?: 'full' | 'compact'
  ownerContext?: Record<string, any>
  uploadingBusy?: boolean
  exportingBusy?: boolean
  onCreateUploadLink?: () => void
  onExportBundle?: () => void
  onOpenDocsTab?: () => void
}) {
  const { t } = useI18n()
  const [mode, setMode] = useState<'blockers' | 'workspace'>('blockers')

  const candidateId = String((candidate as { id?: string })?.id || '')
  const { workspace } = useCandidateRuntimeWorkspace({
    candidateId,
    ownerContext: ownerContext || null,
    enabled: Boolean(candidateId) && !isMasked,
  })

  const docsMeta = useMemo(() => deriveDocsMeta(candidate as any), [candidate])
  const runtimeReadiness = workspace
    ? DOC_READINESS_META[workspace.readinessKey] ?? DOC_READINESS_META.pending
    : null
  const badge = runtimeReadiness ?? DOC_READINESS_META[docsMeta.readinessKey] ?? DOC_READINESS_META.pending
  const readinessLabel = t(
    runtimeReadiness?.labelKey ?? docsMeta.readinessLabelKey,
    { defaultValue: workspace?.readinessKey ?? docsMeta.readinessKey },
  )

  const counts = useMemo(() => {
    if (workspace) {
      const problem = workspace.items.filter((item) =>
        ['missing', 'rejected', 'expired'].includes(item.badge.badge),
      ).length
      const inProgress = workspace.items.filter((item) => item.badge.badge === 'pending').length
      return {
        total: workspace.totalRequired,
        ready: workspace.satisfiedCount,
        problem,
        inProgress,
        withFiles: 0,
      }
    }
    const p = sanitizeDocsProgress((candidate as any)?.docs_progress)
    const total = Number(p.total ?? p.count ?? 0) || 0
    const ready = Number(p.ready ?? p.verified ?? p.approved ?? 0) || 0
    const problem = Number(p.problem ?? p.invalid ?? p.expired ?? p.overdue ?? 0) || 0
    const inProgress = Number(p.in_progress ?? p.submitted ?? p.pending_validation ?? 0) || 0
    const withFiles = Number(p.with_files ?? p.uploaded ?? p.files ?? p.files_count ?? 0) || 0
    return { total, ready, problem, inProgress, withFiles }
  }, [candidate, workspace])

  const pct = useMemo(() => {
    if (workspace) return workspace.percentReady
    const total = counts.total || 0
    if (!total) return 0
    return Math.max(0, Math.min(100, Math.round((counts.ready / total) * 100)))
  }, [counts.ready, counts.total, workspace])

  if (isMasked) return null

  return (
    <section
      className={clsx(
        'rounded-2xl border border-slate-200 bg-white p-3',
        variant === 'full' && 'flex flex-col',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold text-slate-800">
            {t('app.candidate_card.docs_panel.title', { defaultValue: 'Documents' })}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className={clsx('inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold', badge.className)}>
              {readinessLabel}
            </span>
            {counts.total ? (
              <span className="text-[11px] text-slate-500">
                {workspace
                  ? t('app.candidate_card.docs_panel.runtime_kpi', {
                      defaultValue: '{ready}/{total} satisfied · {problem} blockers · {percent}%',
                      values: {
                        ready: counts.ready,
                        total: counts.total,
                        problem: counts.problem,
                        percent: pct,
                      },
                    })
                  : t('app.candidate_card.docs_panel.kpi', {
                      defaultValue: '{ready}/{total} ready · {problem} issues · {files} files',
                      values: { ready: counts.ready, total: counts.total, problem: counts.problem, files: counts.withFiles },
                    })}
              </span>
            ) : (
              <span className="text-[11px] text-slate-500">{t('common.labels.not_available')}</span>
            )}
          </div>

          <div className="mt-2 h-2 w-full rounded-full bg-slate-100 overflow-hidden">
            <div
              className={clsx('h-full rounded-full', pct >= 90 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-rose-500')}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {onOpenDocsTab ? (
          <button type="button" className="btn-secondary btn-sm" onClick={onOpenDocsTab}>
            {t('app.candidate_card.docs_panel.open_full', { defaultValue: 'Open full' })}
          </button>
        ) : null}
      </div>

      {variant === 'compact' ? (
        <div className="mt-3">
          <CandidateDocsChecklistMiniPanel
            candidateId={String((candidate as any)?.id || '')}
            ownerContext={ownerContext || null}
            onOpenDocs={onOpenDocsTab}
          />
        </div>
      ) : (
        <>
          <div className="mt-3 flex items-center gap-1 rounded-xl border border-slate-200 bg-slate-50 p-1">
            {(
              [
                ['blockers', t('app.candidate_card.docs_panel.tabs.blockers', { defaultValue: 'Blockers' })],
                ['workspace', t('app.candidate_card.docs_panel.tabs.workspace', { defaultValue: 'Workspace' })],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                className={clsx(
                  'px-2.5 py-1.5 text-xs font-semibold rounded-lg',
                  mode === key
                    ? 'bg-white border border-slate-200 text-slate-900'
                    : 'text-slate-600 hover:text-slate-800',
                )}
                onClick={() => setMode(key)}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="mt-3 flex-1">
            {mode === 'blockers' ? (
              <CandidateDocsChecklistMiniPanel
                candidateId={String((candidate as any)?.id || '')}
                ownerContext={ownerContext || null}
                onOpenDocs={onOpenDocsTab}
              />
            ) : (
              <CandidateDocsWorkspacePanel
                candidateId={String((candidate as any)?.id || '')}
                candidateProfile={candidateProfile}
                ownerContext={ownerContext || {}}
                isNew={isNew}
                disabled={false}
                uploadingBusy={uploadingBusy}
                exportingBusy={exportingBusy}
                onCreateUploadLink={onCreateUploadLink}
                onExportBundle={onExportBundle}
              />
            )}
          </div>
        </>
      )}
    </section>
  )
}

