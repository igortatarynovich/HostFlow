import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconExternalLink, IconListCheck, IconShield } from '@tabler/icons-react'
import { patchCommunicationThread, type CommunicationThread } from '../../api/communications'
import { createReminder } from '../../api/client'
import { listTenantManagers } from '../../api/users'
import type { ManagerOption } from '../../api/types'
import type { useCommunicationsThread } from '../../hooks/useCommunicationsThread'
import { useI18n } from '../../i18n'
import { isCommunicationThreadUnlinked, uosLinkedServiceOrderId } from '../../utils/communicationThreadUnlinked'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import CommunicationsInboxThreadContextCard from './CommunicationsInboxThreadContextCard'
import CommunicationsInboxWorkflowCard from './CommunicationsInboxWorkflowCard'
import CommunicationsThreadEntityLinkForms from './CommunicationsThreadEntityLinkForms'
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
  const { busyAction, handleMarkRead, handleAutoAssign, load } = model
  const unlinked = isCommunicationThreadUnlinked(thread)
  const cid = String(thread.linked_candidate_id || '').trim()
  const compId = String(thread.linked_company_id || '').trim()
  const linkedOrderId = uosLinkedServiceOrderId(thread.thread_meta)

  const threadStatus = String(thread.status || '').toLowerCase()
  const isThreadDeleted = threadStatus === 'deleted'
  const isThreadArchived = Boolean(thread.is_archived) && !isThreadDeleted
  const isThreadInboxActive = !thread.is_archived && !isThreadDeleted

  const fallbackTitle = t('app.communications_inbox_center.task_default_title', { defaultValue: 'Follow up on conversation' })

  const [taskTitle, setTaskTitle] = useState(() => defaultTitleFromThread(thread))
  const [taskDescription, setTaskDescription] = useState('')
  const [taskDueLocal, setTaskDueLocal] = useState(defaultDueLocal)
  const [taskBusy, setTaskBusy] = useState(false)
  const [taskError, setTaskError] = useState<string | null>(null)
  const [taskCreated, setTaskCreated] = useState(false)

  const [linkError, setLinkError] = useState<string | null>(null)
  const [folderBusy, setFolderBusy] = useState(false)
  const [folderError, setFolderError] = useState<string | null>(null)

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
    const fb = t('app.communications_inbox_center.task_default_title', { defaultValue: 'Follow up on conversation' })
    setTaskTitle(defaultTitleFromThread(thread) || fb)
    setTaskDescription('')
    setTaskDueLocal(defaultDueLocal())
    setTaskError(null)
    setTaskCreated(false)
    setLinkError(null)
    setFolderError(null)
    // Only when switching threads — avoid wiping the form on every thread object refresh.
  }, [thread.id, t])

  const saveManualAssignee = async () => {
    setAssigneeBusy(true)
    setAssigneeOk(false)
    setLinkError(null)
    try {
      await patchCommunicationThread(thread.id, { assignee_id: assigneeDraft || null })
      await load()
      setLinkError(null)
      setAssigneeOk(true)
      await onAfterThreadPatch?.()
    } catch (err: unknown) {
      const fe = getFriendlyErrorInfo(
        err,
        t('app.communications_inbox_center.assignee_save_failed', { defaultValue: 'Could not update assignee.' }),
      )
      setLinkError([fe.title, fe.detail].filter(Boolean).join(' — ') || fe.hint)
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
      const fe = getFriendlyErrorInfo(
        err,
        t('app.communications_inbox_center.folder_error', { defaultValue: 'Could not update thread folder.' }),
      )
      setFolderError([fe.title, fe.detail].filter(Boolean).join(' — ') || fe.hint)
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
      setTaskError(t('app.communications_inbox_center.task_error_due', { defaultValue: 'Choose a valid due date.' }))
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
      const fe = getFriendlyErrorInfo(
        err,
        t('app.communications_inbox_center.task_error_create', { defaultValue: 'Could not create task.' }),
      )
      setTaskError([fe.title, fe.detail].filter(Boolean).join(' — ') || fe.hint)
    } finally {
      setTaskBusy(false)
    }
  }

  return (
    <div className="space-y-4 p-4 xl:p-0">
      {!compact && (
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.communications_inbox_center.control_title', { defaultValue: 'Thread control' })}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.communications_inbox_center.control_subtitle', {
              defaultValue: 'Linked records, SLA, and quick navigation.',
            })}
          </p>
        </div>
      )}

      {hideEntityLinkForms && <CommunicationsInboxThreadContextCard thread={thread} managerOptions={managerOptions} />}

      {!hideEntityLinkForms && (
        <>
          {unlinked && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
              {compact
                ? t('app.communications_inbox_center.unlinked_hint_short', {
                    defaultValue: 'Not linked — use search below.',
                  })
                : t('app.communications_inbox_center.unlinked_hint', {
                    defaultValue:
                      'This thread is not linked to a candidate, client, or service order. Link below to enable full context and outbound where required.',
                  })}
            </div>
          )}
          <div className="card p-4">
            <CommunicationsThreadEntityLinkForms thread={thread} compact={compact} onAfterPatch={afterEntityPatch} />
          </div>
        </>
      )}

      <div className="card p-4">
        <h3 className="text-sm font-semibold text-slate-900">
          {t('app.communications_inbox_center.task_section_title', { defaultValue: 'Follow-up task' })}
        </h3>
        {!compact && (
          <p className="mt-1 text-xs text-slate-500">
            {t('app.communications_inbox_center.task_section_hint', {
              defaultValue: 'Creates a reminder on Tasks. Linked candidate or client is set when available.',
            })}
          </p>
        )}
        <form className="mt-3 space-y-2" onSubmit={(ev) => void submitFollowUpTask(ev)}>
          <label className="block text-xs font-medium text-slate-600">
            {t('app.communications_inbox_center.task_title_label', { defaultValue: 'Title' })}
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
            {t('app.communications_inbox_center.task_due_label', { defaultValue: 'Due' })}
            <input
              type="datetime-local"
              className="input mt-1 w-full text-sm"
              value={taskDueLocal}
              onChange={(ev) => setTaskDueLocal(ev.target.value)}
              disabled={taskBusy}
            />
          </label>
          <label className="block text-xs font-medium text-slate-600">
            {t('app.communications_inbox_center.task_notes_label', { defaultValue: 'Notes (optional)' })}
            <textarea
              className="input mt-1 min-h-[4rem] w-full resize-y text-sm"
              value={taskDescription}
              onChange={(ev) => setTaskDescription(ev.target.value)}
              disabled={taskBusy}
              maxLength={4000}
            />
          </label>
          {taskError && <p className="text-xs text-rose-600">{taskError}</p>}
          {taskCreated && (
            <p className="text-xs text-emerald-700">
              {t('app.communications_inbox_center.task_created', { defaultValue: 'Task created.' })}{' '}
              <Link className="font-medium underline" to="/app/tasks">
                {t('app.communications_inbox_center.task_open_tasks', { defaultValue: 'Open Tasks' })}
              </Link>
            </p>
          )}
          <button type="submit" className="btn-primary btn-sm w-full disabled:opacity-50" disabled={taskBusy}>
            {taskBusy
              ? t('common.loading', { defaultValue: 'Loading...' })
              : t('app.communications_inbox_center.task_submit', { defaultValue: 'Create task' })}
          </button>
        </form>
      </div>

      <CommunicationsInboxWorkflowCard thread={thread} onRefresh={load} />

      <div className="card p-4">
        <h3 className="text-sm font-semibold text-slate-900">
          {t('app.communications_inbox_center.ops_state', { defaultValue: 'Operations' })}
        </h3>
        <dl className="mt-3 space-y-1 text-xs text-slate-600">
          <div className="flex justify-between gap-2">
            <dt>{t('app.communications.queue.assignee', { defaultValue: 'Assignee' })}</dt>
            <dd className="max-w-[65%] text-right text-xs">
              {thread.assignee_id
                ? managerOptions.find((m) => String(m.id) === String(thread.assignee_id))?.label ||
                  String(thread.assignee_id).slice(0, 8)
                : '—'}
            </dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>{t('app.communications_inbox_center.priority_label', { defaultValue: 'Priority' })}</dt>
            <dd className="text-right">{thread.priority || '—'}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>{t('app.communications_inbox_center.sla_due', { defaultValue: 'SLA due' })}</dt>
            <dd className="text-right">{formatThreadDateTime(thread.sla_due_at)}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>{t('app.communications.labels.unread', { defaultValue: 'Unread' })}</dt>
            <dd className="text-right">{thread.unread_count ?? 0}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>{t('app.communications.email.preview.status', { defaultValue: 'Status' })}</dt>
            <dd className="text-right">{thread.status || '—'}</dd>
          </div>
        </dl>
        <div className="mt-3 space-y-2 border-t border-slate-100 pt-3">
          <div className="text-xs font-medium text-slate-700">
            {t('app.communications_inbox_center.assign_manager_title', { defaultValue: 'Назначить менеджера' })}
          </div>
          {linkError && <p className="text-xs text-rose-600">{linkError}</p>}
          <select
            className="input w-full text-sm"
            value={assigneeDraft}
            onChange={(e) => setAssigneeDraft(e.target.value)}
            disabled={assigneeBusy || folderBusy}
          >
            <option value="">{t('app.communications_messages.manager.unassigned', { defaultValue: 'Не назначен' })}</option>
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
              ? t('common.loading', { defaultValue: 'Loading...' })
              : t('app.communications_messages.manager.save', { defaultValue: 'Сохранить' })}
          </button>
          {assigneeOk && (
            <p className="text-xs text-emerald-700">
              {t('app.communications_inbox_center.assignee_saved', { defaultValue: 'Менеджер обновлён.' })}
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
              ? t('common.loading', { defaultValue: 'Loading...' })
              : t('app.communications.queue.auto_assign', { defaultValue: 'Auto assign' })}
          </button>
          <button
            type="button"
            className="btn-secondary btn-sm w-full disabled:opacity-50"
            disabled={busyAction === 'read' || (thread.unread_count ?? 0) <= 0 || folderBusy}
            onClick={() => void handleMarkRead()}
          >
            {busyAction === 'read'
              ? t('common.loading', { defaultValue: 'Loading...' })
              : t('app.communications.actions.mark_thread_read', { defaultValue: 'Mark read' })}
          </button>
        </div>
        <div className="mt-4 border-t border-slate-100 pt-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.communications_inbox_center.folder_section', { defaultValue: 'Archive & trash' })}
          </div>
          {folderError && <p className="mt-2 text-xs text-rose-600">{folderError}</p>}
          <div className="mt-2 flex flex-col gap-2">
            {isThreadInboxActive && (
              <>
                <button
                  type="button"
                  className="btn-secondary btn-sm w-full disabled:opacity-50"
                  disabled={folderBusy}
                  onClick={() =>
                    void applyThreadFolderPatch({ is_archived: true, status: 'archived' }, Boolean(onAfterArchiveOrDelete))
                  }
                >
                  {folderBusy
                    ? t('common.loading', { defaultValue: 'Loading...' })
                    : t('app.communications.email.commands.archive', { defaultValue: 'Archive' })}
                </button>
                <button
                  type="button"
                  className="btn-danger btn-sm w-full disabled:opacity-50"
                  disabled={folderBusy}
                  onClick={() =>
                    void applyThreadFolderPatch({ is_archived: true, status: 'deleted' }, Boolean(onAfterArchiveOrDelete))
                  }
                >
                  {folderBusy
                    ? t('common.loading', { defaultValue: 'Loading...' })
                    : t('app.communications.email.commands.delete', { defaultValue: 'Delete' })}
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
                  ? t('common.loading', { defaultValue: 'Loading...' })
                  : isThreadDeleted
                    ? t('app.communications.email.commands.restore', { defaultValue: 'Restore' })
                    : t('app.communications.email.commands.unarchive', { defaultValue: 'Unarchive' })}
              </button>
            )}
          </div>
          {isThreadInboxActive && onAfterArchiveOrDelete && (
            <p className="mt-2 text-[11px] leading-snug text-slate-500">
              {t('app.communications_inbox_center.folder_exit_hint', {
                defaultValue: 'Archive or delete clears your selection and refreshes the list.',
              })}
            </p>
          )}
        </div>
      </div>

      <div className="card p-4">
        <h3 className="text-sm font-semibold text-slate-900">
          {t('app.communications_inbox_center.quick_links', { defaultValue: 'Quick links' })}
        </h3>
        <ul className="mt-3 space-y-2 text-sm">
          <li>
            <Link className="inline-flex items-center gap-1.5 text-brand-700 hover:text-brand-900" to="/app/tasks">
              <IconListCheck size={16} stroke={1.75} />
              {t('app.nav.items.tasks', { defaultValue: 'Tasks' })}
            </Link>
          </li>
          <li>
            <Link className="inline-flex items-center gap-1.5 text-rose-700 hover:text-rose-900" to="/app/sla-incidents">
              <IconShield size={16} stroke={1.75} />
              {t('app.nav.items.sla_incidents', { defaultValue: 'SLA incidents' })}
            </Link>
          </li>
          <li>
            <Link
              className="inline-flex items-center gap-1.5 text-slate-600 hover:text-slate-900"
              to={`/app/communications/threads/${thread.id}`}
            >
              <IconExternalLink size={16} stroke={1.75} />
              {t('app.communications_inbox_center.classic_view', { defaultValue: 'Classic thread page' })}
            </Link>
          </li>
        </ul>
      </div>
    </div>
  )
}
