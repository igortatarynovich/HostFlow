import type { ReactNode } from 'react'
import clsx from 'clsx'
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
  className?: string
  children: ReactNode
}) {
  const { t } = useI18n()
  if (editing) {
    return (
      <div className={clsx('border-b border-slate-100 py-2', wide && 'md:col-span-2', className)}>
        <div className={wide ? undefined : 'max-w-md'}>{children}</div>
        <Button type="button" variant="link" size="xs" className="mt-1" onClick={onDone}>
          {t('app.candidate_card.ia.done')}
        </Button>
      </div>
    )
  }
  return (
    <div className={clsx('flex min-w-0 items-center gap-3 border-b border-slate-100 py-1.5', className)}>
      <div className="w-32 shrink-0 text-sm text-slate-500">{label}</div>
      <div title={value || undefined} className={clsx('min-w-0 truncate text-sm font-medium text-slate-900', wide ? 'flex-1' : 'max-w-md flex-1')}>{value || '—'}</div>
      {canEdit ? (
        <Button type="button" variant="link" size="xs" onClick={onEdit}>
          {t('common.actions.edit')}
        </Button>
      ) : null}
    </div>
  )
}
