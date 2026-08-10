import { useEffect, useState } from 'react'
import clsx from 'clsx'
import {
  executeWorkspaceCommand,
  getCommunicationsSettings,
  type CommunicationThread,
  type WorkspaceCommandName,
  type WorkspaceCommandResult,
} from '../../api/communications'
import type { ManagerOption } from '../../api/types'
import { listTenantManagers } from '../../api/users'
import { useI18n } from '../../i18n'
import { useAuth } from '../../store/useAuth'
import {
  noReplyNeededFromThread,
  opsModeFromThread,
  slaMutedFromThread,
  slaSnoozedUntilFromThread,
  type CommunicationOpsMode,
} from '../../utils/communicationsOpsMode'
import { formatThreadDateTime } from './CommunicationsThreadWorkArea'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyFormHintError, getFriendlyErrorInfo } from '../../utils/friendlyError'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'

const DEFAULT_ESCALATION_ROLE_OPTIONS = ['administrator', 'employee', 'supervisor', 'admin', 'manager'] as const
const DEFAULT_ESCALATION_QUEUE_OPTIONS = ['priority', 'manual_review', 'supervisor_desk'] as const

type Props = {
  thread: CommunicationThread
  onRefresh: () => Promise<void>
  runCommand?: (
    command: WorkspaceCommandName,
    body?: Record<string, unknown>,
  ) => Promise<WorkspaceCommandResult>
}

export default function CommunicationsInboxWorkflowCard({ thread, onRefresh, runCommand }: Props) {
  const exec = async (command: WorkspaceCommandName, body?: Record<string, unknown>) => {
    if (runCommand) return runCommand(command, body)
    return executeWorkspaceCommand(thread.id, command, body)
  }
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const { me } = useAuth()
  const [busy, setBusy] = useState(false)
  const [workflowError, setWorkflowError] = useState<FriendlyErrorInfo | null>(null)
  const [pauseModalOpen, setPauseModalOpen] = useState(false)
  const [pauseHoursDraft, setPauseHoursDraft] = useState('4')
  const [escalationModalOpen, setEscalationModalOpen] = useState(false)
  const [escalationReasonDraft, setEscalationReasonDraft] = useState('')
  const [escalationTargetTypeDraft, setEscalationTargetTypeDraft] = useState<'role' | 'queue' | 'user'>('role')
  const [escalationTargetValueDraft, setEscalationTargetValueDraft] = useState('supervisor')
  const [escalationRoleOptions, setEscalationRoleOptions] = useState<string[]>([...DEFAULT_ESCALATION_ROLE_OPTIONS])
  const [escalationQueueOptions, setEscalationQueueOptions] = useState<string[]>([...DEFAULT_ESCALATION_QUEUE_OPTIONS])
  const [managerOptions, setManagerOptions] = useState<ManagerOption[]>([])

  useEffect(() => {
    let mounted = true
    void (async () => {
      try {
        const rows = await listTenantManagers()
        if (mounted) setManagerOptions(Array.isArray(rows) ? rows : [])
      } catch {
        if (mounted) setManagerOptions([])
      }
    })()
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    let mounted = true
    void (async () => {
      try {
        const settings = await getCommunicationsSettings()
        if (!mounted) return
        const roles = settings?.access?.roles
        const roleBag = new Set<string>()
        const keys: Array<keyof NonNullable<typeof roles>> = [
          'messages',
          'email',
          'calendar',
          'planner',
          'teamAvailability',
          'myAvailability',
          'timeOffRequests',
          'communicationsAdmin',
        ]
        for (const k of keys) {
          const arr = Array.isArray(roles?.[k]) ? roles?.[k] : []
          for (const role of arr || []) {
            const normalized = String(role || '').trim().toLowerCase()
            if (normalized) roleBag.add(normalized)
          }
        }
        const nextRoles = Array.from(roleBag)
        setEscalationRoleOptions(nextRoles.length ? nextRoles : [...DEFAULT_ESCALATION_ROLE_OPTIONS])
        const queueTargets = Array.isArray(settings?.sla?.escalationTargets)
          ? settings.sla.escalationTargets.map((x) => String(x || '').trim()).filter(Boolean)
          : []
        setEscalationQueueOptions(queueTargets.length ? queueTargets : [...DEFAULT_ESCALATION_QUEUE_OPTIONS])
      } catch {
        if (mounted) {
          setEscalationRoleOptions([...DEFAULT_ESCALATION_ROLE_OPTIONS])
          setEscalationQueueOptions([...DEFAULT_ESCALATION_QUEUE_OPTIONS])
        }
      }
    })()
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    if (escalationTargetTypeDraft === 'role') {
      const fallback = escalationRoleOptions[0] || 'supervisor'
      if (!escalationRoleOptions.includes(escalationTargetValueDraft)) {
        setEscalationTargetValueDraft(fallback)
      }
      return
    }
    if (escalationTargetTypeDraft === 'queue') {
      const fallback = escalationQueueOptions[0] || 'priority'
      if (!escalationQueueOptions.includes(escalationTargetValueDraft)) {
        setEscalationTargetValueDraft(fallback)
      }
      return
    }
    const userIds = new Set(managerOptions.map((m) => String(m.id)))
    if (!userIds.has(escalationTargetValueDraft)) {
      setEscalationTargetValueDraft(String(managerOptions[0]?.id || ''))
    }
  }, [escalationTargetTypeDraft, escalationTargetValueDraft, escalationRoleOptions, escalationQueueOptions, managerOptions])

  const opsModeText = (mode: CommunicationOpsMode | null): string => {
    if (!mode) return t('app.communications_messages.ops.none', { defaultValue: 'No mode' })
    return t(`app.communications_messages.ops.${mode}`, { defaultValue: mode })
  }

  const escalationApiErrorText = (err: unknown): string | null => {
    const anyErr = err as { response?: { data?: { detail?: unknown } } }
    const detail = anyErr?.response?.data?.detail as Record<string, unknown> | undefined
    const code = String(detail?.code || '').trim().toLowerCase()
    if (!code) return null
    if (code === 'ops_escalation_reason_required') {
      return t('app.communications_messages.ops.escalation_reason_required', { defaultValue: 'Escalation reason is required.' })
    }
    if (code === 'ops_escalation_target_required') {
      return t('app.communications_messages.ops.escalation_target_required', { defaultValue: 'Escalation target is required.' })
    }
    if (code === 'ops_escalation_target_unknown_queue') {
      const allowed = Array.isArray(detail?.allowed_targets)
        ? (detail.allowed_targets as unknown[]).map((x) => String(x || '').trim()).filter(Boolean).join(', ')
        : ''
      return t('app.communications_messages.ops.escalation_error_unknown_queue', {
        defaultValue: allowed
          ? 'Selected queue is not allowed. Allowed queues: {allowed}.'
          : 'Selected queue is not allowed for this tenant.',
        values: { allowed },
      })
    }
    if (code === 'ops_escalation_target_invalid_role') {
      return t('app.communications_messages.ops.escalation_error_invalid_role', {
        defaultValue: 'Role target has invalid format.',
      })
    }
    if (code === 'ops_escalation_target_unknown_role') {
      const allowed = Array.isArray(detail?.allowed_roles)
        ? (detail.allowed_roles as unknown[]).map((x) => String(x || '').trim()).filter(Boolean).join(', ')
        : ''
      return t('app.communications_messages.ops.escalation_error_unknown_role', {
        defaultValue: allowed ? 'Unknown role. Allowed: {allowed}.' : 'Unknown role.',
        values: { allowed },
      })
    }
    return null
  }

  const toWorkflowApiError = (err: unknown): FriendlyErrorInfo => {
    const line = escalationApiErrorText(err)
    return line
      ? friendlyFormHintError(line, t)
      : getFriendlyErrorInfo(
          err,
          t('app.communications_inbox_center.workflow_error_generic', { defaultValue: 'Update failed.' }),
          t,
        )
  }

  const toggleNoReplyNeeded = async () => {
    setBusy(true)
    setWorkflowError(null)
    try {
      const current = noReplyNeededFromThread(thread)
      const threadMeta = (thread.thread_meta || {}) as Record<string, unknown>
      const slaPolicy = (threadMeta.sla_policy || {}) as Record<string, unknown>
      await exec( 'UpdateThreadWorkflow', {
        thread_meta: {
          ...threadMeta,
          no_reply_needed: !current,
          sla_policy: {
            ...slaPolicy,
            no_reply_needed: !current,
            ...(current ? {} : { snoozed_until: null }),
          },
        },
      })
      await onRefresh()
    } catch (err: unknown) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications_inbox_center.workflow_error_generic', { defaultValue: 'Update failed.' }),
        )
      ) {
        setWorkflowError(toWorkflowApiError(err))
      }
    } finally {
      setBusy(false)
    }
  }

  const toggleSlaMuted = async () => {
    setBusy(true)
    setWorkflowError(null)
    try {
      const current = slaMutedFromThread(thread)
      const threadMeta = (thread.thread_meta || {}) as Record<string, unknown>
      const slaPolicy = (threadMeta.sla_policy || {}) as Record<string, unknown>
      await exec( 'UpdateThreadWorkflow', {
        thread_meta: {
          ...threadMeta,
          sla_muted: !current,
          sla_policy: {
            ...slaPolicy,
            muted: !current,
          },
        },
      })
      await onRefresh()
    } catch (err: unknown) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications_inbox_center.workflow_error_generic', { defaultValue: 'Update failed.' }),
        )
      ) {
        setWorkflowError(
          getFriendlyErrorInfo(
            err,
            t('app.communications_inbox_center.workflow_error_generic', { defaultValue: 'Update failed.' }),
            t,
          ),
        )
      }
    } finally {
      setBusy(false)
    }
  }

  const snoozeSla = async (hours: number) => {
    if (noReplyNeededFromThread(thread)) return
    setBusy(true)
    setWorkflowError(null)
    try {
      const until = new Date(Date.now() + Math.max(1, hours) * 60 * 60 * 1000).toISOString()
      const threadMeta = (thread.thread_meta || {}) as Record<string, unknown>
      const slaPolicy = (threadMeta.sla_policy || {}) as Record<string, unknown>
      await exec( 'UpdateThreadWorkflow', {
        thread_meta: {
          ...threadMeta,
          no_reply_needed: false,
          sla_policy: {
            ...slaPolicy,
            no_reply_needed: false,
            snoozed_until: until,
          },
        },
      })
      await onRefresh()
    } catch (err: unknown) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications_inbox_center.workflow_error_generic', { defaultValue: 'Update failed.' }),
        )
      ) {
        setWorkflowError(
          getFriendlyErrorInfo(
            err,
            t('app.communications_inbox_center.workflow_error_generic', { defaultValue: 'Update failed.' }),
            t,
          ),
        )
      }
    } finally {
      setBusy(false)
    }
  }

  const setOpsMode = async (
    mode: CommunicationOpsMode,
    options?: {
      pausedUntil?: string | null
      escalationReason?: string
      escalationTargetRole?: string
      escalationTargetQueue?: string
      escalationTargetUserId?: string
    },
  ) => {
    setBusy(true)
    setWorkflowError(null)
    try {
      const threadMeta = (thread.thread_meta || {}) as Record<string, unknown>
      const slaPolicy = (threadMeta.sla_policy || {}) as Record<string, unknown>
      const ops = (threadMeta.ops || {}) as Record<string, unknown>
      const nowIso = new Date().toISOString()
      const noReply = mode === 'no_reply_needed'
      const escalationTarget: Record<string, unknown> = {
        ...(options?.escalationTargetRole ? { role: String(options.escalationTargetRole).trim() } : {}),
        ...(options?.escalationTargetQueue ? { queue: String(options.escalationTargetQueue).trim() } : {}),
        ...(options?.escalationTargetUserId ? { user_id: String(options.escalationTargetUserId).trim() } : {}),
      }
      const nextOps: Record<string, unknown> = {
        ...ops,
        mode,
        updated_at: nowIso,
        by_user_id: me?.sub || null,
      }
      if (mode === 'later') {
        nextOps.paused_until = options?.pausedUntil || null
      }
      if (mode === 'escalated') {
        nextOps.escalation = {
          ...((ops.escalation || {}) as Record<string, unknown>),
          reason: String(options?.escalationReason || '').trim(),
          target: escalationTarget,
          escalated_at: nowIso,
        }
      }
      await exec( 'UpdateThreadWorkflow', {
        thread_meta: {
          ...threadMeta,
          no_reply_needed: noReply,
          ops: nextOps,
          sla_policy: {
            ...slaPolicy,
            no_reply_needed: noReply,
            ...(noReply ? { snoozed_until: null } : {}),
            ...(mode === 'later' ? { snoozed_until: options?.pausedUntil || null } : {}),
          },
        },
      })
      if (mode === 'escalated' && String(thread.priority || '').toLowerCase() !== 'high') {
        await exec( 'SetThreadPriority', { priority: 'high' })
      }
      await onRefresh()
    } catch (err: unknown) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications_inbox_center.workflow_error_generic', { defaultValue: 'Update failed.' }),
        )
      ) {
        setWorkflowError(toWorkflowApiError(err))
      }
    } finally {
      setBusy(false)
    }
  }

  const submitPauseOpsMode = async () => {
    const hours = Number(pauseHoursDraft)
    if (!Number.isFinite(hours) || hours <= 0) {
      setWorkflowError(
        friendlyFormHintError(
          t('app.communications_messages.ops.pause_hours_invalid', { defaultValue: 'Enter a valid number of hours (> 0).' }),
          t,
        ),
      )
      return
    }
    const pausedUntil = new Date(Date.now() + hours * 60 * 60 * 1000).toISOString()
    await setOpsMode('later', { pausedUntil })
    setPauseModalOpen(false)
  }

  const submitEscalationOpsMode = async () => {
    const reason = escalationReasonDraft.trim()
    if (!reason) {
      setWorkflowError(
        friendlyFormHintError(
          t('app.communications_messages.ops.escalation_reason_required', { defaultValue: 'Escalation reason is required.' }),
          t,
        ),
      )
      return
    }
    const targetValue = escalationTargetValueDraft.trim()
    if (!targetValue) {
      setWorkflowError(
        friendlyFormHintError(
          t('app.communications_messages.ops.escalation_target_required', { defaultValue: 'Escalation target is required.' }),
          t,
        ),
      )
      return
    }
    const escalationTargetRole = escalationTargetTypeDraft === 'role' ? targetValue : ''
    const escalationTargetQueue = escalationTargetTypeDraft === 'queue' ? targetValue : ''
    const escalationTargetUserId = escalationTargetTypeDraft === 'user' ? targetValue : ''
    await setOpsMode('escalated', {
      escalationReason: reason,
      escalationTargetRole,
      escalationTargetQueue,
      escalationTargetUserId,
    })
    setEscalationModalOpen(false)
  }

  const mode = opsModeFromThread(thread)
  const snoozed = slaSnoozedUntilFromThread(thread)

  return (
    <>
      <div className="card p-4">
        <h3 className="text-sm font-semibold text-slate-900">
          {t('app.communications_messages.action_groups.workflow', { defaultValue: 'Workflow' })}
        </h3>
        <p className="mt-1 text-xs text-slate-500">
          {t('app.communications_inbox_center.workflow_hint', {
            defaultValue: 'Operational mode, reply requirement, and SLA — same rules as Messages.',
          })}
        </p>
        {workflowError ? (
          <p className="mt-2 text-xs text-rose-600">
            {workflowError.title}
            {workflowError.detail ? ` — ${workflowError.detail}` : ''}
          </p>
        ) : null}
        <div className="mt-3 space-y-2 text-xs text-slate-600">
          <div className="flex flex-wrap justify-between gap-2">
            <span>{t('app.communications_inbox_center.workflow_current_mode', { defaultValue: 'Mode' })}</span>
            <span className="font-medium text-slate-800">{opsModeText(mode)}</span>
          </div>
          {snoozed ? (
            <div className="flex flex-wrap justify-between gap-2">
              <span>{t('app.communications_inbox_center.workflow_sla_snoozed', { defaultValue: 'SLA snoozed until' })}</span>
              <span className="text-right">{formatThreadDateTime(snoozed)}</span>
            </div>
          ) : null}
        </div>
        <div className="mt-3 flex flex-col gap-2">
          <button
            type="button"
            className={clsx(
              'btn-secondary btn-sm w-full disabled:opacity-50',
              noReplyNeededFromThread(thread) && 'border-emerald-300 bg-emerald-50 text-emerald-900',
            )}
            disabled={busy}
            onClick={() => void toggleNoReplyNeeded()}
          >
            {noReplyNeededFromThread(thread)
              ? t('app.communications_messages.ops.no_reply_needed')
              : t('app.communications_messages.reply_required')}
          </button>
          <button
            type="button"
            className={clsx(
              'btn-secondary btn-sm w-full disabled:opacity-50',
              mode === 'in_work' && 'border-emerald-300 bg-emerald-50 text-emerald-900',
            )}
            disabled={busy}
            onClick={() => void setOpsMode('in_work')}
          >
            {t('app.communications_messages.ops.in_work')}
          </button>
          <button
            type="button"
            className={clsx(
              'btn-secondary btn-sm w-full disabled:opacity-50',
              mode === 'later' && 'border-amber-200 bg-amber-50 text-amber-900',
            )}
            disabled={busy}
            onClick={() => {
              setPauseHoursDraft('4')
              setPauseModalOpen(true)
            }}
          >
            {t('app.communications_messages.ops.later')}
          </button>
          <button
            type="button"
            className={clsx(
              'btn-secondary btn-sm w-full disabled:opacity-50',
              mode === 'escalated' && 'border-rose-200 bg-rose-50 text-rose-900',
            )}
            disabled={busy}
            title={t('app.communications_messages.ops.escalated_hint', {
              defaultValue: 'Escalation routes this dialog for supervisor attention and requires a reason.',
            })}
            onClick={() => {
              setEscalationReasonDraft('')
              setEscalationTargetTypeDraft('role')
              setEscalationTargetValueDraft(String(escalationRoleOptions[0] || 'supervisor'))
              setEscalationModalOpen(true)
            }}
          >
            {t('app.communications_messages.ops.escalated')}
          </button>
        </div>
        <div className="mt-4 border-t border-slate-100 pt-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.communications_messages.action_groups.sla', { defaultValue: 'SLA' })}
          </div>
          <div className="mt-2 flex flex-col gap-2">
            <button
              type="button"
              className={clsx(
                'btn-secondary btn-sm w-full disabled:opacity-50',
                slaMutedFromThread(thread) && 'border-amber-200 bg-amber-50 text-amber-900',
              )}
              disabled={busy}
              onClick={() => void toggleSlaMuted()}
            >
              {slaMutedFromThread(thread)
                ? t('app.communications_messages.sla.sla_muted')
                : t('app.communications_messages.sla.mute_sla')}
            </button>
            <button
              type="button"
              className="btn-secondary btn-sm w-full disabled:opacity-50"
              disabled={busy || noReplyNeededFromThread(thread) || slaMutedFromThread(thread)}
              onClick={() => void snoozeSla(1)}
            >
              {t('app.communications_messages.sla.snooze_1h', { defaultValue: 'Snooze +1h' })}
            </button>
            <button
              type="button"
              className="btn-secondary btn-sm w-full disabled:opacity-50"
              disabled={busy || noReplyNeededFromThread(thread) || slaMutedFromThread(thread)}
              onClick={() => void snoozeSla(4)}
            >
              {t('app.communications_messages.sla.snooze_4h', { defaultValue: 'Snooze +4h' })}
            </button>
          </div>
        </div>
      </div>

      {pauseModalOpen && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-4 shadow-xl">
            <div className="mb-3 text-sm font-semibold text-slate-900">
              {t('app.communications_messages.ops.pause_modal_title', { defaultValue: 'Pause dialog' })}
            </div>
            <label className="block">
              <div className="mb-1 text-xs font-medium text-slate-600">
                {t('app.communications_messages.ops.pause_hours_label', { defaultValue: 'Pause duration (hours)' })}
              </div>
              <input
                type="number"
                min={1}
                step={1}
                value={pauseHoursDraft}
                onChange={(e) => setPauseHoursDraft(e.target.value)}
                className="w-full input"
              />
            </label>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setPauseModalOpen(false)} className="btn-secondary btn-sm">
                {t('common.actions.cancel', { defaultValue: 'Cancel' })}
              </button>
              <button
                type="button"
                onClick={() => void submitPauseOpsMode()}
                disabled={busy}
                className="btn-primary btn-sm disabled:opacity-50"
              >
                {t('common.actions.apply', { defaultValue: 'Apply' })}
              </button>
            </div>
          </div>
        </div>
      )}

      {escalationModalOpen && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-lg border border-slate-200 bg-white p-4 shadow-xl">
            <div className="mb-3 text-sm font-semibold text-slate-900">
              {t('app.communications_messages.ops.escalation_modal_title', { defaultValue: 'Escalate dialog' })}
            </div>
            <div className="space-y-2">
              <label className="block">
                <div className="mb-1 text-xs font-medium text-slate-600">
                  {t('app.communications_messages.ops.escalation_reason_prompt', { defaultValue: 'Escalation reason' })}
                </div>
                <textarea
                  rows={3}
                  value={escalationReasonDraft}
                  onChange={(e) => setEscalationReasonDraft(e.target.value)}
                  className="w-full textarea"
                />
              </label>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
                <label className="block md:col-span-1">
                  <div className="mb-1 text-xs font-medium text-slate-600">
                    {t('app.communications_messages.ops.escalation_target_type_label', { defaultValue: 'Target type' })}
                  </div>
                  <select
                    value={escalationTargetTypeDraft}
                    onChange={(e) => setEscalationTargetTypeDraft(e.target.value as 'role' | 'queue' | 'user')}
                    className="w-full input"
                  >
                    <option value="role">{t('app.communications_messages.ops.target_type_role', { defaultValue: 'Role' })}</option>
                    <option value="queue">{t('app.communications_messages.ops.target_type_queue', { defaultValue: 'Queue' })}</option>
                    <option value="user">{t('app.communications_messages.ops.target_type_user', { defaultValue: 'User' })}</option>
                  </select>
                </label>
                <label className="block md:col-span-2">
                  <div className="mb-1 text-xs font-medium text-slate-600">
                    {t('app.communications_messages.ops.escalation_target_value_label', { defaultValue: 'Target value' })}
                  </div>
                  {escalationTargetTypeDraft === 'role' && (
                    <select
                      value={escalationTargetValueDraft}
                      onChange={(e) => setEscalationTargetValueDraft(e.target.value)}
                      className="w-full input"
                    >
                      {escalationRoleOptions.map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                  )}
                  {escalationTargetTypeDraft === 'queue' && (
                    <select
                      value={escalationTargetValueDraft}
                      onChange={(e) => setEscalationTargetValueDraft(e.target.value)}
                      className="w-full input"
                    >
                      {escalationQueueOptions.map((queueId) => (
                        <option key={queueId} value={queueId}>
                          {queueId}
                        </option>
                      ))}
                    </select>
                  )}
                  {escalationTargetTypeDraft === 'user' && (
                    <select
                      value={escalationTargetValueDraft}
                      onChange={(e) => setEscalationTargetValueDraft(e.target.value)}
                      className="w-full input"
                    >
                      {managerOptions.length === 0 && (
                        <option value="">{t('app.communications_messages.manager.unassigned')}</option>
                      )}
                      {managerOptions.map((m) => (
                        <option key={m.id} value={String(m.id)}>
                          {String(m.label || m.full_name || m.email || m.id)}
                        </option>
                      ))}
                    </select>
                  )}
                </label>
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setEscalationModalOpen(false)} className="btn-secondary btn-sm">
                {t('common.actions.cancel', { defaultValue: 'Cancel' })}
              </button>
              <button
                type="button"
                onClick={() => void submitEscalationOpsMode()}
                disabled={busy}
                className="btn-primary btn-sm disabled:opacity-50"
              >
                {t('common.actions.apply', { defaultValue: 'Apply' })}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
