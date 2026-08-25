import { useState } from 'react'
import clsx from 'clsx'
import type {
  ThreadContext,
  WorkspaceCommandName,
  WorkspaceCommandResult,
} from '../../api/communications'
import { useI18n } from '../../i18n'
import { formatThreadDateTime } from './CommunicationsThreadWorkArea'

type RunCommand = (
  command: WorkspaceCommandName,
  body?: Record<string, unknown>,
) => Promise<WorkspaceCommandResult>

/** C1.3 — SLA indicator from ThreadContext + Pause/Resume Commands. */
export default function ThreadWorkspaceSlaChip({
  workState,
  runCommand,
  interactive,
}: {
  workState?: ThreadContext['work_state'] | null
  runCommand?: RunCommand
  /** Show Pause/Resume controls (header/control panel). */
  interactive?: boolean
}) {
  const { t } = useI18n()
  const [busy, setBusy] = useState(false)
  const sla = workState?.sla
  if (!sla && !workState?.sla_due_at) return null

  const status = String(sla?.status || '').toLowerCase()
  const breached = Boolean(sla?.breached) || status === 'breached'
  const paused = Boolean(sla?.paused) || status === 'paused'
  const resolved = status === 'resolved' || status === 'none'
  const due = sla?.target_due_at || workState?.sla_due_at || null
  const canToggle = Boolean(interactive && runCommand && !resolved && (due || paused || status === 'running' || breached))

  if (!due && !breached && !paused && (status === 'none' || !status)) return null

  const onToggle = async () => {
    if (!runCommand || busy) return
    setBusy(true)
    try {
      await runCommand(paused ? 'ResumeSLA' : 'PauseSLA')
    } catch {
      // parent surfaces errors via threadError when using model.runCommand
    } finally {
      setBusy(false)
    }
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium',
        breached
          ? 'bg-rose-100 text-rose-800'
          : paused
            ? 'bg-amber-100 text-amber-900'
            : 'bg-slate-100 text-slate-700',
      )}
      title={due ? formatThreadDateTime(due) : undefined}
    >
      {breached
        ? t('app.communications.sla.breached', { defaultValue: 'SLA breached' })
        : paused
          ? t('app.communications.sla.paused', { defaultValue: 'SLA paused' })
          : t('app.communications.sla.due', { defaultValue: 'SLA' })}
      {due ? <span className="font-normal opacity-80">· {formatThreadDateTime(due)}</span> : null}
      {canToggle ? (
        <button
          type="button"
          className="ml-0.5 rounded border border-current/20 px-1 py-px text-[10px] font-semibold uppercase tracking-wide opacity-90 hover:opacity-100 disabled:opacity-50"
          disabled={busy}
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()
            void onToggle()
          }}
        >
          {busy
            ? '…'
            : paused
              ? t('app.communications.sla.resume', { defaultValue: 'Resume' })
              : t('app.communications.sla.pause', { defaultValue: 'Pause' })}
        </button>
      ) : null}
    </span>
  )
}
