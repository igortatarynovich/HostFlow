import clsx from 'clsx'
import type { ReminderWorkQueueItem } from '../../api/types'
import { useI18n } from '../../i18n'
import { SEVERITY_META } from '../../constants/workforceOperationalTaxonomy'
import {
  DOCUMENT_ACTION_LABEL,
  formatDocumentActionDueDate,
  humanizeDocumentCode,
  humanizePackCode,
  sortReminderWorkQueue,
} from '../../utils/documentActionsPanel'

type Props = {
  items?: ReminderWorkQueueItem[] | null
  loading?: boolean
  error?: string | null
}

function severityTone(severity: string): string {
  const key = severity as keyof typeof SEVERITY_META
  return SEVERITY_META[key]?.tone || SEVERITY_META.low.tone
}

function ActionRow({ item }: { item: ReminderWorkQueueItem }) {
  const { t } = useI18n()
  const actionLabel =
    t(`app.hr.document_actions.action.${item.action}`, {
      defaultValue: DOCUMENT_ACTION_LABEL[item.action] || item.action,
    })

  return (
    <li className="rounded-lg border border-slate-200 bg-white px-3 py-3 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold text-slate-900">{item.title}</div>
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-600">
            <span>
              {t('app.hr.document_actions.document', { defaultValue: 'Document' })}:{' '}
              <span className="font-medium text-slate-800">{humanizeDocumentCode(item.document_code)}</span>
            </span>
            <span>
              {t('app.hr.document_actions.pack', { defaultValue: 'Pack' })}:{' '}
              <span className="font-medium text-slate-800">{humanizePackCode(item.source_pack)}</span>
            </span>
            <span>
              {t('app.hr.document_actions.due', { defaultValue: 'Due' })}:{' '}
              <span className="font-medium text-slate-800">{formatDocumentActionDueDate(item.due_date)}</span>
            </span>
          </div>
        </div>
        <span
          className={clsx(
            'shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
            severityTone(item.severity),
          )}
        >
          {item.severity}
        </span>
      </div>
      <div className="mt-3">
        <span className="inline-flex rounded border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-800">
          {actionLabel}
        </span>
      </div>
    </li>
  )
}

export function DocumentActionsPanel({ items, loading = false, error = null }: Props) {
  const { t } = useI18n()

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
  }

  if (error) {
    return <p className="text-sm text-red-600">{error}</p>
  }

  const sorted = sortReminderWorkQueue(items || [])
  if (!sorted.length) {
    return (
      <p className="text-sm text-slate-500">
        {t('app.hr.document_actions.empty', { defaultValue: 'No document actions' })}
      </p>
    )
  }

  return (
    <ul className="space-y-2">
      {sorted.map((item) => (
        <ActionRow key={item.task_key} item={item} />
      ))}
    </ul>
  )
}
