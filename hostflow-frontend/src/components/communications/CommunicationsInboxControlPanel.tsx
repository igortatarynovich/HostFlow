import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconChevronDown, IconExternalLink, IconListCheck, IconLink, IconShield } from '@tabler/icons-react'
import { patchCommunicationThread, rematchUnlinkedCommunicationThreads, type CommunicationThread } from '../../api/communications'
import { createReminder } from '../../api/client'
import { listTenantManagers } from '../../api/users'
import type { ManagerOption } from '../../api/types'
import type { useCommunicationsThread } from '../../hooks/useCommunicationsThread'
import { useI18n } from '../../i18n'
import { isCommunicationThreadUnlinked, uosLinkedServiceOrderId } from '../../utils/communicationThreadUnlinked'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyFormHintError, getFriendlyErrorInfo } from '../../utils/friendlyError'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import CommunicationsInboxThreadContextCard from './CommunicationsInboxThreadContextCard'
import CommunicationsInboxWorkflowCard from './CommunicationsInboxWorkflowCard'
import CommunicationsThreadEntityLinkForms from './CommunicationsThreadEntityLinkForms'
import { communicationsThreadPath, CRM_APP_PATHS } from '../../app/crmAppPaths'
import { formatThreadDateTime } from './CommunicationsThreadWorkArea'
import { NextActionBadge } from '../candidate/NextActionBadge'
import { useThreadNextAction } from './useThreadNextAction'

type ThreadModel = ReturnType<typeof useCommunicationsThread>

type Props = {
  thread: CommunicationThread
  model: ThreadModel
  /** Unified Inbox list shows only active threads — after archive/delete, refresh the hub list and leave `/app/inbox/threads/:id`. */
  onAfterArchiveOrDelete?: () => void
  /** Email / compact workspace: drop long instructional copy. */
  compact?: boolean
  /** Messages workspace: entity search/link forms live in the chat column; rail shows summary + operations only. */
  hideEntityLinkForms?: boolean
  /** Parent list refresh (e.g. Messages page `loadThreads`) after thread fields change. */
  onAfterThreadPatch?: () => void | Promise<void>
}

const REMIND_BEFORE_MS = 15 * 60 * 1000

function pad2(n: number) {
  return String(n).padStart(2, '0')
}

function defaultDueLocal(): string {
  const dt = new Date(Date.now() + 60 * 60 * 1000)
  return `${dt.getFullYear()}-${pad2(dt.getMonth() + 1)}-${pad2(dt.getDate())}T${pad2(dt.getHours())}:${pad2(dt.getMinutes())}`
}

function parseLocalDue(value: string): Date | null {
  const d = new Date(value)
  return Number.isFinite(d.getTime()) ? d : null
}

function defaultTitleFromThread(thread: CommunicationThread): string {
  const sub = String(thread.subject || '').trim()
  if (sub) return sub
  const prev = String(thread.last_message_preview || '').trim().slice(0, 120)
  if (prev) return prev
  return ''
}

export default function CommunicationsInboxControlPanel({
  thread,
  model,
  onAfterArchiveOrDelete,
  compact,
  hideEntityLinkForms,
  onAfterThreadPatch,
}: Props) {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const { busyAction, handleMarkRead, handleAutoAssign, load } = model
  const unlinked = isCommunicationThreadUnlinked(thread)
  const cid = String(thread.linked_candidate_id || '').trim()
  const compId = String(thread.linked_company_id || '').trim()
  const linkedOrderId = uosLinkedServiceOrderId(thread.thread_meta)

  const threadStatus = String(thread.status || '').toLowerCase()
  const isThreadDeleted = threadStatus === 'deleted'
  const isThreadArchived = Boolean(thread.is_archived) && !isThreadDeleted
  const isThreadInboxActive = !thread.is_archived && !isThreadDeleted

  const fallbackTitle = t('app.communications_inbox_center.task_default_title')

  const [taskTitle, setTaskTitle] = useState(() => defaultTitleFromThread(thread))
  const [taskDescription, setTaskDescription] = useState('')
  const [taskDueLocal, setTaskDueLocal] = useState(defaultDueLocal)
  const [taskBusy, setTaskBusy] = useState(false)
  const [taskError, setTaskError] = useState<FriendlyErrorInfo | null>(null)
  const [taskCreated, setTaskCreated] = useState(false)
  const [linkPickerOpen, setLinkPickerOpen] = useState(false)
  const [taskFormOpen, setTaskFormOpen] = useState(false)
  const [workflowOpen, setWorkflowOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const [rematchBusy, setRematchBusy] = useState(false)
  const [rematchHint, setRematchHint] = useState<string | null>(null)
  const [rematchError, setRematchError] = useState<FriendlyErrorInfo | null>(null)

  const [assigneeSaveError, setAssigneeSaveError] = useState<FriendlyErrorInfo | null>(null)
  const [folderBusy, setFolderBusy] = useState(false)
  const [folderError, setFolderError] = useState<FriendlyErrorInfo | null>(null)

  const [managerOptions, setManagerOptions] = useState<ManagerOption[]>([])
  const [assigneeDraft, setAssigneeDraft] = useState(() => String(thread.assignee_id || ''))
  const [assigneeBusy, setAssigneeBusy] = useState(false)
  const [assigneeOk, setAssigneeOk] = useState(false)

  useEffect(() => {
    let canceled = false
    void listTenantManagers()
      .then((rows) => {
        if (!canceled) setManagerOptions(Array.isArray(rows) ? rows : [])
      })
      .catch(() => {
        if (!canceled) setManagerOptions([])
      })
    return () => {
      canceled = true
    }
  }, [])

  useEffect(() => {
    setAssigneeDraft(String(thread.assignee_id || ''))
    setAssigneeOk(false)
  }, [thread.id, thread.assignee_id])

  useEffect(() => {
    const fb = t('app.communications_inbox_center.task_default_title')
    setTaskTitle(defaultTitleFromThread(thread) || fb)
    setTaskDescription('')
    setTaskDueLocal(defaultDueLocal())
    setTaskError(null)
    setTaskCreated(false)
    setAssigneeSaveError(null)
    setFolderError(null)
    setLinkPickerOpen(false)
    setTaskFormOpen(false)
    setWorkflowOpen(false)
    setMoreOpen(false)
    setRematchHint(null)
    setRematchError(null)
    // Only when switching threads — avoid wiping the form on every thread object refresh.
  }, [thread.id, t])

  const threadNextActionFingerprint = `${thread.status ?? ''}|${thread.is_archived ? 1 : 0}|${thread.unread_count ?? 0}|${thread.sla_due_at ?? ''}|${thread.last_inbound_at ?? ''}|${thread.last_outbound_at ?? ''}`
  const {
    data: threadNextAction,
    loading: threadNextActionLoading,
    error: threadNextActionError,
  } = useThreadNextAction(thread.id, threadNextActionFingerprint)

  const saveManualAssignee = async () => {
    setAssigneeBusy(true)
    setAssigneeOk(false)
    setAssigneeSaveError(null)
    try {
      await patchCommunicationThread(thread.id, { assignee_id: assigneeDraft || null })
      await load()
      setAssigneeSaveError(null)
      setAssigneeOk(true)
      await onAfterThreadPatch?.()
    } catch (err: unknown) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.communications_inbox_center.assignee_save_failed'))) {
        setAssigneeSaveError(
          getFriendlyErrorInfo(err, t('app.communications_inbox_center.assignee_save_failed'), t),
        )
      }
    } finally {
      setAssigneeBusy(false)
    }
  }

  const applyThreadFolderPatch = async (payload: Record<string, unknown>, exitCenter: boolean) => {
    setFolderBusy(true)
    setFolderError(null)
    try {
      await patchCommunicationThread(thread.id, payload)
      await load()
      await onAfterThreadPatch?.()
      if (exitCenter) onAfterArchiveOrDelete?.()
    } catch (err: unknown) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.communications_inbox_center.folder_error'))) {
        setFolderError(getFriendlyErrorInfo(err, t('app.communications_inbox_center.folder_error'), t))
      }
    } finally {
      setFolderBusy(false)
    }
  }

  const afterEntityPatch = async () => {
    await load()
    await onAfterThreadPatch?.()
  }

  const runG15Rematch = async () => {
    setRematchBusy(true)
    setRematchError(null)
    setRematchHint(null)
    try {
      const result = await rematchUnlinkedCommunicationThreads({
        threadIds: [thread.id],
        limit: 1,
        dryRun: false,
      })
      const item = Array.isArray(result.items) ? result.items[0] : null
      if (item?.skipped) {
        setRematchHint(
          t('app.communications_inbox_center.rematch_skipped', {
            defaultValue: 'Пропущено: {{reason}}',
            reason: item.skip_reason || '—',
          }),
        )
      } else if (item?.auto_linked || result.linked > 0) {
        setRematchHint(
          t('app.communications_inbox_center.rematch_linked', {
            defaultValue: 'Привязано по strong match.',
          }),
        )
      } else if (result.ambiguous > 0 || item?.confidence === 'ambiguous') {
        setRematchHint(
          t('app.communications_inbox_center.rematch_ambiguous', {
            defaultValue: 'Несколько кандидатов — без авто-привязки. Выберите вручную.',
          }),
        )
      } else {
        setRematchHint(
          t('app.communications_inbox_center.rematch_none', {
            defaultValue: 'Подходящее обращение не найдено.',
          }),
        )
      }
      await load()
      await onAfterThreadPatch?.()
    } catch (err: unknown) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications_inbox_center.rematch_failed', { defaultValue: 'Не удалось перепривязать' }),
        )
      ) {
        setRematchError(
          getFriendlyErrorInfo(
            err,
            t('app.communications_inbox_center.rematch_failed', { defaultValue: 'Не удалось перепривязать' }),
            t,
          ),
        )
      }
    } finally {
      setRematchBusy(false)
    }
  }

  const submitFollowUpTask = async (e: FormEvent) => {
    e.preventDefault()
    const title = taskTitle.trim() || fallbackTitle
    if (!title) return
    const due = parseLocalDue(taskDueLocal)
    if (!due) {
      setTaskError(friendlyFormHintError(t('app.communications_inbox_center.task_error_due'), t))
      return
    }
    const remindAt = new Date(due.getTime() - REMIND_BEFORE_MS)
    setTaskBusy(true)
    setTaskError(null)
    setTaskCreated(false)
    try {
      let entity_type: string
      let entity_id: string
      if (cid) {
        entity_type = 'candidate'
        entity_id = cid
      } else if (compId) {
        entity_type = 'company'
        entity_id = compId
      } else {
        entity_type = 'custom'
        entity_id = 'manual'
      }
      const desc = taskDescription.trim()
      await createReminder({
        title,
        description: desc || undefined,
        type: 'custom',
        entity_type,
        entity_id,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        priority: 'normal',
        channel: 'internal',
        source: 'communications.inbox_control_panel',
        payload: {
          communication_thread_id: thread.id,
          communication_channel: thread.channel,
        },
      })
      setTaskCreated(true)
    } catch (err: unknown) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.communications_inbox_center.task_error_create'))) {
        setTaskError(getFriendlyErrorInfo(err, t('app.communications_inbox_center.task_error_create'), t))
      }
    } finally {
      setTaskBusy(false)
    }
  }

  return (
    <div className="space-y-3 p-3 xl:p-0">
      {!compact && (
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.communications_inbox_center.control_title')}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.communications_inbox_center.control_subtitle')}
          </p>
        </div>
      )}

      <CommunicationsInboxThreadContextCard thread={thread} managerOptions={managerOptions} />

      <div className="rounded-lg border border-slate-100 bg-slate-50/70 px-3 py-2">
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-600">
          <NextActionBadge
            dto={threadNextAction}
            loading={threadNextActionLoading}
            error={threadNextActionError}
          />
          <span>
            {t('app.communications_inbox_center.sla_due')}: {formatThreadDateTime(thread.sla_due_at)}
          </span>
          {(thread.unread_count ?? 0) > 0 ? (
            <span className="rounded bg-amber-100 px-1.5 py-0.5 font-medium text-amber-900">
              {thread.unread_count} {t('app.communications.labels.unread_lower')}
            </span>
          ) : null}
        </div>
      </div>

      {!hideEntityLinkForms && (
        <div className="space-y-2">
          {unlinked && (
            <div className="space-y-2">
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
                {t('app.communications_inbox_center.unlinked_hint_action', {
                  defaultValue: 'Not linked — use Link to attach an inquiry, client, or order.',
                })}
              </div>
              {String(thread.channel || '') === 'email' ? (
                <button
                  type="button"
                  className="btn-secondary btn-sm w-full"
                  disabled={rematchBusy}
                  onClick={() => void runG15Rematch()}
                  data-testid="thread-g15-rematch"
                >
                  {rematchBusy
                    ? t('app.communications_inbox_center.rematch_busy', {
                        defaultValue: 'Проверяем…',
                      })
                    : t('app.communications_inbox_center.rematch_action', {
                        defaultValue: 'Повторно найти обращение (G15)',
                      })}
                </button>
              ) : null}
              {rematchHint ? <p className="text-[11px] text-slate-600">{rematchHint}</p> : null}
              {rematchError ? (
                <p className="text-[11px] text-rose-700">{friendlyFormHintError(rematchError)}</p>
              ) : null}
            </div>
          )}
          <button
            type="button"
            className="btn-secondary btn-sm inline-flex w-full items-center justify-center gap-1.5"
            onClick={() => setLinkPickerOpen((v) => !v)}
          >
            <IconLink size={16} stroke={1.75} />
            {linkPickerOpen
              ? t('app.communications_inbox_center.link_entities_hide', { defaultValue: 'Hide link picker' })
              : t('app.communications_inbox_center.link_entities_action', { defaultValue: 'Link entities' })}
            <IconChevronDown size={14} className={linkPickerOpen ? 'rotate-180' : ''} />
          </button>
          {linkPickerOpen && (
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <CommunicationsThreadEntityLinkForms thread={thread} compact dense onAfterPatch={afterEntityPatch} />
            </div>
          )}
        </div>
      )}

      <div className="space-y-2">
        <button
          type="button"
          className="btn-secondary btn-sm inline-flex w-full items-center justify-center gap-1.5"
          onClick={() => setTaskFormOpen((v) => !v)}
        >
          <IconListCheck size={16} stroke={1.75} />
          {taskFormOpen
            ? t('app.communications_inbox_center.task_form_hide', { defaultValue: 'Hide task form' })
            : t('app.communications_inbox_center.task_create_action', { defaultValue: 'Create task' })}
          <IconChevronDown size={14} className={taskFormOpen ? 'rotate-180' : ''} />
        </button>
        {taskFormOpen && (
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <form className="space-y-2" onSubmit={(ev) => void submitFollowUpTask(ev)}>
              <label className="block text-xs font-medium text-slate-600">
                {t('app.communications_inbox_center.task_title_label')}
                <input
                  type="text"
                  className="input mt-1 w-full text-sm"
                  value={taskTitle}
                  onChange={(ev) => setTaskTitle(ev.target.value)}
                  placeholder={fallbackTitle}
                  disabled={taskBusy}
                  maxLength={500}
                />
              </label>
              <label className="block text-xs font-medium text-slate-600">
                {t('app.communications_inbox_center.task_due_label')}
                <input
                  type="datetime-local"
                  className="input mt-1 w-full text-sm"
                  value={taskDueLocal}
                  onChange={(ev) => setTaskDueLocal(ev.target.value)}
                  disabled={taskBusy}
                />
              </label>
              <label className="block text-xs font-medium text-slate-600">
                {t('app.communications_inbox_center.task_notes_label')}
                <textarea
                  className="input mt-1 min-h-[3rem] w-full resize-y text-sm"
                  value={taskDescription}
                  onChange={(ev) => setTaskDescription(ev.target.value)}
                  disabled={taskBusy}
                  maxLength={4000}
                />
              </label>
              {taskError ? (
                <p className="text-xs text-rose-600">
                  {taskError.title}
                  {taskError.detail ? ` — ${taskError.detail}` : ''}
                </p>
              ) : null}
              {taskCreated && (
                <p className="text-xs text-emerald-700">
                  {t('app.communications_inbox_center.task_created')}{' '}
                  <Link className="font-medium underline" to={CRM_APP_PATHS.tasks}>
                    {t('app.communications_inbox_center.task_open_tasks')}
                  </Link>
                </p>
              )}
              <button type="submit" className="btn-primary btn-sm w-full disabled:opacity-50" disabled={taskBusy}>
                {taskBusy ? t('common.loading') : t('app.communications_inbox_center.task_submit')}
              </button>
            </form>
          </div>
        )}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-3">
        <div className="text-xs font-semibold text-slate-800">
          {t('app.communications.queue.assignee')}
        </div>
        {assigneeSaveError ? (
          <p className="mt-1 text-xs text-rose-600">
            {assigneeSaveError.title}
            {assigneeSaveError.detail ? ` — ${assigneeSaveError.detail}` : ''}
          </p>
        ) : null}
        <select
          className="input mt-2 w-full text-sm"
          value={assigneeDraft}
          onChange={(e) => setAssigneeDraft(e.target.value)}
          disabled={assigneeBusy || folderBusy}
        >
          <option value="">{t('app.communications_messages.manager.unassigned')}</option>
          {managerOptions.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
        </select>
        <div className="mt-2 flex gap-2">
          <button
            type="button"
            className="btn-primary btn-sm flex-1 disabled:opacity-50"
            disabled={assigneeBusy || folderBusy}
            onClick={() => void saveManualAssignee()}
          >
            {assigneeBusy ? t('common.loading') : t('common.actions.save')}
          </button>
          <button
            type="button"
            className="btn-secondary btn-sm disabled:opacity-50"
            disabled={busyAction === 'assign' || folderBusy}
            onClick={() => void handleAutoAssign()}
            title={t('app.communications.queue.auto_assign')}
          >
            {busyAction === 'assign' ? '…' : 'Auto'}
          </button>
        </div>
        {assigneeOk && (
          <p className="mt-1 text-xs text-emerald-700">{t('app.communications_inbox_center.assignee_saved')}</p>
        )}
      </div>

      <div className="space-y-2">
        <button
          type="button"
          className="inline-flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-50"
          onClick={() => setWorkflowOpen((v) => !v)}
        >
          <span>{t('app.communications_inbox_center.workflow_section', { defaultValue: 'Workflow & SLA' })}</span>
          <IconChevronDown size={14} className={workflowOpen ? 'rotate-180' : ''} />
        </button>
        {workflowOpen && <CommunicationsInboxWorkflowCard thread={thread} onRefresh={load} />}
      </div>

      <div className="space-y-2">
        <button
          type="button"
          className="inline-flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-50"
          onClick={() => setMoreOpen((v) => !v)}
        >
          <span>{t('app.communications_inbox_center.more_actions', { defaultValue: 'More actions' })}</span>
          <IconChevronDown size={14} className={moreOpen ? 'rotate-180' : ''} />
        </button>
        {moreOpen && (
          <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-3">
            <button
              type="button"
              className="btn-secondary btn-sm w-full disabled:opacity-50"
              disabled={busyAction === 'read' || (thread.unread_count ?? 0) <= 0 || folderBusy}
              onClick={() => void handleMarkRead()}
            >
              {busyAction === 'read' ? t('common.loading') : t('app.communications.actions.mark_thread_read')}
            </button>
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                {t('app.communications_inbox_center.folder_section')}
              </div>
              {folderError ? (
                <p className="mt-2 text-xs text-rose-600">
                  {folderError.title}
                  {folderError.detail ? ` — ${folderError.detail}` : ''}
                </p>
              ) : null}
              <div className="mt-2 flex flex-col gap-2">
                {isThreadInboxActive && (
                  <>
                    <button
                      type="button"
                      className="btn-secondary btn-sm w-full disabled:opacity-50"
                      disabled={folderBusy}
                      onClick={() =>
                        void applyThreadFolderPatch(
                          { is_archived: true, status: 'archived' },
                          Boolean(onAfterArchiveOrDelete),
                        )
                      }
                    >
                      {folderBusy ? t('common.loading') : t('app.communications.email.commands.archive')}
                    </button>
                    <button
                      type="button"
                      className="btn-danger btn-sm w-full disabled:opacity-50"
                      disabled={folderBusy}
                      onClick={() =>
                        void applyThreadFolderPatch(
                          { is_archived: true, status: 'deleted' },
                          Boolean(onAfterArchiveOrDelete),
                        )
                      }
                    >
                      {folderBusy ? t('common.loading') : t('app.communications.email.commands.delete')}
                    </button>
                  </>
                )}
                {(isThreadArchived || isThreadDeleted) && (
                  <button
                    type="button"
                    className="btn-secondary btn-sm w-full disabled:opacity-50"
                    disabled={folderBusy}
                    onClick={() => void applyThreadFolderPatch({ is_archived: false, status: 'open' }, false)}
                  >
                    {folderBusy
                      ? t('common.loading')
                      : isThreadDeleted
                        ? t('app.communications.email.commands.restore')
                        : t('app.communications.email.commands.unarchive')}
                  </button>
                )}
              </div>
            </div>
            <ul className="space-y-2 border-t border-slate-100 pt-2 text-sm">
              <li>
                <Link
                  className="inline-flex items-center gap-1.5 text-brand-700 hover:text-brand-900"
                  to={CRM_APP_PATHS.tasks}
                >
                  <IconListCheck size={16} stroke={1.75} />
                  {t('app.nav.items.tasks')}
                </Link>
              </li>
              <li>
                <Link
                  className="inline-flex items-center gap-1.5 text-rose-700 hover:text-rose-900"
                  to={CRM_APP_PATHS.slaIncidents}
                >
                  <IconShield size={16} stroke={1.75} />
                  {t('app.communications_inbox_hub.cta_sla')}
                </Link>
              </li>
              <li>
                <Link
                  className="inline-flex items-center gap-1.5 text-slate-600 hover:text-slate-900"
                  to={communicationsThreadPath(thread.id)}
                >
                  <IconExternalLink size={16} stroke={1.75} />
                  {t('app.communications_inbox_center.classic_view')}
                </Link>
              </li>
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
