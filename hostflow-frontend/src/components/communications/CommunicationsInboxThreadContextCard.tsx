import type { CommunicationThread } from '../../api/communications'
import type { ManagerOption } from '../../api/types'
import { useI18n } from '../../i18n'
import { uosLinkedServiceOrderId } from '../../utils/communicationThreadUnlinked'
import { threadDetailMetaLine } from '../../utils/communicationThreadMeta'

type Props = {
  thread: CommunicationThread
  managerOptions: ManagerOption[]
}

/** Compact thread summary for the Messages right rail — no instructional copy. */
export default function CommunicationsInboxThreadContextCard({ thread, managerOptions }: Props) {
  const { t } = useI18n()
  const metaLine = threadDetailMetaLine(thread, t)
  const assigneeLabel = thread.assignee_id
    ? managerOptions.find((m) => String(m.id) === String(thread.assignee_id))?.label ||
      String(thread.assignee_id).slice(0, 8)
    : '—'

  const cid = String(thread.linked_candidate_id || '').trim()
  const candLabel = cid
    ? String((thread.thread_meta || {}).linked_candidate_name || '').trim() || `${cid.slice(0, 8)}…`
    : '—'

  const compId = String(thread.linked_company_id || '').trim()
  const clientLabel = compId
    ? String((thread.thread_meta || {}).linked_company_name || '').trim() || `${compId.slice(0, 8)}…`
    : '—'

  const orderId = uosLinkedServiceOrderId(thread.thread_meta)
  const orderLabel = orderId
    ? String((thread.thread_meta?.uos as Record<string, unknown> | undefined)?.linked_service_order_label || '').trim() ||
      `${orderId.slice(0, 8)}…`
    : '—'

  return (
    <div className="border-b border-slate-100 pb-3">
      <div className="truncate text-[11px] font-medium text-slate-800" title={metaLine}>
        {metaLine}
      </div>
      <dl className="mt-2 grid grid-cols-1 gap-x-4 gap-y-1 text-[11px] text-slate-700 sm:grid-cols-2">
        <div className="flex min-w-0 gap-1">
          <dt className="shrink-0 text-slate-400">
            {t('app.communications_messages.header.manager_badge', { defaultValue: 'Менеджер' })}
          </dt>
          <dd className="min-w-0 truncate font-medium text-slate-800" title={assigneeLabel}>
            {assigneeLabel}
          </dd>
        </div>
        <div className="flex min-w-0 gap-1">
          <dt className="shrink-0 text-slate-400">
            {t('app.communications_messages.header.candidate_badge', { defaultValue: 'Кандидат' })}
          </dt>
          <dd className="min-w-0 truncate font-medium text-slate-800" title={candLabel}>
            {candLabel}
          </dd>
        </div>
        <div className="flex min-w-0 gap-1 sm:col-span-2">
          <dt className="shrink-0 text-slate-400">
            {t('app.communications_inbox_center.rail_client_short', { defaultValue: 'Клиент' })}
          </dt>
          <dd className="min-w-0 truncate font-medium text-slate-800" title={clientLabel}>
            {clientLabel}
          </dd>
        </div>
        <div className="flex min-w-0 gap-1 sm:col-span-2">
          <dt className="shrink-0 text-slate-400">
            {t('app.communications_inbox_center.rail_order_short', { defaultValue: 'Заказ' })}
          </dt>
          <dd className="min-w-0 truncate font-medium text-slate-800" title={orderLabel}>
            {orderLabel}
          </dd>
        </div>
      </dl>
    </div>
  )
}
