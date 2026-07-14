import { Link } from 'react-router-dom'
import clsx from 'clsx'
import { IconAlertTriangle, IconCheck, IconHourglass } from '@tabler/icons-react'

import type {
  ClientPreparationCheckItem,
  ClientPreparationChecklistDTO,
  ClientPreparationItemStatus,
} from '../../api/clientPreparation'
import { useI18n } from '../../i18n'

interface ClientPreparationChecklistPanelProps {
  data: ClientPreparationChecklistDTO | null
  loading?: boolean
  error?: unknown
}

function statusTone(status: ClientPreparationItemStatus): string {
  switch (status) {
    case 'done':
      return 'bg-emerald-500'
    case 'warning':
      return 'bg-amber-400'
    case 'missing':
    default:
      return 'bg-rose-500'
  }
}

function statusIcon(status: ClientPreparationItemStatus) {
  switch (status) {
    case 'done':
      return <IconCheck size={14} className="text-emerald-600" />
    case 'warning':
      return <IconAlertTriangle size={14} className="text-amber-600" />
    case 'missing':
    default:
      return <IconHourglass size={14} className="text-rose-600" />
  }
}

function ChecklistRow({ item }: { item: ClientPreparationCheckItem }) {
  const { t } = useI18n()
  if (!item.visible) return null

  const title = item.title_key
    ? t(item.title_key, { defaultValue: item.title })
    : item.title
  const hint = item.hint_key
    ? t(item.hint_key, { defaultValue: item.hint ?? '' })
    : item.hint ?? ''

  const textClass =
    item.status === 'done'
      ? 'text-slate-700'
      : item.status === 'warning'
        ? 'text-amber-800'
        : 'text-rose-700'

  const content = (
    <div className="flex min-w-0 flex-1 items-start gap-2">
      <span
        className={clsx('mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full', statusTone(item.status))}
        aria-hidden
      />
      <div className="min-w-0">
        <div className={clsx('flex items-center gap-1.5 text-sm font-medium', textClass)}>
          {statusIcon(item.status)}
          <span className="truncate">{title}</span>
          {item.soft ? (
            <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700">
              {t('app.client_preparation.soft_badge', { defaultValue: 'мягкий чек' })}
            </span>
          ) : null}
        </div>
        {hint ? <p className="mt-0.5 text-xs text-slate-500">{hint}</p> : null}
      </div>
    </div>
  )

  if (item.href && item.status !== 'done') {
    return (
      <li>
        <Link
          to={item.href}
          className="block rounded-xl border border-transparent px-2 py-2 transition hover:border-slate-200 hover:bg-slate-50"
        >
          {content}
        </Link>
      </li>
    )
  }

  return (
    <li className="rounded-xl px-2 py-2">
      {content}
    </li>
  )
}

export function ClientPreparationChecklistPanel({
  data,
  loading = false,
  error,
}: ClientPreparationChecklistPanelProps) {
  const { t } = useI18n()

  if (loading && !data) {
    return (
      <p className="text-sm text-slate-500" aria-busy="true">
        {t('app.client_preparation.loading', { defaultValue: 'Проверяем готовность…' })}
      </p>
    )
  }

  if (error && !data) {
    return (
      <p className="text-sm text-rose-600">
        {t('app.client_preparation.error', { defaultValue: 'Не удалось загрузить чек-лист подготовки.' })}
      </p>
    )
  }

  if (!data || data.items.length === 0) {
    return null
  }

  const visibleItems = data.items.filter((item) => item.visible)
  const doneCount = visibleItems.filter((item) => item.status === 'done').length
  const hardItems = visibleItems.filter((item) => !item.soft)
  const hardDone = hardItems.filter((item) => item.status === 'done').length

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.client_preparation.title', { defaultValue: 'Подготовка клиента' })}
        </p>
        <span
          className={clsx(
            'rounded-full px-2 py-0.5 text-[11px] font-semibold',
            data.is_prepared
              ? 'bg-emerald-50 text-emerald-800'
              : 'bg-slate-100 text-slate-600',
          )}
        >
          {data.is_prepared
            ? t('app.client_preparation.prepared', { defaultValue: 'Готов к работе' })
            : t('app.client_preparation.progress', {
                defaultValue: '{done}/{total} обязательных',
                values: { done: String(hardDone), total: String(hardItems.length) },
              })}
        </span>
      </div>
      <p className="mt-1 text-xs text-slate-500">
        {t('app.client_preparation.subtitle', {
          defaultValue: 'Что уже готово, что мешает и что желательно, но не блокирует.',
        })}
      </p>
      <ul className="mt-3 space-y-1">
        {visibleItems.map((item) => (
          <ChecklistRow key={item.key} item={item} />
        ))}
      </ul>
      {doneCount === visibleItems.length ? (
        <p className="mt-2 text-xs text-emerald-700">
          {t('app.client_preparation.all_done_hint', {
            defaultValue: 'Все пункты закрыты — можно сосредоточиться на заказах и счетах.',
          })}
        </p>
      ) : null}
    </div>
  )
}

export default ClientPreparationChecklistPanel
