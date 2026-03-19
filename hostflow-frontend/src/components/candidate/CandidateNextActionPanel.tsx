import { useEffect, useMemo, useState } from 'react'
import clsx from 'clsx'
import type { ReminderRecord } from '../../api/types'
import { useI18n } from '../../i18n'
import CandidateRemindersSection from './CandidateRemindersSection'

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
  remindersError: string | null
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
  docsBlockersActive?: boolean
  docsRequestTitle?: string
  docsRequestDueLabel?: string
  onDocsRequestCreate?: () => void
  /**
   * When set to a value > 0, forces the embedded reminders editor
   * (create/snooze/complete) to open.
   */
  detailsOpenTrigger?: number
}) {
  const { t, locale } = useI18n()
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [nowTs, setNowTs] = useState<number>(0)

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

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold text-slate-800">
            {t('app.candidate_card.next_action.title', { defaultValue: 'Next action' })}
          </div>
          {props.remindersError ? (
            <div className="mt-1 text-xs text-rose-600">{props.remindersError}</div>
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
          ) : props.docsBlockersActive ? (
            <>
              <div className="mt-1 text-sm font-semibold text-slate-900 truncate">
                {props.docsRequestTitle || t('app.candidate_card.next_action.docs_request_title', { defaultValue: 'Request documents' })}
              </div>
              <div className="mt-0.5 text-xs text-slate-600">
                {t('app.candidate_card.next_action.due', { defaultValue: 'Due' })}: {props.docsRequestDueLabel || t('common.today', { defaultValue: 'Today' })}
                <span className="ml-2 inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                  {t('app.candidate_card.next_action.docs_blocking', { defaultValue: 'Blocking' })}
                </span>
              </div>
            </>
          ) : (
            <div className="mt-1 text-xs text-slate-500">
              {t('app.candidate_card.next_action.empty', { defaultValue: 'No active reminders.' })}
            </div>
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
          ) : props.docsBlockersActive ? (
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => {
                props.onDocsRequestCreate?.()
                setDetailsOpen(true)
              }}
            >
              {t('app.candidate_card.next_action.create_task', { defaultValue: 'Create task' })}
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

