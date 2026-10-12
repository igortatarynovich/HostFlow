import { useState, type ReactNode } from 'react'
import clsx from 'clsx'
import { useI18n } from '../../i18n'

/**
 * Operator entity record.
 * Header, then an optional banner, then navigation and body beside a 17.5rem rail.
 * A domain surface fills the slots. It does not choose the geometry.
 */
export function EntityRecordSurface({
  header,
  banner,
  rail,
  children,
}: {
  header?: ReactNode
  banner?: ReactNode
  rail?: ReactNode
  children: ReactNode
}) {
  return (
    <div className="min-w-0 space-y-3">
      {header}
      {banner}
      <div className="grid min-w-0 items-start gap-3 lg:grid-cols-[minmax(0,1fr)_17.5rem]">
        <aside className="flex min-h-0 min-w-0 flex-col gap-2 max-lg:order-last lg:sticky lg:top-3 lg:col-start-2 lg:row-start-1 lg:max-h-[calc(100dvh-4.5rem)] lg:overflow-y-auto lg:overscroll-contain">
          {rail}
        </aside>
        <div className="min-w-0 space-y-3 lg:col-start-1 lg:row-start-1">{children}</div>
      </div>
    </div>
  )
}

export function EntityRecordTabs<T extends string>({
  value,
  onChange,
  tabs,
}: {
  value: T
  onChange: (id: T) => void
  tabs: Array<{ id: T; label: string }>
}) {
  return (
    <div className="flex gap-1 overflow-x-auto border-b border-slate-200" role="tablist">
      {tabs.map((item) => {
        const selected = value === item.id
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={selected}
            className={clsx(
              '-mb-px shrink-0 border-b-2 px-3 py-2 text-sm font-semibold',
              selected ? 'border-brand-600 text-slate-900' : 'border-transparent text-slate-500 hover:text-slate-800',
            )}
            onClick={() => onChange(item.id)}
          >
            {item.label}
          </button>
        )
      })}
    </div>
  )
}

export function EntityRecordSection({
  title,
  summary,
  defaultOpen = false,
  editing = false,
  onEdit,
  onDone,
  children,
}: {
  title: string
  summary?: string | null
  defaultOpen?: boolean
  editing?: boolean
  onEdit?: () => void
  onDone?: () => void
  children: ReactNode
}) {
  const { t } = useI18n()
  const [open, setOpen] = useState(defaultOpen)
  const expanded = editing || open

  return (
    <section className="rounded-xl border border-slate-200 bg-white">
      <div className="flex items-start gap-3 px-3 py-2.5">
        <button
          type="button"
          className="min-w-0 flex-1 text-left"
          aria-expanded={expanded}
          onClick={() => {
            if (!editing) setOpen((value) => !value)
          }}
        >
          <span className="text-sm font-semibold text-slate-900">{title}</span>
          {!expanded && summary ? (
            <span className="mt-0.5 block truncate text-xs text-slate-500">{summary}</span>
          ) : null}
        </button>
        {onEdit ? (
          <button
            type="button"
            className="shrink-0 text-xs font-medium text-brand-700 hover:underline"
            onClick={editing ? onDone : onEdit}
          >
            {editing ? t('app.candidate_card.ia.done') : t('common.actions.edit')}
          </button>
        ) : null}
        <button
          type="button"
          className="shrink-0 text-xs text-slate-400"
          aria-label={expanded ? t('common.actions.collapse') : t('common.actions.expand')}
          onClick={() => {
            if (!editing) setOpen((value) => !value)
          }}
        >
          {expanded ? '−' : '+'}
        </button>
      </div>
      {expanded ? <div className="border-t border-slate-100 px-3 py-3">{children}</div> : null}
    </section>
  )
}

export function EntityRecordRows({ rows }: { rows: Array<{ label: string; value: string }> }) {
  return (
    <dl>
      {rows.map((row) => (
        <div key={row.label} className="flex items-baseline justify-between gap-6 py-1">
          <dt className="text-sm text-slate-500">{row.label}</dt>
          <dd className="text-right text-sm font-medium text-slate-900">{row.value}</dd>
        </div>
      ))}
    </dl>
  )
}

export function joinRecordParts(parts: Array<string | null | undefined | false>): string {
  return parts.map((part) => (typeof part === 'string' ? part.trim() : '')).filter(Boolean).join(' · ')
}

/** Shared chrome for a widget mounted in the entity record rail. */
export function RailWidget({
  title,
  actions,
  children,
}: {
  title: ReactNode
  actions?: ReactNode
  children?: ReactNode
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0 text-xs font-semibold text-slate-800">{title}</div>
        {actions}
      </div>
      {children}
    </section>
  )
}
