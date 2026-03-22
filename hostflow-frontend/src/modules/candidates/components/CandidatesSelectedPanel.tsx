import { useMemo } from 'react'
import CandidateDocsRailPanel from '../../../components/candidate/CandidateDocsRailPanel'
import CandidateHandoffSection from '../../../components/candidate/CandidateHandoffSection'
import CandidateNextActionPanel from '../../../components/candidate/CandidateNextActionPanel'
import StageTag from '../../../components/StageTag'
import { docsIssuesPresent, docsPipelineBlocksForward } from '../../../utils/candidateStageDocPolicy'
import { canonicalStageKey } from '../../../utils/stageLabels'
import { formatDateSafe } from '../candidateUtils'

type TimelineItem = {
  at: string
  kind: string
  source: string
  title?: string | null
  description?: string | null
}

type CandidatesSelectedPanelProps = {
  t: (key: string, options?: any) => string
  locale: string
  selectedCandidate: any | null
  selectedCandidateId: string | null
  /** Human-readable current stage for document blocker context */
  stageSummaryLabel?: string | null
  previewReminders: any[]
  previewRemindersLoading: boolean
  previewRemindersError: string | null
  previewReminderBusy: string | null
  previewReminderTitle: string
  previewReminderDueAt: string
  previewReminderOffset: number
  nextActionDetailsOpenTrigger: number
  docsBlockers: { missing: string[]; problematic: string[]; inProgress: string[] }
  docsBlockersLoading: boolean
  docsOwnerContext: any
  previewTimelineItems: TimelineItem[]
  previewTimelineLoading: boolean
  previewTimelineError: string | null
  previewTimelineExpanded: boolean
  previewTimelineCollapsedCount: number
  onClose: () => void
  onOpenCandidate: (candidateId: string) => void
  onOpenDocuments: (candidateId: string) => void
  onOpenMessages: (candidateId: string) => void
  onReminderTitleChange: (value: string) => void
  onReminderDueAtChange: (value: string) => void
  onReminderOffsetChange: (value: number) => void
  onReminderCreate: () => void
  onReminderComplete: (id: string) => void
  onReminderSnooze: (id: string, minutes: number) => void
  onDocsRequestCreate: () => void
  onDocsLoadedBlockers: (value: { missing: string[]; problematic: string[]; inProgress: string[] }) => void
  onDocsLoadingChange: (value: boolean) => void
  onDocsSelectType: (candidateId: string, typeCode: string) => void
  onTimelineRefresh: (candidateId: string) => void
  onTimelineExpandedChange: (updater: (prev: boolean) => boolean) => void
}

export function CandidatesSelectedPanel({
  t,
  locale,
  selectedCandidate,
  selectedCandidateId,
  stageSummaryLabel,
  previewReminders,
  previewRemindersLoading,
  previewRemindersError,
  previewReminderBusy,
  previewReminderTitle,
  previewReminderDueAt,
  previewReminderOffset,
  nextActionDetailsOpenTrigger,
  docsBlockers,
  docsBlockersLoading,
  docsOwnerContext,
  previewTimelineItems,
  previewTimelineLoading,
  previewTimelineError,
  previewTimelineExpanded,
  previewTimelineCollapsedCount,
  onClose,
  onOpenCandidate,
  onOpenDocuments,
  onOpenMessages,
  onReminderTitleChange,
  onReminderDueAtChange,
  onReminderOffsetChange,
  onReminderCreate,
  onReminderComplete,
  onReminderSnooze,
  onDocsRequestCreate,
  onDocsLoadedBlockers,
  onDocsLoadingChange,
  onDocsSelectType,
  onTimelineRefresh,
  onTimelineExpandedChange,
}: CandidatesSelectedPanelProps) {
  if (!selectedCandidate) return null

  const stageCode = String(selectedCandidate?.stage || '').trim() || null
  const canonicalStageForOps = stageCode ? canonicalStageKey(stageCode, null) || stageCode.toLowerCase() : null
  const docsIssues = useMemo(
    () => docsIssuesPresent(docsBlockers, docsBlockersLoading),
    [docsBlockers, docsBlockersLoading],
  )
  const docsPipelineBlocking = useMemo(
    () => docsPipelineBlocksForward(stageCode, docsBlockers, docsBlockersLoading),
    [stageCode, docsBlockers, docsBlockersLoading],
  )

  return (
    <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-slate-900">
            {selectedCandidate.masked === true
              ? selectedCandidate.short_id
                ? t('app.candidates.table.masked_label_short_id', {
                    defaultValue: 'Кандидат {short_id}',
                    values: { short_id: selectedCandidate.short_id },
                  })
                : t('app.candidates.table.masked_label', {
                    defaultValue: 'Кандидат #{id}',
                    values: { id: (selectedCandidate.id ?? '').slice(0, 8) },
                  })
              : `${selectedCandidate.first_name ?? ''} ${selectedCandidate.last_name ?? ''}`.trim() || t('common.labels.not_available')}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <StageTag code={selectedCandidate.stage} />
            <span className="text-[11px] text-slate-500">
              {(selectedCandidate as any).__extra?.companyName || (selectedCandidate as any).company_name || '—'}
            </span>
          </div>
          {selectedCandidate.masked !== true ? (
            <p className="mt-1 text-[10px] leading-snug text-slate-400">
              {t('app.candidates.preview.stage_scope_hint', {
                defaultValue: 'Stage changes, journey, and compliance gates — in the full card.',
              })}
            </p>
          ) : null}
        </div>
        <button type="button" className="btn-secondary h-8 rounded-lg px-2 text-xs" onClick={onClose}>
          {t('common.actions.close', { defaultValue: 'Close' })}
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-primary btn-xs" onClick={() => onOpenCandidate(String(selectedCandidate.id))}>
          {t('common.actions.open', { defaultValue: 'Open' })}
        </button>
        <button type="button" className="btn-secondary btn-xs" onClick={() => onOpenDocuments(String(selectedCandidate.id))}>
          {t('app.nav.items.documents', { defaultValue: 'Documents' })}
        </button>
      </div>

      <div className="space-y-3">
        <CandidateNextActionPanel
          candidateId={String(selectedCandidate.id)}
          reminders={previewReminders}
          remindersLoading={previewRemindersLoading}
          remindersError={previewRemindersError}
          reminderBusy={previewReminderBusy}
          reminderTitle={previewReminderTitle}
          reminderDueAt={previewReminderDueAt}
          reminderOffset={previewReminderOffset}
          detailsOpenTrigger={nextActionDetailsOpenTrigger}
          onReminderTitleChange={onReminderTitleChange}
          onReminderDueAtChange={onReminderDueAtChange}
          onReminderOffsetChange={onReminderOffsetChange}
          onReminderCreate={onReminderCreate}
          onReminderComplete={onReminderComplete}
          onReminderSnooze={onReminderSnooze}
          docsIssuesPresent={!selectedCandidate.masked && docsIssues}
          docsPipelineBlocking={!selectedCandidate.masked && docsPipelineBlocking}
          docsRequestDueLabel={t('common.today', { defaultValue: 'Today' })}
          onDocsRequestCreate={onDocsRequestCreate}
          hideToggle
          canonicalStageCode={canonicalStageForOps}
        />

        {!selectedCandidate.masked ? (
          <CandidateDocsRailPanel
            key={`docs-rail:${selectedCandidate.id}`}
            candidateId={String(selectedCandidate.id)}
            ownerContext={docsOwnerContext}
            uploadBusy={false}
            onUpload={() => onOpenDocuments(String(selectedCandidate.id))}
            onLoadedBlockers={(b) =>
              onDocsLoadedBlockers({ missing: b.missing, problematic: b.problematic, inProgress: b.inProgress })
            }
            onLoadingChange={onDocsLoadingChange}
            refreshTrigger={0}
            onSelectType={(typeCode) => onDocsSelectType(String(selectedCandidate.id), typeCode)}
            pollingEnabled={false}
            stageSummaryLabel={stageSummaryLabel}
            docsPipelineBlocking={!selectedCandidate.masked && docsPipelineBlocking}
          />
        ) : null}

        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-secondary btn-xs w-full" onClick={() => onOpenMessages(String(selectedCandidate.id))}>
            {t('app.candidate_card.control.open_messages', { defaultValue: 'Messages' })}
          </button>
        </div>
      </div>

      <div className="space-y-2 text-xs">
        <div className="rounded-lg border border-slate-200 bg-white p-3">
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold text-slate-700">
              {t('app.candidates.preview.timeline_title', { defaultValue: 'Timeline' })}
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="btn-secondary h-7 rounded-lg px-2 text-[11px]"
                onClick={() => selectedCandidateId && onTimelineRefresh(selectedCandidateId)}
              >
                {t('common.actions.refresh', { defaultValue: 'Refresh' })}
              </button>
              {previewTimelineItems.length > previewTimelineCollapsedCount ? (
                <button
                  type="button"
                  className="btn-secondary h-7 rounded-lg px-2 text-[11px]"
                  onClick={() => onTimelineExpandedChange((v) => !v)}
                >
                  {previewTimelineExpanded
                    ? t('common.actions.collapse', { defaultValue: 'Hide' })
                    : t('common.actions.expand', { defaultValue: 'Show more' })}
                </button>
              ) : null}
            </div>
          </div>

          {previewTimelineLoading ? (
            <div className="py-3 text-center text-[11px] text-slate-500">{t('common.loading')}</div>
          ) : previewTimelineError ? (
            <div className="mt-2 rounded border border-rose-200 bg-rose-50 p-2 text-[11px] text-rose-700">{previewTimelineError}</div>
          ) : previewTimelineItems.length === 0 ? (
            <div className="mt-2 rounded border border-slate-200 bg-slate-50 p-2 text-[11px] text-slate-500">
              {t('app.candidates.preview.timeline_empty', { defaultValue: 'No events yet.' })}
            </div>
          ) : (
            <ul className="mt-2 space-y-1.5">
              {(previewTimelineExpanded ? previewTimelineItems : previewTimelineItems.slice(0, previewTimelineCollapsedCount)).map((ev, idx) => (
                <li key={`${ev.at}-${ev.kind}-${idx}`} className="flex items-start gap-2">
                  <div className="mt-[3px] h-1.5 w-1.5 rounded-full bg-slate-400" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <div className="truncate text-[11px] font-medium text-slate-800">
                        {ev.title || ev.kind || t('app.candidates.preview.event', { defaultValue: 'Event' })}
                      </div>
                      <div className="shrink-0 text-[10px] text-slate-500">{formatDateSafe(ev.at, locale) || ev.at}</div>
                    </div>
                    {ev.description ? <div className="mt-0.5 text-[11px] text-slate-600 truncate">{ev.description}</div> : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <CandidateHandoffSection candidateId={String(selectedCandidate.id)} />
    </section>
  )
}
