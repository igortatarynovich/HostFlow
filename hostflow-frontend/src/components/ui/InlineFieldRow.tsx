import type { ReactNode } from 'react'
import { useI18n } from '../../i18n'
import { Button } from './Button'

export function InlineFieldRow({
  label,
  value,
  editing,
  canEdit = true,
  onEdit,
  onDone,
  children,
}: {
  label: string
  value: string
  editing: boolean
  canEdit?: boolean
  onEdit: () => void
  onDone: () => void
  children: ReactNode
}) {
  const { t } = useI18n()
  if (editing) {
    return (
      <div className="border-b border-slate-100 py-2">
        {children}
        <Button type="button" variant="link" size="xs" className="mt-1" onClick={onDone}>
          {t('app.candidate_card.ia.done')}
        </Button>
      </div>
    )
  }
  return (
    <div className="flex items-center gap-3 border-b border-slate-100 py-1.5">
      <div className="w-36 shrink-0 text-sm text-slate-500">{label}</div>
      <div className="min-w-0 flex-1 truncate text-sm font-medium text-slate-900">{value || '—'}</div>
      {canEdit ? (
        <Button type="button" variant="link" size="xs" onClick={onEdit}>
          {t('common.actions.edit')}
        </Button>
      ) : null}
    </div>
  )
}
