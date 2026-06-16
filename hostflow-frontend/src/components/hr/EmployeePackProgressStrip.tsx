import clsx from 'clsx'
import type { PackStripItem } from '../../utils/buildEmployeeReadinessSummary'
import { useI18n } from '../../i18n'

const TONE_CLASS: Record<PackStripItem['tone'], string> = {
  emerald: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  amber: 'border-amber-200 bg-amber-50 text-amber-950',
  rose: 'border-rose-200 bg-rose-50 text-rose-950',
  slate: 'border-slate-200 bg-slate-50 text-slate-700',
}

type Props = {
  items: PackStripItem[]
  loading?: boolean
}

export function EmployeePackProgressStrip({ items, loading = false }: Props) {
  const { t } = useI18n()

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
  }

  if (!items.length) return null

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <div
          key={item.code}
          className={clsx(
            'inline-flex min-w-0 items-center gap-2 rounded-lg border px-3 py-2 text-sm shadow-sm',
            TONE_CLASS[item.tone],
          )}
        >
          <span className="font-medium truncate">{item.label}</span>
          <span className="shrink-0 text-xs font-semibold uppercase tracking-wide opacity-80">
            {item.statusLabel}
          </span>
        </div>
      ))}
    </div>
  )
}
