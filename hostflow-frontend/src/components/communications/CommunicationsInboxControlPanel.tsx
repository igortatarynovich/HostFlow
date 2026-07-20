import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconExternalLink, IconListCheck, IconShield } from '@tabler/icons-react'
import ThreadWorkspaceSlaChip from './ThreadWorkspaceSlaChip'
import { type CommunicationThread } from '../../api/communications'
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
  const { busyAction, handleMarkRead, handleAutoAssign, load, applyCommandResult, runCommand, threadContext } = model
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
    // Only when switching threads — avoid wiping the form on every thread object refresh.
  }, [thread.id, t])

  const saveManualAssignee = async () => {
    setAssigneeBusy(true)
    setAssigneeOk(false)
    setAssigneeSaveError(null)
    try {
      const draft = String(assigneeDraft || '').trim()
      const result = draft
        ? await model.runCommand(thread.assignee_id ? 'ReassignThread' : 'AssignThread', {
            assignee_id: draft,
            reason: 'manual',
          })
        : await model.runCommand('UnassignThread', { reason: 'manual' })
      applyCommandResult?.(result)
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

  const applyThreadFolderCommand = async (
    command: 'CloseThread' | 'ReopenThread',
    exitCenter: boolean,
  ) => {
    setFolderBusy(true)
    setFolderError(null)
    try {
      const result = await model.runCommand(command)
      applyCommandResult?.(result)
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
    <div className="space-y-4 p-4 xl:p-0">
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

      {hideEntityLinkForms && <CommunicationsInboxThreadContextCard thread={thread} managerOptions={managerOptions} />}

      {!hideEntityLinkForms && (
        <>
          {unlinked && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
              {compact
                ? t('app.communications_inbox_center.unlinked_hint_short')
                : t('app.communications_inbox_center.unlinked_hint')}
            </div>
          )}
          <div className="card p-4">
            <CommunicationsThreadEntityLinkForms
              thread={thread}
              compact={compact}
              onAfterPatch={afterEntityPatch}
              runCommand={runCommand}
            />
          </div>
        </>
      )}

      <div className="card p-4">
        <h3 className="text-sm font-semibold text-slate-900">
          {t('app.communications_inbox_center.task_section_title')}
        </h3>
        {!compact && (
          <p className="mt-1 text-xs text-slate-500">
            {t('app.communications_inbox_center.task_section_hint')}
          </p>
        )}
        <form className="mt-3 space-y-2" onSubmit={(ev) => void submitFollowUpTask(ev)}>
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
              className="input mt-1 min-h-[4rem] w-full resize-y text-sm"
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
            {taskBusy
              ? t('common.loading')
              : t('app.communications_inbox_center.task_submit')}
          </button>
        </form>
      </div>

      <CommunicationsInboxWorkflowCard thread={thread} onRefresh={load} runCommand={runCommand} />

      <div className="card p-4">
        <h3 className="text-sm font-semibold text-slate-900">
          {t('app.communications_inbox_center.ops_state')}
        </h3>
        <dl className="mt-3 space-y-1 text-xs text-slate-600">
          <div className="flex justify-between gap-2">
            <dt>{t('app.communications.queue.assignee')}</dt>
            <dd className="max-w-[65%] text-right text-xs">
              {thread.assignee_id
                ? managerOptions.find((m) => String(m.id) === String(thread.assignee_id))?.label ||
                  String(thread.assignee_id).slice(0, 8)
                : '—'}
            </dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>{t('app.communications_inbox_center.priority_label')}</dt>
            <dd className="text-right">{thread.priority || '—'}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>{t('app.communications_inbox_center.sla_due')}</dt>
            <dd className="text-right">
              <ThreadWorkspaceSlaChip
                workState={threadContext?.work_state}
                runCommand={runCommand}
                interactive
              />
              {!threadContext?.work_state?.sla && !threadContext?.work_state?.sla_due_at
                ? formatThreadDateTime(thread.sla_due_at)
                : null}
            </dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>{t('app.communications.labels.unread')}</dt>
            <dd className="text-right">
              {threadContext?.work_state?.unread_count ?? thread.unread_count ?? 0}
            </dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>{t('app.communications.email.preview.status')}</dt>
            <dd className="text-right">
              {threadContext?.identity?.thread?.status || thread.status || '—'}
            </dd>
          </div>
        </dl>
        <div className="mt-3 space-y-2 border-t border-slate-100 pt-3">
          <div className="text-xs font-medium text-slate-700">
            {t('app.communications_inbox_center.assign_manager_title')}
          </div>
          {assigneeSaveError ? (
            <p className="text-xs text-rose-600">
              {assigneeSaveError.title}
              {assigneeSaveError.detail ? ` — ${assigneeSaveError.detail}` : ''}
            </p>
          ) : null}
          <select
            className="input w-full text-sm"
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
          <button
            type="button"
            className="btn-primary btn-sm w-full disabled:opacity-50"
            disabled={assigneeBusy || folderBusy}
            onClick={() => void saveManualAssignee()}
          >
            {assigneeBusy
              ? t('common.loading')
              : t('common.actions.save')}
          </button>
          {assigneeOk && (
            <p className="text-xs text-emerald-700">
              {t('app.communications_inbox_center.assignee_saved')}
            </p>
          )}
        </div>
        <div className="mt-3 flex flex-col gap-2">
          <button
            type="button"
            className="btn-secondary btn-sm w-full disabled:opacity-50"
            disabled={busyAction === 'assign' || folderBusy}
            onClick={() => void handleAutoAssign()}
          >
            {busyAction === 'assign'
              ? t('common.loading')
              : t('app.communications.queue.auto_assign')}
          </button>
          <button
            type="button"
            className="btn-secondary btn-sm w-full disabled:opacity-50"
            disabled={busyAction === 'read' || (thread.unread_count ?? 0) <= 0 || folderBusy}
            onClick={() => void handleMarkRead()}
          >
            {busyAction === 'read'
              ? t('common.loading')
              : t('app.communications.actions.mark_thread_read')}
          </button>
        </div>
        <div className="mt-4 border-t border-slate-100 pt-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
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
                    void applyThreadFolderCommand('CloseThread', Boolean(onAfterArchiveOrDelete))
                  }
                >
                  {folderBusy
                    ? t('common.loading')
                    : t('app.communications.email.commands.archive')}
                </button>
                <button
                  type="button"
                  className="btn-danger btn-sm w-full disabled:opacity-50"
                  disabled={folderBusy}
                  onClick={() =>
                    void applyThreadFolderCommand('CloseThread', Boolean(onAfterArchiveOrDelete))
                  }
                >
                  {folderBusy
                    ? t('common.loading')
                    : t('app.communications.email.commands.delete')}
                </button>
              </>
            )}
            {(isThreadArchived || isThreadDeleted) && (
              <button
                type="button"
                className="btn-secondary btn-sm w-full disabled:opacity-50"
                disabled={folderBusy}
                onClick={() => void applyThreadFolderCommand('ReopenThread', false)}
              >
                {folderBusy
                  ? t('common.loading')
                  : isThreadDeleted
                    ? t('app.communications.email.commands.restore')
                    : t('app.communications.email.commands.unarchive')}
              </button>
            )}
          </div>
          {isThreadInboxActive && onAfterArchiveOrDelete && (
            <p className="mt-2 text-[11px] leading-snug text-slate-500">
              {t('app.communications_inbox_center.folder_exit_hint')}
            </p>
          )}
        </div>
      </div>

      <div className="card p-4">
        <h3 className="text-sm font-semibold text-slate-900">
          {t('app.communications_inbox_center.quick_links')}
        </h3>
        <ul className="mt-3 space-y-2 text-sm">
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
    </div>
  )
}
