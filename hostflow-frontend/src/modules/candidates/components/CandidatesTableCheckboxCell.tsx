import clsx from 'clsx'
import type { AugmentedCandidate } from '../types'

type CandidatesTableCheckboxCellProps = {
  c: AugmentedCandidate
  isFocused: boolean
  checked: Record<string, boolean>
  canManage: boolean
  toggle: (id: string) => void
  t: (key: string, opts?: any) => string
}

export function CandidatesTableCheckboxCell({
  c,
  isFocused,
  checked,
  canManage,
  toggle,
  t,
}: CandidatesTableCheckboxCellProps) {
  const isChecked = !!checked[c.id]
  const masked = c.masked === true

  const maskedName = masked
    ? c.short_id
      ? t('app.candidates.table.masked_label_short_id', {
          defaultValue: 'Кандидат {short_id}',
          values: { short_id: c.short_id },
        })
      : t('app.candidates.table.masked_label', {
          defaultValue: 'Кандидат #{id}',
          values: { id: (c.id ?? '').slice(0, 8) },
        })
    : `${c.first_name ?? ''} ${c.last_name ?? ''}`.trim()

  return (
    <td
      className={clsx(
        'px-4 py-2.5 border-r border-slate-200 align-middle',
        isFocused ? 'bg-brand-100' : 'bg-white',
      )}
      data-candidate-id={c.id}
      style={{ width: '56px', minWidth: '56px', maxWidth: '56px' }}
    >
      <div className="flex items-center justify-center">
        <input
          type="checkbox"
          checked={isChecked}
          disabled={!canManage}
          onChange={() => toggle(c.id)}
          onClick={(e) => e.stopPropagation()}
          className="cursor-pointer w-4 h-4"
          title={isChecked ? (t('app.candidates.table.deselect') || 'Снять выделение') : (t('app.candidates.table.select') || 'Выделить')}
          aria-label={
            t('app.candidates.table.select_candidate', {
              values: {
                name: maskedName,
              },
            }) || 'Select candidate'
          }
        />
      </div>
    </td>
  )
}

