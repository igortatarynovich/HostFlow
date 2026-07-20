import { useState } from 'react'
import type { WorkspaceCommandName, WorkspaceCommandResult } from '../../api/communications'
import { useI18n } from '../../i18n'
import { formatThreadDateTime } from './CommunicationsThreadWorkArea'

type RunCommand = (
  command: WorkspaceCommandName,
  body?: Record<string, unknown>,
) => Promise<WorkspaceCommandResult>

/** C1.3 — active ThreadNextAction from ThreadContext + Workspace Commands. */
export default function ThreadNextActionPanel({
  nextAction,
  runCommand,
  compact,
}: {
  nextAction?: Record<string, unknown> | null
  runCommand: RunCommand
  compact?: boolean
}) {
  const { t } = useI18n()
  const [busy, setBusy] = useState<'complete' | 'cancel' | 'set' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [draftType, setDraftType] = useState('follow_up')

  const active = nextAction && String(nextAction.status || 'active') === 'active' ? nextAction : null
  const actionType = active ? String(active.action_type || active.actionType || 'action') : null
  const dueAt = active ? (active.due_at as string | null | undefined) : null
  const note = active ? String(active.note || '') : ''

  const run = async (kind: 'complete' | 'cancel' | 'set') => {
    setBusy(kind)
    setError(null)
    try {
      if (kind === 'complete') {
        await runCommand('CompleteNextAction', {
          next_action_id: active?.id ? String(active.id) : undefined,
        })
      } else if (kind === 'cancel') {
        await runCommand('CancelNextAction', {
          next_action_id: active?.id ? String(active.id) : undefined,
        })
      } else {
        await runCommand('SetNextAction', {
          action_type: draftType.trim() || 'follow_up',
          source: 'manual',
        })
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err || 'failed'))
    } finally {
      setBusy(null)
    }
  }

  return (
    <div
      className={
        compact
          ? 'rounded border border-slate-200 bg-slate-50 px-2 py-1.5 text-[11px] text-slate-700'
          : 'rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700'
      }
    >
      <div className="font-semibold text-slate-900">
        {t('app.communications.next_action.title', { defaultValue: 'Next action' })}
      </div>
      {active ? (
        <div className="mt-1 space-y-1">
          <div>
            <span className="font-medium">{actionType}</span>
            {dueAt ? <span className="text-slate-500"> · {formatThreadDateTime(dueAt)}</span> : null}
          </div>
          {note ? <div className="text-slate-500">{note}</div> : null}
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            <button
              type="button"
              className="btn-secondary btn-sm disabled:opacity-50"
              disabled={busy != null}
              onClick={() => void run('complete')}
            >
              {busy === 'complete'
                ? t('common.loading')
                : t('app.communications.next_action.complete', { defaultValue: 'Complete' })}
            </button>
            <button
              type="button"
              className="btn-secondary btn-sm disabled:opacity-50"
              disabled={busy != null}
              onClick={() => void run('cancel')}
            >
              {busy === 'cancel'
                ? t('common.loading')
                : t('app.communications.next_action.cancel', { defaultValue: 'Cancel' })}
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-1 space-y-1.5">
          <div className="text-slate-500">
            {t('app.communications.next_action.empty', { defaultValue: 'No active next action.' })}
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <input
              className="input input-sm min-w-[8rem] flex-1"
              value={draftType}
              onChange={(e) => setDraftType(e.target.value)}
              placeholder={t('app.communications.next_action.type_placeholder', {
                defaultValue: 'Action type',
              })}
            />
            <button
              type="button"
              className="btn-secondary btn-sm disabled:opacity-50"
              disabled={busy != null || !draftType.trim()}
              onClick={() => void run('set')}
            >
              {busy === 'set'
                ? t('common.loading')
                : t('app.communications.next_action.set', { defaultValue: 'Set' })}
            </button>
          </div>
        </div>
      )}
      {error ? <div className="mt-1 text-rose-700">{error}</div> : null}
    </div>
  )
}
