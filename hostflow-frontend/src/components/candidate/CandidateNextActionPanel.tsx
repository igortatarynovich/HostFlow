import { useCallback, useEffect, useMemo, useState } from 'react'
import clsx from 'clsx'
import type { ReminderRecord } from '../../api/types'
import { useI18n } from '../../i18n'
import CandidateRemindersSection from './CandidateRemindersSection'
import {
  operationalHintForStageResolved,
  type StageOperationalHintKind,
} from '../../utils/stageOperationalHints'
import { isPipelineCompletedCanonicalStage } from '../../utils/candidatePipelineCompleted'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'

function parseTs(value?: string | null): number {
  if (!value) return 0
  const ts = Date.parse(String(value))
  return Number.isNaN(ts) ? 0 : ts
}

function pickNextAction(reminders: ReminderRecord[], nowTs: number): ReminderRecord | null {
  const active = reminders.filter((r) => r && r.status !== 'done' && r.status !== 'cancelled')
  if (!active.length) return null
  // Prefer overdue by status or due_at in past, then soonest due
  active.sort((a, b) => {
    const aDue = parseTs(a.due_at)
    const bDue = parseTs(b.due_at)
    const aOver = a.status === 'overdue' || (aDue > 0 && aDue < nowTs)
    const bOver = b.status === 'overdue' || (bDue > 0 && bDue < nowTs)
    if (aOver !== bOver) return aOver ? -1 : 1
    if (aDue !== bDue) return (aDue || Number.MAX_SAFE_INTEGER) - (bDue || Number.MAX_SAFE_INTEGER)
    return String(a.id).localeCompare(String(b.id))
  })
  return active[0] ?? null
}

export default function CandidateNextActionPanel(props: {
  reminders: ReminderRecord[]
  remindersLoading: boolean
  remindersError: FriendlyErrorInfo | null
  reminderBusy: string | null
  reminderTitle: string
  reminderDueAt: string
  reminderOffset: number
  onReminderTitleChange: (title: string) => void
  onReminderDueAtChange: (date: string) => void
  onReminderOffsetChange: (offset: number) => void
  onReminderCreate: () => void
  onReminderComplete: (id: string) => void
  onReminderSnooze: (id: string, minutes: number) => void
  candidateId: string
  hideToggle?: boolean
  hideRemindersList?: boolean
  /** @deprecated Prefer docsIssuesPresent + docsPipelineBlocking */
  docsBlockersActive?: boolean
  /** Checklist has gaps (missing / problematic / in review). */
  docsIssuesPresent?: boolean
  /** When true, documents are a hard gate for the pipeline at this stage. */
  docsPipelineBlocking?: boolean
  docsRequestTitle?: string
  docsRequestDueLabel?: string
  docsBlockerKind?: 'request' | 'review' | null
  onDocsRequestCreate?: () => void
  /**
   * When set to a value > 0, forces the embedded reminders editor
   * (create/snooze/complete) to open.
   */
  detailsOpenTrigger?: number
  /** Canonical stage (e.g. `contacted`, `docs_wait`) for suggested next step when no reminder. */
  canonicalStageCode?: string | null
  /** Next stage in journey order — used to advance operational hints after gates are satisfied. */
  nextPipelineStageCode?: string | null
  vacancyPipelineBlocking?: boolean
  contactAttemptPipelineBlocking?: boolean
  /** Emphasize this panel as the single “do this next” rail step (reminder due, vacancy gate, etc.). */
  primaryStepHighlight?: boolean
  /**
   * Documents rail/panel is shown alongside: do not duplicate checklist copy, badges, or “create doc task” here;
   * keep missing types + upload only in that panel.
   */
  documentsChecklistSibling?: boolean
}) {
  const { t, locale } = useI18n()
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [nowTs, setNowTs] = useState<number>(0)

  const pipelineCompleted = isPipelineCompletedCanonicalStage(props.canonicalStageCode ?? undefined)

  const issuesPresent = props.docsIssuesPresent ?? props.docsBlockersActive ?? false
  const pipelineBlocking = props.docsPipelineBlocking ?? props.docsBlockersActive ?? false

  const stageHint = useMemo(
    () =>
      operationalHintForStageResolved(
        props.canonicalStageCode ?? undefined,
        props.nextPipelineStageCode ?? undefined,
        {
          vacancyPipelineBlocking: props.vacancyPipelineBlocking,
          contactAttemptPipelineBlocking: props.contactAttemptPipelineBlocking,
        },
      ),
    [
      props.canonicalStageCode,
      props.nextPipelineStageCode,
      props.vacancyPipelineBlocking,
      props.contactAttemptPipelineBlocking,
    ],
  )

  const stageHintTitle = useCallback(
    (kind: StageOperationalHintKind) => {
      switch (kind) {
        case 'call_candidate':
          return t('app.candidate_card.next_action.stage_hint.call', { defaultValue: 'Call / contact the candidate' })
        case 'assign_vacancy':
          return t('app.candidate_card.next_action.stage_hint.assign', {
            defaultValue: 'Qualify & assign vacancy / client',
          })
        case 'request_documents':
          return t('app.candidate_card.next_action.stage_hint.request_docs', { defaultValue: 'Collect required documents' })
        case 'verify_documents':
          return t('app.candidate_card.next_action.stage_hint.verify_docs', { defaultValue: 'Verify uploaded documents' })
        case 'handoff_prep':
          return t('app.candidate_card.next_action.stage_hint.handoff', {
            defaultValue: 'Complete checks before handoff',
          })
        case 'advance_pipeline':
          return t('app.candidate_card.next_action.stage_hint.advance', { defaultValue: 'Move the case forward' })
        default:
          return ''
      }
    },
    [t],
  )

  useEffect(() => {
    // Keep "overdue" state stable without calling impure Date.now() inside hook callbacks.
    setNowTs(Date.now())
    const id = window.setInterval(() => setNowTs(Date.now()), 30_000)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => {
    if ((props.detailsOpenTrigger ?? 0) > 0) setDetailsOpen(true)
  }, [props.detailsOpenTrigger])

  const next = useMemo(() => pickNextAction(props.reminders || [], nowTs), [props.reminders, nowTs])
  const dueLabel = useMemo(() => {
    if (!next?.due_at) return '—'
    try {
      return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : undefined, {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      }).format(new Date(next.due_at))
    } catch {
      return String(next.due_at)
    }
  }, [locale, next])

  const isOverdue = useMemo(() => {
    if (!next) return false
    if (next.status === 'overdue') return true
    const ts = parseTs(next.due_at)
    return ts > 0 && (nowTs ? ts < nowTs : false)
  }, [next, nowTs])

  const docsBlockingTitle = useMemo(() => {
    if (props.docsRequestTitle) return props.docsRequestTitle
    if (stageHint?.kind === 'request_documents') return stageHintTitle('request_documents')
    if (stageHint?.kind === 'verify_documents') return stageHintTitle('verify_documents')
    return t('app.candidate_card.next_action.docs_request_title', { defaultValue: 'Request documents' })
  }, [props.docsRequestTitle, stageHint, stageHintTitle, t])

  const docsSoftTitle = useMemo(() => {
    if (stageHint?.kind === 'call_candidate') return stageHintTitle('call_candidate')
    if (stageHint?.kind === 'assign_vacancy') return stageHintTitle('assign_vacancy')
    return t('app.candidate_card.next_action.contact_first_title', {
      defaultValue: 'Contact & qualify candidate',
    })
  }, [stageHint, stageHintTitle, t])

  const deferDocsDuplicate = Boolean(props.documentsChecklistSibling) && issuesPresent && !next

  const primary = Boolean(props.primaryStepHighlight)

  if (pipelineCompleted) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-slate-50/80 p-3">
        <div className="text-xs font-semibold text-slate-600">
          {t('app.candidate_card.next_action.pipeline_completed_title', { defaultValue: 'Process completed' })}
        </div>
        <p className="mt-1 text-sm text-slate-600">
          {t('app.candidate_card.next_action.pipeline_completed_body', {
            defaultValue:
              'This candidate is in a final stage (hired, rejected, declined, or probation completed) — no further pipeline steps apply.',
          })}
        </p>
      </section>
    )
  }

  return (
    <section
      className={clsx(
        'rounded-2xl border border-slate-200 bg-white p-3 transition-shadow duration-200',
        primary && 'ring-2 ring-amber-400/95 ring-offset-2 ring-offset-white shadow-sm shadow-amber-500/10',
      )}
      data-rail-primary-step={primary ? 'true' : undefined}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-xs font-semibold text-slate-800">
              {t('app.candidate_card.next_action.title', { defaultValue: 'Next action' })}
            </div>
            {primary ? (
              <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-950">
                {t('app.candidate_card.rail.primary_step_badge', { defaultValue: 'Next step' })}
              </span>
            ) : null}
          </div>
          {props.remindersError ? (
            <div className="mt-1 text-xs text-rose-600">
              <div>{props.remindersError.title}</div>
              {props.remindersError.detail ? (
                <div className="mt-0.5 text-[11px] text-rose-700/90">{props.remindersError.detail}</div>
              ) : null}
            </div>
          ) : props.remindersLoading ? (
            <div className="mt-1 text-xs text-slate-500">{t('common.loading')}</div>
          ) : next ? (
            <>
              <div className="mt-1 text-sm font-semibold text-slate-900 truncate">
                {next.title || t('app.candidate_card.reminders.untitled')}
              </div>
              <div className={clsx('mt-0.5 text-xs', isOverdue ? 'text-rose-700' : 'text-slate-600')}>
                {t('app.candidate_card.next_action.due', { defaultValue: 'Due' })}: {dueLabel}
                {isOverdue ? (
                  <span className="ml-2 inline-flex items-center rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-semibold text-rose-700">
                    {t('app.candidate_card.next_action.overdue', { defaultValue: 'Overdue' })}
                  </span>
                ) : null}
              </div>
            </>
          ) : deferDocsDuplicate ? (
            <>
              <div className="mt-1 text-sm text-slate-700">
                {t('app.candidate_card.next_action.docs_in_panel_below', {
                  defaultValue: 'What’s missing and where to upload are in the Documents section below.',
                })}
              </div>
              {stageHint &&
              stageHint.kind !== 'request_documents' &&
              stageHint.kind !== 'verify_documents' ? (
                <div className="mt-2 text-xs text-slate-600">
                  {t('app.candidate_card.next_action.suggested_focus', {
                    defaultValue: 'Suggested focus: {label}',
                    values: { label: stageHintTitle(stageHint.kind) },
                  })}
                </div>
              ) : (
                <div className="mt-2 text-xs text-slate-500">
                  {t('app.candidate_card.next_action.reminder_optional_nudge', {
                    defaultValue: 'Add a reminder if you want a tracked due date.',
                  })}
                </div>
              )}
            </>
          ) : issuesPresent ? (
            <>
              <div className="mt-1 text-sm font-semibold text-slate-900 truncate">
                {pipelineBlocking ? docsBlockingTitle : docsSoftTitle}
              </div>
              <div className="mt-2 space-y-2">
                <div className="text-xs text-slate-600">
                  {t('app.candidate_card.next_action.due', { defaultValue: 'Due' })}:{' '}
                  {props.docsRequestDueLabel || t('common.today', { defaultValue: 'Today' })}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {pipelineBlocking ? (
                    <span className="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-semibold leading-tight text-amber-700">
                      {t('app.candidate_card.next_action.docs_blocking', { defaultValue: 'Blocking' })}
                    </span>
                  ) : (
                    <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold leading-tight text-slate-700">
                      {t('app.candidate_card.next_action.docs_not_blocking_stage', {
                        defaultValue: 'Not blocking at this stage',
                      })}
                    </span>
                  )}
                  {props.docsBlockerKind === 'review' ? (
                    <span className="inline-flex items-center rounded-full bg-rose-50 px-2.5 py-1 text-[11px] font-semibold leading-tight text-rose-700">
                      {t('app.candidate_card.next_action.docs_review_required', { defaultValue: 'Review required' })}
                    </span>
                  ) : (
                    <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-semibold leading-tight text-blue-700">
                      {t('app.candidate_card.next_action.docs_missing_badge', { defaultValue: 'Documents missing' })}
                    </span>
                  )}
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="mt-1 text-sm font-semibold text-slate-900">
                {stageHint
                  ? stageHintTitle(stageHint.kind)
                  : t('app.candidate_card.next_action.empty_title', { defaultValue: 'No active reminders' })}
              </div>
              {stageHint ? (
                <div className="mt-0.5 text-xs text-slate-600">
                  {t('app.candidate_card.next_action.stage_hint.footer', {
                    defaultValue: 'Suggested focus for this stage (add a reminder to track it).',
                  })}
                </div>
              ) : (
                <div className="mt-0.5 text-xs text-slate-500">
                  {t('app.candidate_card.next_action.empty', { defaultValue: 'Create a reminder to track the next step.' })}
                </div>
              )}
            </>
          )}
        </div>

        <div className="shrink-0 flex flex-wrap items-center gap-2">
          {next ? (
            <>
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={props.reminderBusy === next.id}
                onClick={() => props.onReminderComplete(next.id)}
              >
                {props.reminderBusy === next.id ? t('common.loading') : t('app.candidate_card.next_action.complete', { defaultValue: 'Complete' })}
              </button>
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={props.reminderBusy === next.id}
                onClick={() => props.onReminderSnooze(next.id, 60)}
              >
                {t('app.candidate_card.next_action.snooze', { defaultValue: 'Snooze 1h' })}
              </button>
            </>
          ) : deferDocsDuplicate ? (
            <button type="button" className="btn-secondary btn-sm" onClick={() => setDetailsOpen(true)}>
              {t('app.candidate_card.next_action.create', { defaultValue: 'Create' })}
            </button>
          ) : issuesPresent ? (
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => {
                props.onDocsRequestCreate?.()
                setDetailsOpen(true)
              }}
            >
              {pipelineBlocking
                ? t('app.candidate_card.next_action.create_task', { defaultValue: 'Create task' })
                : t('app.candidate_card.next_action.create_contact_task', {
                    defaultValue: 'Create follow-up',
                  })}
            </button>
          ) : (
            <button type="button" className="btn-secondary btn-sm" onClick={() => setDetailsOpen(true)}>
              {t('app.candidate_card.next_action.create', { defaultValue: 'Create' })}
            </button>
          )}
        </div>
      </div>

      {!props.hideToggle ? (
        <div className="mt-2">
          <button
            type="button"
            className="text-[11px] text-slate-500 hover:text-slate-700"
            onClick={() => setDetailsOpen((v) => !v)}
          >
            {detailsOpen ? t('common.actions.collapse') : t('common.actions.expand')}
          </button>
        </div>
      ) : null}

      {!props.hideRemindersList && detailsOpen ? (
        <div className="mt-3">
          <CandidateRemindersSection
            candidateId={props.candidateId}
            reminders={props.reminders}
            remindersLoading={props.remindersLoading}
            remindersError={props.remindersError}
            reminderTitle={props.reminderTitle}
            reminderDueAt={props.reminderDueAt}
            reminderOffset={props.reminderOffset}
            reminderBusy={props.reminderBusy}
            onReminderTitleChange={props.onReminderTitleChange}
            onReminderDueAtChange={props.onReminderDueAtChange}
            onReminderOffsetChange={props.onReminderOffsetChange}
            onReminderCreate={props.onReminderCreate}
            onReminderComplete={props.onReminderComplete}
            onReminderSnooze={props.onReminderSnooze}
            embedded
          />
        </div>
      ) : null}
    </section>
  )
}

