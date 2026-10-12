import { useState, type ReactNode } from 'react'
import { useI18n } from '../../i18n'
import { WorkspaceSection } from '../../components/ui/WorkspaceSection'
import { WorkspaceTabs } from '../../components/ui/WorkspaceTabs'

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
      <div className="grid min-w-0 items-start gap-3 lg:grid-cols-[minmax(0,1fr)_20rem]">
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
  ariaLabel,
}: {
  value: T
  onChange: (id: T) => void
  tabs: Array<{ id: T; label: string; badge?: ReactNode }>
  ariaLabel?: string
}) {
  return (
    <WorkspaceTabs
      ariaLabel={ariaLabel}
      value={value}
      onChange={(id) => onChange(id as T)}
      items={tabs.map((item) => ({ id: item.id, label: item.label, badge: item.badge }))}
    />
  )
}

export function EntityRecordSection({
  title,
  summary,
  description,
  icon,
  defaultOpen = false,
  editing = false,
  onEdit,
  onDone,
  children,
}: {
  title: string
  summary?: string | null
  description?: string | null
  icon?: ReactNode
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
    <WorkspaceSection
      title={title}
      description={expanded ? description || null : summary || description}
      icon={icon}
      collapsible
      open={expanded}
      onOpenChange={(next) => {
        if (!editing) setOpen(next)
      }}
      action={
        onEdit ? (
          <button
            type="button"
            className="shrink-0 text-xs font-medium text-brand-700 hover:underline"
            onClick={editing ? onDone : onEdit}
          >
            {editing ? t('app.candidate_card.ia.done') : t('common.actions.edit')}
          </button>
        ) : null
      }
    >
      {children}
    </WorkspaceSection>
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
