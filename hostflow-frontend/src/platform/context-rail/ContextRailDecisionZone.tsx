import clsx from 'clsx'
import { Link } from 'react-router-dom'
import { IconBrandWhatsapp, IconMail, IconPhone } from '@tabler/icons-react'
import type { ObjectDecision } from '../decision-model/types'
import type { DetailRailContactAction } from '../detail-rail/detailRailTypes'

function ContactIcon({
  kind,
  variant,
}: {
  kind: DetailRailContactAction['icon']
  variant?: DetailRailContactAction['variant']
}) {
  if (kind === 'phone') return <IconPhone size={14} stroke={1.8} className={variant === 'primary' ? 'text-white' : undefined} />
  if (kind === 'whatsapp') return <IconBrandWhatsapp size={14} stroke={1.8} className={variant === 'primary' ? 'text-white' : undefined} />
  return <IconMail size={14} stroke={1.8} className={variant === 'primary' ? 'text-white' : undefined} />
}

function DecisionActionButton({
  action,
  size,
}: {
  action: { id: string; label: string; onClick?: () => void; href?: string; disabled?: boolean }
  size: 'primary' | 'secondary' | 'danger'
}) {
  const cls =
    size === 'primary'
      ? 'w-full justify-center rounded-xl bg-brand-700 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-60'
      : size === 'danger'
        ? 'rounded-xl border border-rose-200 bg-white px-4 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-60'
        : 'rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60'
  if (action.href) {
    return (
      <Link to={action.href} className={clsx('inline-flex items-center', cls)} data-entity-link="primary">
        {action.label}
      </Link>
    )
  }
  return (
    <button
      type="button"
      disabled={action.disabled}
      onClick={action.onClick}
      className={clsx('inline-flex items-center', cls)}
    >
      {action.label}
    </button>
  )
}

/**
 * Fixed Decision Zone — one state narrative: current action + why + primary.
 * Not a stack of unrelated blocks.
 */
export function ContextRailDecisionZone({ decision }: { decision: ObjectDecision }) {
  const variant = decision.variant ?? (decision.terminal ? 'terminal' : 'default')

  if (decision.terminal && decision.outcome) {
    const o = decision.outcome
    return (
      <div
        className={clsx(
          'rounded-xl border p-4',
          o.variant === 'terminal' && 'border-slate-200 bg-slate-100/80',
          o.variant === 'success' && 'border-emerald-200 bg-emerald-50/50',
          (!o.variant || o.variant === 'default') && 'border-slate-200 bg-slate-50/80',
        )}
        data-decision-state={decision.stateId}
      >
        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Итог</p>
        <p className="mt-2 text-base font-bold leading-tight text-slate-900">{o.title}</p>
        {o.body ? <p className="mt-2 text-sm text-slate-600">{o.body}</p> : null}
        {o.why ? (
          <div className="mt-3 border-l-2 border-slate-300 pl-3">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Почему</p>
            <p className="mt-0.5 text-sm text-slate-700">{o.why}</p>
          </div>
        ) : null}
      </div>
    )
  }

  return (
    <div
      className={clsx(
        'rounded-xl border p-4',
        variant === 'blocker' && 'border-amber-200 bg-amber-50/60',
        variant === 'success' && 'border-emerald-200 bg-emerald-50/50',
        variant === 'terminal' && 'border-slate-200 bg-slate-100/80',
        variant === 'default' && 'border-brand-200 bg-brand-50/50',
      )}
      data-decision-state={decision.stateId}
    >
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Следующее действие</p>
      <p className="mt-2 text-base font-bold leading-tight text-slate-900">{decision.currentState}</p>
      {decision.why ? (
        <div className="mt-3 border-l-2 border-slate-300 pl-3">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Почему</p>
          <p className="mt-0.5 text-sm text-slate-700">{decision.why}</p>
        </div>
      ) : null}
      {decision.primaryAction ? (
        <div className="mt-4">
          <DecisionActionButton action={decision.primaryAction} size="primary" />
        </div>
      ) : null}
      {decision.afterActionHint ? (
        <p className="mt-3 text-xs text-slate-500">{decision.afterActionHint}</p>
      ) : null}
      {decision.secondaryActions?.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {decision.secondaryActions.map((action) => (
            <DecisionActionButton
              key={action.id}
              action={action}
              size={action.variant === 'danger' ? 'danger' : 'secondary'}
            />
          ))}
        </div>
      ) : null}
      {decision.contactActions?.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {decision.contactActions.map((action) => {
            const cls =
              action.variant === 'primary'
                ? 'bg-brand-700 text-white hover:bg-brand-800'
                : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
            const inner = (
              <>
                <ContactIcon kind={action.icon} variant={action.variant} />
                {action.label}
              </>
            )
            if (action.href) {
              return (
                <a
                  key={action.id}
                  href={action.href}
                  className={clsx('inline-flex items-center gap-1 rounded-lg px-3 py-2 text-xs font-medium', cls)}
                >
                  {inner}
                </a>
              )
            }
            return (
              <button
                key={action.id}
                type="button"
                onClick={action.onClick}
                className={clsx('inline-flex items-center gap-1 rounded-lg px-3 py-2 text-xs font-medium', cls)}
              >
                {inner}
              </button>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}
