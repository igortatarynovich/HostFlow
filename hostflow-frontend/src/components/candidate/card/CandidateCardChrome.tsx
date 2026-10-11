import { useState, type ReactNode } from 'react'
import clsx from 'clsx'
import { useI18n } from '../../../i18n'

export type CandidateCardTabId = 'personal' | 'profile' | 'documents' | 'legalization' | 'services'

const TAB_IDS: CandidateCardTabId[] = ['personal', 'profile', 'documents', 'legalization', 'services']

export function CandidateCardTabs({
  value,
  onChange,
}: {
  value: CandidateCardTabId
  onChange: (id: CandidateCardTabId) => void
}) {
  const { t } = useI18n()
  return (
    <div className="flex gap-1 overflow-x-auto border-b border-slate-200" role="tablist">
      {TAB_IDS.map((id) => {
        const selected = value === id
        return (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={selected}
            className={clsx(
              '-mb-px shrink-0 border-b-2 px-3 py-2 text-sm font-semibold',
              selected ? 'border-brand-600 text-slate-900' : 'border-transparent text-slate-500 hover:text-slate-800',
            )}
            onClick={() => onChange(id)}
          >
            {t(`app.candidate_card.ia.tabs.${id}`)}
          </button>
        )
      })}
    </div>
  )
}

export function CardAccordion({
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

export function ReadRows({ rows }: { rows: Array<{ label: string; value: string }> }) {
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

export function joinParts(parts: Array<string | null | undefined | false>): string {
  return parts.map((part) => (typeof part === 'string' ? part.trim() : '')).filter(Boolean).join(' · ')
}
