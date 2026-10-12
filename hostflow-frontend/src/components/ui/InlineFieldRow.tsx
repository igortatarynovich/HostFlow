import type { ReactNode } from 'react'
import clsx from 'clsx'
import { IconPencil } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { Button } from './Button'

export function InlineFieldRow({
  label,
  value,
  editing,
  canEdit = true,
  onEdit,
  onDone,
  wide = false,
  column,
  row,
  variant = 'inline',
  emptyLabel,
  className,
  children,
}: {
  label: string
  value: string
  editing: boolean
  canEdit?: boolean
  onEdit: () => void
  onDone: () => void
  /** Address and other grouped editors need the cell width. Short values stay capped. */
  wide?: boolean
  /** Place the row in a parent two-column workspace grid. */
  column?: 1 | 2
  /** Explicit grid row so paired columns line up when parents use display:contents. */
  row?: 1 | 2 | 3 | 4 | 5 | 6
  /** `summary` stacks the label over the value, for address-like objects. */
  variant?: 'inline' | 'summary'
  emptyLabel?: string
  className?: string
  children: ReactNode
}) {
  const { t } = useI18n()
  const columnClass = column === 1 ? 'md:col-start-1' : column === 2 ? 'md:col-start-2' : undefined
  const rowClass = row === 1 ? 'md:row-start-1'
    : row === 2 ? 'md:row-start-2'
    : row === 3 ? 'md:row-start-3'
    : row === 4 ? 'md:row-start-4'
    : row === 5 ? 'md:row-start-5'
    : row === 6 ? 'md:row-start-6'
    : undefined
  const spanClass = wide ? 'md:col-span-2' : undefined
  const blank = !value.trim() || value.trim() === '—'

  if (editing) {
    return (
      <div className={clsx('workspace-editor border-b border-slate-100 py-2', spanClass, columnClass, rowClass, className)}>
        <div className={wide || variant === 'summary' ? undefined : 'max-w-md'}>{children}</div>
        <Button type="button" variant="secondary" size="compact" className="mt-1.5" onClick={onDone}>
          {t('app.candidate_card.ia.done')}
        </Button>
      </div>
    )
  }

  const editButton = canEdit ? (
    blank && variant === 'summary' ? (
      <Button type="button" variant="secondary" size="compact" onClick={onEdit}>
        {t('common.actions.add')}
      </Button>
    ) : (
      <Button type="button" variant="icon" size="compact" onClick={onEdit} aria-label={t('common.actions.edit')}>
        <IconPencil size={14} />
      </Button>
    )
  ) : null

  if (variant === 'summary') {
    return (
      <div className={clsx('rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-2', spanClass, columnClass, rowClass, className)}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="text-xs text-slate-500">{label}</div>
            <div className={clsx('mt-0.5 text-sm font-medium', blank ? 'text-slate-400' : 'text-slate-900')}>
              {blank ? emptyLabel || '—' : value}
            </div>
          </div>
          {editButton}
        </div>
      </div>
    )
  }

  return (
    <div className={clsx('flex min-w-0 items-center gap-2 border-b border-slate-100 py-1', spanClass, columnClass, rowClass, className)}>
      <div className="w-40 shrink-0 text-xs leading-tight text-slate-500">{label}</div>
      <div title={blank ? undefined : value} className="min-w-0 flex-1 truncate text-sm font-medium text-slate-900">
        {blank ? '—' : value}
      </div>
      {editButton}
    </div>
  )
}
