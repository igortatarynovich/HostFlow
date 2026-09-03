import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  completeActivity,
  createActivity,
  listReminders,
  snoozeActivity,
} from '../../api/client'
import type { ReminderRecord } from '../../api/types'
import { useI18n } from '../../i18n'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { canonicalStageKey } from '../../utils/stageLabels'
import { isPipelineCompletedCanonicalStage } from '../../utils/candidatePipelineCompleted'
import CandidateNextActionPanel from '../candidate/CandidateNextActionPanel'
import CandidateDocsRailPanel from '../candidate/CandidateDocsRailPanel'
import type { WorkforceHrBundle } from '../../api/workforce'

type Props = {
  candidateId: string | null | undefined
  docsOwnerContext: Record<string, unknown>
  linkedCandidateStage: string | null
  onboardingTasks: WorkforceHrBundle['onboarding_tasks']
  refreshSignal: number
  canViewCandidate: boolean
  onRefreshParent: () => void
}

export function HrEmployeeRail({
  candidateId,
  docsOwnerContext,
  linkedCandidateStage,
  onboardingTasks,
  refreshSignal,
  canViewCandidate,
  onRefreshParent,
}: Props) {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const [reminders, setReminders] = useState<ReminderRecord[]>([])
  const [remindersLoading, setRemindersLoading] = useState(false)
  const [remindersError, setRemindersError] = useState<FriendlyErrorInfo | null>(null)
  const [reminderBusy, setReminderBusy] = useState<string | null>(null)
  const [reminderTitle, setReminderTitle] = useState('')
  const [reminderDueAt, setReminderDueAt] = useState('')
  const [reminderOffset, setReminderOffset] = useState(30)
  const [docsRefresh, setDocsRefresh] = useState(0)

  const loadReminders = useCallback(async () => {
    if (!candidateId || !canViewCandidate) {
      setReminders([])
      return
    }
    setRemindersLoading(true)
    setRemindersError(null)
    try {
      const res = await listReminders({
        entityType: 'candidate',
        entityId: candidateId,
        status: ['pending', 'new', 'overdue'],
      })
      const items = Array.isArray(res?.items) ? res.items : []
      setReminders(items.slice(0, 12))
    } catch (err: unknown) {
      setRemindersError(
        getFriendlyErrorInfo(err, t('app.reminders.errors.load', { defaultValue: 'Could not load reminders' }), t),
      )
      setReminders([])
    } finally {
      setRemindersLoading(false)
    }
  }, [candidateId, canViewCandidate, t])

  useEffect(() => {
    void loadReminders()
  }, [loadReminders, refreshSignal])

  useEffect(() => {
    if (!candidateId || !canViewCandidate) return
    if (reminderDueAt.trim()) return
    setReminderDueAt(new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16))
  }, [candidateId, canViewCandidate, reminderDueAt])

  const handleCreateReminder = useCallback(async () => {
    if (!candidateId || !reminderTitle || !reminderDueAt) return
    try {
      const due = new Date(reminderDueAt)
      const remindAt = new Date(due.getTime() - reminderOffset * 60 * 1000)
      await createActivity({
        title: reminderTitle,
        description: '',
        type: 'custom',
        entity_type: 'candidate',
        entity_id: candidateId,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        priority: 'normal',
        source: 'manual',
      })
      setReminderTitle('')
      setReminderDueAt(new Date(due.getTime() + 60 * 60 * 1000).toISOString().slice(0, 16))
      await loadReminders()
      onRefreshParent()
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.create'))) return
      const info = getFriendlyErrorInfo(err, t('app.reminders.errors.create'), t)
      setRemindersError(info)
    }
  }, [candidateId, reminderTitle, reminderDueAt, reminderOffset, loadReminders, onRefreshParent, planLimitModal, t])

  const handleReminderComplete = useCallback(
    async (id: string) => {
      try {
        setReminderBusy(id)
        await completeActivity(id)
        await loadReminders()
        onRefreshParent()
      } catch (err: unknown) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.complete'))) return
        const info = getFriendlyErrorInfo(err, t('app.reminders.errors.complete'), t)
        setRemindersError(info)
      } finally {
        setReminderBusy((prev) => (prev === id ? null : prev))
      }
    },
    [loadReminders, onRefreshParent, planLimitModal, t],
  )

  const handleReminderSnooze = useCallback(
    async (id: string, minutes: number) => {
      try {
        setReminderBusy(id)
        await snoozeActivity(id, { minutes })
        await loadReminders()
        onRefreshParent()
      } catch (err: unknown) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.snooze'))) return
        const info = getFriendlyErrorInfo(err, t('app.reminders.errors.snooze'), t)
        setRemindersError(info)
      } finally {
        setReminderBusy((prev) => (prev === id ? null : prev))
      }
    },
    [loadReminders, onRefreshParent, planLimitModal, t],
  )

  const handleDocsRequestCreate = useCallback(() => {
    const dt = new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16)
    setReminderTitle(t('app.candidate_card.next_action.docs_request_title', { defaultValue: 'Request documents' }))
    setReminderDueAt(dt)
  }, [t])

  const canonicalStageForOps = useMemo(() => {
    const stored =
      canonicalStageKey(linkedCandidateStage ?? null, null) ||
      String(linkedCandidateStage || '').trim().toLowerCase() ||
      ''
    if (stored && isPipelineCompletedCanonicalStage(stored)) return stored
    const raw = String(linkedCandidateStage || '').trim()
    if (!raw) return null
    return canonicalStageKey(raw, null) || raw.toLowerCase()
  }, [linkedCandidateStage])

  const openOnboarding = onboardingTasks.filter((x) => String(x.status).toLowerCase() !== 'done')

  if (!canViewCandidate || !candidateId) {
    return (
      <div className="space-y-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-3 text-xs text-slate-600">
          {t('app.hr.employee_detail.rail.no_candidate', {
            defaultValue: 'Link a candidate to enable document checklist and reminders in this rail.',
          })}
        </div>
      </div>
    )
  }

  return (
    <div
      className="flex w-full min-w-0 flex-col gap-4 lg:sticky lg:top-4 lg:max-h-[calc(100dvh-3.5rem)] lg:overflow-y-auto"
      data-hr-employee-control-rail
    >
      <CandidateNextActionPanel
        candidateId={candidateId}
        reminders={reminders}
        remindersLoading={remindersLoading}
        remindersError={remindersError}
        reminderBusy={reminderBusy}
        reminderTitle={reminderTitle}
        reminderDueAt={reminderDueAt}
        reminderOffset={reminderOffset}
        onReminderTitleChange={setReminderTitle}
        onReminderDueAtChange={setReminderDueAt}
        onReminderOffsetChange={setReminderOffset}
        onReminderCreate={handleCreateReminder}
        onReminderComplete={handleReminderComplete}
        onReminderSnooze={handleReminderSnooze}
        hideToggle
        hideRemindersList
        reminderEditorInModal
        docsRequestDueLabel={t('common.today', { defaultValue: 'Today' })}
        onDocsRequestCreate={handleDocsRequestCreate}
        canonicalStageCode={canonicalStageForOps}
        documentsChecklistSibling
        vacancyPipelineBlocking={false}
        contactAttemptPipelineBlocking={false}
      />

      <CandidateDocsRailPanel
        candidateId={candidateId}
        ownerContext={docsOwnerContext}
        uploadBusy={false}
        refreshTrigger={refreshSignal + docsRefresh}
        onOpenDocs={() => setDocsRefresh((x) => x + 1)}
        onSelectType={() => setDocsRefresh((x) => x + 1)}
        stageSummaryLabel={linkedCandidateStage ? String(linkedCandidateStage) : null}
        pollingEnabled={false}
      />

      <div className="rounded-2xl border border-slate-200 bg-white p-3">
        <div className="text-xs font-semibold text-slate-800">
          {t('app.hr.employee_detail.rail.onboarding_title', { defaultValue: 'Onboarding tasks' })}
        </div>
        {openOnboarding.length === 0 ? (
          <p className="mt-2 text-xs text-slate-500">
            {t('app.hr.employee_detail.rail.onboarding_clear', { defaultValue: 'No open tasks.' })}
          </p>
        ) : (
          <ul className="mt-2 space-y-2">
            {openOnboarding.map((task) => (
              <li
                key={task.id}
                className="flex items-start justify-between gap-2 rounded-lg border border-slate-100 bg-slate-50/80 px-2 py-1.5 text-xs text-slate-800"
              >
                <span className="min-w-0 flex-1 font-medium">{task.title}</span>
                <span className="shrink-0 text-[10px] uppercase text-slate-500">{task.status}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-2 text-[10px] text-slate-500">
          {t('app.hr.employee_detail.rail.onboarding_footer', {
            defaultValue: 'Complete tasks in the main form below.',
          })}
        </p>
      </div>
    </div>
  )
}
