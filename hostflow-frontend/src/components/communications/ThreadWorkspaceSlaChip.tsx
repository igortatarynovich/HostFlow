import clsx from 'clsx'
import type { ThreadContext } from '../../api/communications'
import { useI18n } from '../../i18n'
import { formatThreadDateTime } from './CommunicationsThreadWorkArea'

/** C1.3 — SLA indicator from ThreadContext.work_state.sla (event clock projection). */
export default function ThreadWorkspaceSlaChip({
  workState,
}: {
  workState?: ThreadContext['work_state'] | null
}) {
  const { t } = useI18n()
  const sla = workState?.sla
  if (!sla && !workState?.sla_due_at) return null

  const status = String(sla?.status || '').toLowerCase()
  const breached = Boolean(sla?.breached) || status === 'breached'
  const paused = Boolean(sla?.paused) || status === 'paused'
  const due = sla?.target_due_at || workState?.sla_due_at || null

  if (!due && !breached && !paused && status === 'none') return null

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
    </span>
  )
}
