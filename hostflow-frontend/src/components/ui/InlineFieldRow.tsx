import type { ReactNode } from 'react'
import clsx from 'clsx'
import { IconCheck, IconPencil, IconX } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { Button } from './Button'

function FieldEditActions({
  onSave,
  onCancel,
  saveLabel,
  cancelLabel,
}: {
  onSave: () => void
  onCancel?: () => void
  saveLabel: string
  cancelLabel: string
}) {
  return (
    <>
      <Button type="button" variant="icon" size="compact" onClick={onSave} aria-label={saveLabel}>
        <IconCheck size={14} />
      </Button>
      {onCancel ? (
        <Button type="button" variant="icon" size="compact" onClick={onCancel} aria-label={cancelLabel}>
          <IconX size={14} />
        </Button>
      ) : null}
    </>
  )
}

export function InlineFieldRow({
  label,
  value,
  editing,
  canEdit = true,
  onEdit,
  onDone,
  onCancel,
  wide = false,
  contentEditor = false,
  variant = 'inline',
  emptyLabel,
  className,
  testId,
  children,
}: {
  label: string
  value: string
  editing: boolean
  canEdit?: boolean
  onEdit: () => void
  onDone: () => void
  /** Restores the value from before this row was opened. Defaults to save for existing callers. */
  onCancel?: () => void
  /** Address and other grouped editors need the full grid width. */
  wide?: boolean
  /** Chips and segmented choices size to their content. Text and select stay a fixed editor width. */
  contentEditor?: boolean
  /** `summary` stacks the label over the value, for address-like objects. */
  variant?: 'inline' | 'summary'
  emptyLabel?: string
  className?: string
  testId?: string
  children: ReactNode
}) {
  const { t } = useI18n()
  const spanClass = wide ? 'md:col-span-2' : undefined
  const blank = !value.trim() || value.trim() === '—'
  const actions = (
    <FieldEditActions
      onSave={onDone}
      onCancel={onCancel}
      saveLabel={t('common.actions.save')}
      cancelLabel={t('common.actions.cancel')}
    />
  )

  if (editing && (wide || variant === 'summary')) {
    return (
      <div className={clsx('workspace-editor border-b border-slate-100 py-2 md:col-span-2', className)} data-testid={testId}>
        <div className="mb-2 flex items-center gap-2">
          <div className="w-40 shrink-0 text-xs leading-tight text-slate-500">{label}</div>
          {actions}
        </div>
        {children}
      </div>
    )
  }

  if (editing) {
    return (
      <div className={clsx('workspace-editor flex min-w-0 max-w-full items-center gap-2 border-b border-slate-100 py-1', spanClass, className)} data-testid={testId}>
        <div className="w-40 shrink-0 text-xs leading-tight text-slate-500">{label}</div>
        <div className={clsx('min-w-0', contentEditor ? 'max-w-full' : 'w-52')}>{children}</div>
        {actions}
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
      <div className={clsx('inline-flex max-w-full items-start gap-2', spanClass, className)} data-testid={testId}>
        <div className="min-w-0">
          <div className="text-xs text-slate-500">{label}</div>
          <div className={clsx('mt-0.5 text-sm font-medium', blank ? 'text-slate-400' : 'text-slate-900')}>
            {blank ? emptyLabel || '—' : value}
          </div>
        </div>
        {editButton}
      </div>
    )
  }

  return (
    <div className={clsx('flex min-w-0 max-w-full items-center gap-2 border-b border-slate-100 py-1', spanClass, className)} data-testid={testId}>
      <div className="w-40 shrink-0 text-xs leading-tight text-slate-500">{label}</div>
      <div title={blank ? undefined : value} className={clsx('min-w-0 truncate text-sm font-medium', blank ? 'text-slate-400' : 'text-slate-900')}>
        {blank ? '—' : value}
      </div>
      {editButton}
    </div>
  )
}
