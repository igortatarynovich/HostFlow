import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import CandidateDocsRailPanel, {
  type CandidateDocsRailEmbeddedDocumentsSummary,
} from '../../../components/candidate/CandidateDocsRailPanel'
import type { CandidatesWorkPanelCommsLinks } from '../hooks/useCandidatesWorkPanelPreview'
import CandidateHandoffSection from '../../../components/candidate/CandidateHandoffSection'
import CandidateNextActionPanel from '../../../components/candidate/CandidateNextActionPanel'
import CandidateRemindersSection from '../../../components/candidate/CandidateRemindersSection'
import { Modal } from '../../../components/Modal'
import { isCandidateOperationallyTerminal } from '../../../utils/candidatePipelineCompleted'
import StageTag from '../../../components/StageTag'
import {
  docsIssuesPresent,
  docsPipelineBlocksForward,
  pipelineRelaxedRequirementsFromOverrides,
  relaxRequirementBlockers,
} from '../../../utils/candidateStageDocPolicy'
import CandidateRequirementsWorkPanelPreview from '../../../components/candidate/CandidateRequirementsWorkPanelPreview'
import type { CandidatePipelineOverride } from '../../../api/candidatePipelineOverrides'
import type { WorkPanelRequirementsSummary } from '../../../utils/workPanelRequirements'
import { canonicalStageKey } from '../../../utils/stageLabels'
import { formatDateSafe } from '../candidateUtils'
import EntityCorrespondenceOpen from '../../../components/communications/EntityCorrespondenceOpen'
import { buildInboxHubPath } from '../../../utils/inboxDeepLinks'
import type { FriendlyErrorInfo } from '../../../utils/friendlyError'

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
  previewRemindersError: FriendlyErrorInfo | null
  previewReminderBusy: string | null
  previewReminderTitle: string
  previewReminderDueAt: string
  previewReminderOffset: number
  /** Bumped from list context menu to expand next-action editor in preview. */
  nextActionDetailsOpenTrigger: number
  docsBlockers: { missing: string[]; problematic: string[]; inProgress: string[] }
  docsBlockersLoading: boolean
  usesRequirementBlockers?: boolean
  previewRequirementsSummary?: WorkPanelRequirementsSummary | null
  previewPipelineOverrides?: CandidatePipelineOverride[]
  docsRailEmbeddedSummary: CandidateDocsRailEmbeddedDocumentsSummary
  canUseTeamWorkPanelAssigneeScope: boolean
  workPanelAssigneeScope: 'mine' | 'team'
  onWorkPanelAssigneeScopeChange: (scope: 'mine' | 'team') => void
  docsOwnerContext: any
  previewTimelineItems: TimelineItem[]
  previewTimelineLoading: boolean
  previewTimelineError: FriendlyErrorInfo | null
  previewTimelineExpanded: boolean
  previewTimelineCollapsedCount: number
  onClose: () => void
  onOpenCandidate: (candidateId: string) => void
  onOpenDocuments: (candidateId: string) => void
  workPanelCommsLinks: CandidatesWorkPanelCommsLinks | null
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
  usesRequirementBlockers = false,
  previewRequirementsSummary = null,
  previewPipelineOverrides = [],
  docsRailEmbeddedSummary,
  canUseTeamWorkPanelAssigneeScope,
  workPanelAssigneeScope,
  onWorkPanelAssigneeScopeChange,
  docsOwnerContext,
  previewTimelineItems,
  previewTimelineLoading,
  previewTimelineError,
  previewTimelineExpanded,
  previewTimelineCollapsedCount,
  onClose,
  onOpenCandidate,
  onOpenDocuments,
  workPanelCommsLinks,
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
  const navigate = useNavigate()
  const [reminderModalOpen, setReminderModalOpen] = useState(false)

  useEffect(() => {
    if (nextActionDetailsOpenTrigger > 0) setReminderModalOpen(true)
  }, [nextActionDetailsOpenTrigger])

  const stageCode = selectedCandidate
    ? String(selectedCandidate?.stage || '').trim() || null
    : null

  // Hooks must run every render — never place `return` above them (React #310 when selection appears).
  const relaxedRequirements = useMemo(
    () => pipelineRelaxedRequirementsFromOverrides(previewPipelineOverrides),
    [previewPipelineOverrides],
  )

  const effectiveBlockers = useMemo(
    () =>
      usesRequirementBlockers
        ? relaxRequirementBlockers(docsBlockers, relaxedRequirements)
        : docsBlockers,
    [docsBlockers, relaxedRequirements, usesRequirementBlockers],
  )

  const docsIssues = useMemo(
    () =>
      selectedCandidate ? docsIssuesPresent(effectiveBlockers, docsBlockersLoading) : false,
    [selectedCandidate, effectiveBlockers, docsBlockersLoading],
  )
  const docsPipelineBlocking = useMemo(
    () =>
      selectedCandidate && stageCode
        ? docsPipelineBlocksForward(stageCode, effectiveBlockers, docsBlockersLoading)
        : false,
    [selectedCandidate, stageCode, effectiveBlockers, docsBlockersLoading],
  )

  if (!selectedCandidate) return null

  const cid = String(selectedCandidate.id)
  const messagesHref =
    workPanelCommsLinks?.messagesRelativeUrl ?? buildInboxHubPath({ candidateId: cid, channel: 'messages' })
  const emailHref =
    workPanelCommsLinks?.emailRelativeUrl ?? buildInboxHubPath({ candidateId: cid, channel: 'email' })

  const canonicalStageForOps = stageCode ? canonicalStageKey(stageCode, null) || stageCode.toLowerCase() : null
  const previewOperationallyTerminal = isCandidateOperationallyTerminal({
    stage: selectedCandidate?.stage,
    row_status: selectedCandidate?.row_status,
    status: selectedCandidate?.status,
  })

  return (
    <section className="space-y-2 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
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
            <p className="mt-0.5 line-clamp-2 text-[10px] leading-snug text-slate-400">
              {t('app.candidates.preview.stage_scope_hint', {
                defaultValue: 'Stage changes, journey, and compliance gates — in the full card.',
              })}
            </p>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          {canUseTeamWorkPanelAssigneeScope ? (
            <div
              className="inline-flex rounded-lg border border-slate-200 bg-slate-50/80 p-0.5"
              role="group"
              aria-label={t('app.candidates.preview.reminders_assignee_scope', {
                defaultValue: 'Reminder scope for this candidate',
              })}
            >
              <button
                type="button"
                className={clsx(
                  'rounded-md px-2 py-1 text-[10px] font-medium transition-colors',
                  workPanelAssigneeScope === 'mine'
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'text-slate-600 hover:bg-white/80',
                )}
                onClick={() => onWorkPanelAssigneeScopeChange('mine')}
              >
                {t('app.reminders.assignee.mine', { defaultValue: 'My tasks' })}
              </button>
              <button
                type="button"
                className={clsx(
                  'rounded-md px-2 py-1 text-[10px] font-medium transition-colors',
                  workPanelAssigneeScope === 'team'
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'text-slate-600 hover:bg-white/80',
                )}
                onClick={() => onWorkPanelAssigneeScopeChange('team')}
              >
                {t('app.reminders.assignee.team', { defaultValue: 'Team tasks' })}
              </button>
            </div>
          ) : null}
          <button type="button" className="btn-secondary h-8 rounded-lg px-2 text-xs" onClick={onClose}>
            {t('common.actions.close', { defaultValue: 'Close' })}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-primary btn-xs" onClick={() => onOpenCandidate(String(selectedCandidate.id))}>
          {t('common.actions.open', { defaultValue: 'Open' })}
        </button>
        <button type="button" className="btn-secondary btn-xs" onClick={() => onOpenDocuments(String(selectedCandidate.id))}>
          {t('app.nav.items.documents', { defaultValue: 'Documents' })}
        </button>
        <button
          type="button"
          className="btn-secondary btn-xs border-brand-200 bg-brand-50/80 font-semibold text-brand-900 hover:bg-brand-100"
          onClick={() => setReminderModalOpen(true)}
        >
          {t('app.candidates.preview.reminders_button', { defaultValue: 'Reminders' })}
        </button>
      </div>

      {!previewOperationallyTerminal && typeof (selectedCandidate as any).risk_score === 'number' ? (
        <div className="space-y-1.5 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            {t('app.candidates.preview.risk_title', { defaultValue: 'Risk (v1)' })}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {(() => {
              const score = (selectedCandidate as any).risk_score as number
              const bandRaw = String((selectedCandidate as any).risk_band || '')
              const band =
                bandRaw ||
                (score >= 85 ? 'critical' : score >= 65 ? 'high' : score >= 35 ? 'medium' : 'low')
              const badgeCls =
                band === 'critical'
                  ? 'bg-red-50 text-red-800 border-red-200'
                  : band === 'high'
                    ? 'bg-rose-50 text-rose-800 border-rose-200'
                    : band === 'medium'
                      ? 'bg-amber-50 text-amber-900 border-amber-200'
                      : 'bg-slate-100 text-slate-700 border-slate-200'
              const bandLabel =
                band === 'critical'
                  ? t('app.candidates.risk.band_critical', { defaultValue: 'Critical' })
                  : band === 'high'
                    ? t('app.candidates.risk.band_high', { defaultValue: 'High' })
                    : band === 'medium'
                      ? t('app.candidates.risk.band_medium', { defaultValue: 'Medium' })
                      : t('app.candidates.risk.band_low', { defaultValue: 'Low' })
              return (
                <>
                  <span
                    className={clsx('text-[11px] rounded border px-2 py-0.5 font-medium', badgeCls)}
                    title={Array.isArray((selectedCandidate as any).risk_drivers) ? (selectedCandidate as any).risk_drivers.join(' · ') : undefined}
                  >
                    {bandLabel}
                  </span>
                  <span className="text-[11px] font-mono text-slate-600">{score}</span>
                  {(selectedCandidate as any).risk_version ? (
                    <span className="text-[10px] text-slate-400">{(selectedCandidate as any).risk_version}</span>
                  ) : null}
                </>
              )
            })()}
          </div>
          {Array.isArray((selectedCandidate as any).risk_drivers) && (selectedCandidate as any).risk_drivers.length ? (
            <ul className="list-inside list-disc text-[11px] leading-snug text-slate-600">
              {(selectedCandidate as any).risk_drivers.slice(0, 4).map((line: string, i: number) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          ) : null}
          {(selectedCandidate as any).risk_score >= 35 ? (
            <p className="text-[11px] leading-snug text-amber-900/90">
              {t('app.candidates.preview.risk_nudge', {
                defaultValue: 'Elevated risk — review next action, response time, and stage stagnation.',
              })}
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="space-y-2">
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
          reminderEditorInModal
          onReminderModalOpenChange={setReminderModalOpen}
          onReminderTitleChange={onReminderTitleChange}
          onReminderDueAtChange={onReminderDueAtChange}
          onReminderOffsetChange={onReminderOffsetChange}
          onReminderCreate={onReminderCreate}
          onReminderComplete={onReminderComplete}
          onReminderSnooze={onReminderSnooze}
          operationallyTerminal={previewOperationallyTerminal}
          docsIssuesPresent={!selectedCandidate.masked && docsIssues}
          docsPipelineBlocking={!selectedCandidate.masked && docsPipelineBlocking}
          docsRequestDueLabel={t('common.today', { defaultValue: 'Today' })}
          onDocsRequestCreate={onDocsRequestCreate}
          hideToggle
          canonicalStageCode={canonicalStageForOps}
          documentsChecklistSibling={!selectedCandidate.masked}
        />

        {!selectedCandidate.masked ? (
          <>
            {usesRequirementBlockers ? (
              <CandidateRequirementsWorkPanelPreview
                items={previewRequirementsSummary?.items ?? []}
                loading={docsBlockersLoading}
              />
            ) : null}
            <CandidateDocsRailPanel
              key={`docs-rail:${selectedCandidate.id}`}
              candidateId={String(selectedCandidate.id)}
              embeddedDocumentsSummary={docsRailEmbeddedSummary}
              ownerContext={docsOwnerContext}
              uploadBusy={false}
              onUpload={() => onOpenDocuments(String(selectedCandidate.id))}
              suppressBlockerCallbacks={usesRequirementBlockers}
              onLoadedBlockers={
                usesRequirementBlockers
                  ? undefined
                  : (b) =>
                      onDocsLoadedBlockers({
                        missing: b.missing,
                        problematic: b.problematic,
                        inProgress: b.inProgress,
                      })
              }
              onLoadingChange={onDocsLoadingChange}
              refreshTrigger={0}
              onSelectType={(typeCode) => onDocsSelectType(String(selectedCandidate.id), typeCode)}
              pollingEnabled={false}
              stageSummaryLabel={stageSummaryLabel}
              docsPipelineBlocking={!selectedCandidate.masked && docsPipelineBlocking}
              blockersPresentation={previewOperationallyTerminal ? 'historical' : 'operational'}
              hideDocumentTypeChecklist={usesRequirementBlockers}
            />
          </>
        ) : null}

        <div className="space-y-1.5">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            {t('app.candidates.preview.comms_title', { defaultValue: 'Comms' })}
          </div>
          <EntityCorrespondenceOpen
            refs={[{ entityType: 'candidate', entityId: cid }]}
            candidateId={cid}
            className="btn-secondary btn-xs inline-flex w-full items-center justify-center gap-1"
            testId="candidates-panel-correspondence"
          />
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary btn-xs min-w-[7.5rem] flex-1"
              onClick={() => navigate(messagesHref)}
            >
              {t('app.candidate_card.control.open_messages', { defaultValue: 'Messages' })}
            </button>
            <button type="button" className="btn-secondary btn-xs min-w-[7.5rem] flex-1" onClick={() => navigate(emailHref)}>
              {t('app.nav.items.email', { defaultValue: 'Email' })}
            </button>
          </div>
        </div>
      </div>

      <div className="space-y-1.5 text-xs">
        <div className="rounded-lg border border-slate-200 bg-white p-2.5">
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
                {t('common.actions.refresh')}
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
            <div className="mt-2 rounded border border-rose-200 bg-rose-50 p-2 text-[11px] text-rose-700">
              <div>{previewTimelineError.title}</div>
              {previewTimelineError.detail ? (
                <div className="mt-0.5 text-[10px] text-rose-800/90">{previewTimelineError.detail}</div>
              ) : null}
            </div>
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

      <Modal
        open={reminderModalOpen}
        onClose={() => setReminderModalOpen(false)}
        title={t('app.candidates.preview.reminders_modal_title', {
          defaultValue: 'Reminders for this candidate',
        })}
        size="lg"
      >
        <p className="mb-4 text-sm text-slate-600">
          {t('app.candidates.preview.reminders_modal_hint', {
            defaultValue: 'Set a due time, save, and return to the list — without scrolling the preview.',
          })}
        </p>
        <CandidateRemindersSection
          candidateId={cid}
          reminders={previewReminders}
          remindersLoading={previewRemindersLoading}
          remindersError={previewRemindersError}
          reminderBusy={previewReminderBusy}
          reminderTitle={previewReminderTitle}
          reminderDueAt={previewReminderDueAt}
          reminderOffset={previewReminderOffset}
          onReminderTitleChange={onReminderTitleChange}
          onReminderDueAtChange={onReminderDueAtChange}
          onReminderOffsetChange={onReminderOffsetChange}
          onReminderCreate={onReminderCreate}
          onReminderComplete={onReminderComplete}
          onReminderSnooze={onReminderSnooze}
          embedded
        />
      </Modal>
    </section>
  )
}
