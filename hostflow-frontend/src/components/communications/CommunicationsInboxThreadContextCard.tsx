import type { CommunicationThread } from '../../api/communications'
import type { ManagerOption } from '../../api/types'
import { salesInquiryPath } from '../../app/salesPaths'
import { clientDetailPath } from '../../services/platformHandoff'
import { EntityDeepLink } from '../../platform/EntityDeepLink'
import { buildEntityDeepLink } from '../../platform/entityDeepLinks'
import { useI18n } from '../../i18n'
import { uosLinkedServiceOrderId } from '../../utils/communicationThreadUnlinked'
import { threadDetailMetaLine } from '../../utils/communicationThreadMeta'

type Props = {
  thread: CommunicationThread
  managerOptions: ManagerOption[]
}

function entityLinksOf(thread: CommunicationThread) {
  return Array.isArray(thread.entity_links) ? thread.entity_links : []
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
  const candHref = cid ? buildEntityDeepLink('candidate', cid) : null

  const compId = String(thread.linked_company_id || '').trim()
  const clientLabel = compId
    ? String((thread.thread_meta || {}).linked_company_name || '').trim() || `${compId.slice(0, 8)}…`
    : '—'
  const companyHref = compId ? buildEntityDeepLink('client_account', compId) : null

  const orderId = uosLinkedServiceOrderId(thread.thread_meta)
  const orderLabel = orderId
    ? String((thread.thread_meta?.uos as Record<string, unknown> | undefined)?.linked_service_order_label || '').trim() ||
      `${orderId.slice(0, 8)}…`
    : '—'
  const orderHref = orderId ? buildEntityDeepLink('service_order', orderId) : null

  const links = entityLinksOf(thread)
  const inquiryLink = links.find((l) => {
    const et = String(l.entity_type || '').trim()
    return et === 'lead' || et === 'inquiry' || et === 'sales_inquiry'
  })
  const accountLink = links.find((l) => String(l.entity_type || '').trim() === 'client_account')
  const inquiryId = String(inquiryLink?.entity_id || '').trim()
  const accountId = String(accountLink?.entity_id || '').trim()
  const inquiryMetaLabel = String(
    (thread.thread_meta || {}).linked_inquiry_name ||
      (thread.thread_meta || {}).linked_lead_name ||
      '',
  ).trim()
  const inquiryLabel = inquiryId
    ? inquiryMetaLabel || `${inquiryId.slice(0, 8)}…`
    : '—'
  const accountLabel = accountId
    ? String((thread.thread_meta || {}).linked_client_account_name || '').trim() ||
      `${accountId.slice(0, 8)}…`
    : '—'
  // Sales inquiry ownership — entity_links may still say "lead".
  const inquiryHref = inquiryId
    ? buildEntityDeepLink(
        String(inquiryLink?.entity_type || '') === 'lead' ? 'inquiry' : String(inquiryLink?.entity_type || 'inquiry'),
        inquiryId,
      ) || salesInquiryPath(inquiryId)
    : null

  return (
    <div className="border-b border-slate-100 pb-3">
      <div className="truncate text-[11px] font-medium text-slate-800" title={metaLine}>
        {metaLine}
      </div>
      <dl className="mt-2 grid grid-cols-1 gap-x-4 gap-y-1 text-[11px] text-slate-700 sm:grid-cols-2">
        <div className="flex min-w-0 gap-1 sm:col-span-2">
          <dt className="shrink-0 text-slate-400">
            {t('app.communications_inbox_center.rail_inquiry_short', { defaultValue: 'Обращение' })}
          </dt>
          <dd className="min-w-0 truncate font-medium text-slate-800" title={inquiryLabel}>
            {inquiryHref ? (
              <EntityDeepLink
                href={inquiryHref}
                className="text-brand-700 hover:underline"
                data-testid="thread-rail-inquiry-link"
              >
                {inquiryLabel}
              </EntityDeepLink>
            ) : (
              inquiryLabel
            )}
          </dd>
        </div>
        {accountId ? (
          <div className="flex min-w-0 gap-1 sm:col-span-2">
            <dt className="shrink-0 text-slate-400">
              {t('app.communications_inbox_center.rail_client_account_short', {
                defaultValue: 'Клиентский счёт',
              })}
            </dt>
            <dd className="min-w-0 truncate font-medium text-slate-800" title={accountLabel}>
              <EntityDeepLink
                href={clientDetailPath(accountId)}
                className="text-brand-700 hover:underline"
                data-testid="thread-rail-client-account-link"
              >
                {accountLabel}
              </EntityDeepLink>
            </dd>
          </div>
        ) : null}
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
            {candHref ? (
              <EntityDeepLink href={candHref} className="text-brand-700 hover:underline" data-testid="thread-rail-candidate-link">
                {candLabel}
              </EntityDeepLink>
            ) : (
              candLabel
            )}
          </dd>
        </div>
        <div className="flex min-w-0 gap-1 sm:col-span-2">
          <dt className="shrink-0 text-slate-400">
            {t('app.communications_inbox_center.rail_client_short', { defaultValue: 'Клиент' })}
          </dt>
          <dd className="min-w-0 truncate font-medium text-slate-800" title={clientLabel}>
            {companyHref ? (
              <EntityDeepLink href={companyHref} className="text-brand-700 hover:underline">
                {clientLabel}
              </EntityDeepLink>
            ) : (
              clientLabel
            )}
          </dd>
        </div>
        <div className="flex min-w-0 gap-1 sm:col-span-2">
          <dt className="shrink-0 text-slate-400">
            {t('app.communications_inbox_center.rail_order_short', { defaultValue: 'Заказ' })}
          </dt>
          <dd className="min-w-0 truncate font-medium text-slate-800" title={orderLabel}>
            {orderHref ? (
              <EntityDeepLink href={orderHref} className="text-brand-700 hover:underline" data-testid="thread-rail-order-link">
                {orderLabel}
              </EntityDeepLink>
            ) : (
              orderLabel
            )}
          </dd>
        </div>
      </dl>
    </div>
  )
}
