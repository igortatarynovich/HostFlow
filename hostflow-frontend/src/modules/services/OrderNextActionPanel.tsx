import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import type { AdditionalServiceItem, AdditionalServiceOrder, ServiceOrderStatus } from '../../api/types/service'
import { createInvoiceFromServiceOrder, createPayment, getCompany } from '../../api/client'
import { useToast } from '../../components/Toast'
import { useI18n } from '../../i18n'
import { executePlatformHandoff } from '../../services/platformHandoff'
import type { PlatformHandoff } from '../../api/platformCompletion'
import { invoiceOutstandingAmount, resolveServiceOrderNextAction } from './utils'
import { itemExecutionMode, itemHandoffAction, orderBeneficiaryKind } from './serviceOrderBeneficiary'

type InvoiceSummaryLike = {
  invoice_id?: string
  invoice_number?: string
  status?: string
  total_amount?: number
  paid_amount?: number
  due_date?: string
} | null

type OrderNextActionPanelProps = {
  order: AdditionalServiceOrder
  invoiceSummary: InvoiceSummaryLike
  canManage: boolean
  /** Updates order status and reloads order/list/summary. */
  onStatusUpdate: (orderId: string, status: ServiceOrderStatus) => void
  /** Reloads the linked invoice summary. */
  onInvoiceChanged: () => void
}

type HandoffSpec = {
  i18nKey: string
  defaultValue: string
  /** Beneficiary kinds this executor can be launched for. */
  requires: 'client' | 'any'
}

const HANDOFF_SPECS: Record<string, HandoffSpec> = {
  'recruitment.create_search': {
    i18nKey: 'app.services.orders.handoff.create_search',
    defaultValue: 'Создать подбор',
    requires: 'client',
  },
  'marketing.create_project': {
    i18nKey: 'app.services.orders.handoff.create_marketing',
    defaultValue: 'Создать marketing project',
    requires: 'client',
  },
}

export function OrderNextActionPanel({
  order,
  invoiceSummary,
  canManage,
  onStatusUpdate,
  onInvoiceChanged,
}: OrderNextActionPanelProps) {
  const { t } = useI18n()
  const navigate = useNavigate()
  const { notify } = useToast()
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const nextAction = useMemo(
    () => resolveServiceOrderNextAction(order, invoiceSummary),
    [order, invoiceSummary],
  )

  const outstanding = invoiceSummary?.invoice_id
    ? invoiceOutstandingAmount(invoiceSummary.total_amount, invoiceSummary.paid_amount)
    : 0

  const handoffItems = useMemo(
    () =>
      (order.items || []).filter(
        (item) => item.status !== 'cancelled' && itemExecutionMode(item) === 'handoff',
      ),
    [order.items],
  )

  const beneficiaryKind = orderBeneficiaryKind(order)
  const clientId = String(order.company_id || order.client_id || '').trim()

  async function runConfirm() {
    onStatusUpdate(order.id, 'confirmed' as ServiceOrderStatus)
  }

  async function runComplete() {
    onStatusUpdate(order.id, 'completed' as ServiceOrderStatus)
  }

  async function runCreateInvoice() {
    setError(null)
    setBusy('invoice')
    try {
      await createInvoiceFromServiceOrder(order.id)
      onInvoiceChanged()
      notify({
        title: t('app.services.orders.action_cta.invoice_created', { defaultValue: 'Счёт создан' }),
        variant: 'success',
      })
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to create invoice')
    } finally {
      setBusy(null)
    }
  }

  async function runCollectPayment() {
    if (!invoiceSummary?.invoice_id || outstanding <= 0) return
    setError(null)
    setBusy('payment')
    try {
      const today = new Date().toISOString().slice(0, 10)
      await createPayment(String(invoiceSummary.invoice_id), {
        amount: outstanding,
        payment_date: today,
        method: 'bank_transfer',
      })
      onInvoiceChanged()
      notify({
        title: t('app.services.orders.action_cta.payment_recorded', { defaultValue: 'Оплата внесена' }),
        variant: 'success',
      })
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to record payment')
    } finally {
      setBusy(null)
    }
  }

  async function runHandoff(item: AdditionalServiceItem, action: string) {
    setError(null)
    setBusy(`handoff:${item.id}`)
    try {
      let clientName = ''
      if (clientId) {
        try {
          const company = await getCompany(clientId)
          clientName = String((company as { name?: string })?.name || '').trim()
        } catch {
          // Name is a label only; fall through to a generic default.
        }
      }
      const handoff: PlatformHandoff = {
        action,
        label: handoffLabel(action),
        context: {
          service_order_id: order.id,
          service_item_id: item.id,
          service_code: item.service?.code || item.service_code || null,
          client_id: clientId || null,
          client_name: clientName || null,
          candidate_id: order.candidate_id || null,
          employee_id: order.employee_id || null,
        },
      }
      const result = await executePlatformHandoff(handoff)
      if (result?.pending) {
        notify({
          title: t('app.services.orders.handoff.pending', {
            defaultValue: 'Исполнитель появится позже',
          }),
          variant: 'info',
        })
        return
      }
      notify({ title: handoffLabel(action), variant: 'success' })
      if (result?.navigateTo) navigate(result.navigateTo)
    } catch (e: any) {
      const msg = e?.message === 'client_id_required'
        ? t('app.services.orders.handoff.client_required', {
            defaultValue: 'Handoff-подбор доступен только для клиентских заказов',
          })
        : e?.response?.data?.detail || e?.message || 'Handoff failed'
      setError(msg)
    } finally {
      setBusy(null)
    }
  }

  function handoffLabel(action: string): string {
    const spec = HANDOFF_SPECS[action]
    if (spec) return t(spec.i18nKey, { defaultValue: spec.defaultValue })
    return action
  }

  const nextStepText = describeNextStep(nextAction, t)

  return (
    <section className="rounded-xl border border-brand-200 bg-brand-50/60 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="text-xs font-semibold uppercase tracking-wide text-brand-700">
            {t('app.services.orders.action_cta.title', { defaultValue: 'Следующее действие' })}
          </div>
          <div className="mt-0.5 text-sm font-medium text-slate-900">{nextStepText}</div>
        </div>
        {canManage ? <NextActionButton
          nextAction={nextAction}
          busy={busy}
          hasInvoice={Boolean(invoiceSummary?.invoice_id)}
          outstanding={outstanding}
          t={t}
          onConfirm={runConfirm}
          onComplete={runComplete}
          onCreateInvoice={runCreateInvoice}
          onCollectPayment={runCollectPayment}
        /> : null}
      </div>

      {canManage && handoffItems.length > 0 ? (
        <div className="mt-4 border-t border-brand-100 pt-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-violet-700">
            {t('app.services.orders.handoff.title', { defaultValue: 'Запуск исполнителей' })}
          </div>
          <p className="mt-0.5 text-xs text-slate-600">
            {t('app.services.orders.handoff.hint', {
              defaultValue: 'Платформа запускает исполнителей по строкам заказа с execution=handoff.',
            })}
          </p>
          <div className="mt-2 space-y-2">
            {handoffItems.map((item) => {
              const action = itemHandoffAction(item)
              const spec = action ? HANDOFF_SPECS[action] : undefined
              const needsClient = spec?.requires === 'client'
              const blockedNoClient = needsClient && !clientId
              return (
                <div
                  key={item.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-violet-200 bg-white px-3 py-2"
                >
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-slate-900">
                      {item.service?.name || item.service_id}
                    </div>
                    <div className="text-xs text-slate-500">{action || '—'}</div>
                  </div>
                  <button
                    type="button"
                    className="rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-50"
                    disabled={!action || busy === `handoff:${item.id}` || blockedNoClient}
                    title={
                      blockedNoClient
                        ? t('app.services.orders.handoff.client_required', {
                            defaultValue: 'Handoff-подбор доступен только для клиентских заказов',
                          })
                        : undefined
                    }
                    onClick={() => action && void runHandoff(item, action)}
                  >
                    {busy === `handoff:${item.id}`
                      ? t('app.services.orders.handoff.launching', { defaultValue: 'Запускаем…' })
                      : action
                        ? handoffLabel(action)
                        : t('app.services.orders.handoff.not_configured', { defaultValue: 'Действие не задано' })}
                  </button>
                </div>
              )
            })}
          </div>
          {beneficiaryKind && beneficiaryKind !== 'client' ? (
            <p className="mt-2 text-xs text-amber-700">
              {t('app.services.orders.handoff.non_client_note', {
                defaultValue: 'Получатель заказа — не клиент; подбор доступен только для клиентских заказов.',
              })}
            </p>
          ) : null}
        </div>
      ) : null}

      {error ? <div className="mt-3 text-sm text-red-600">{error}</div> : null}
    </section>
  )
}

function NextActionButton({
  nextAction,
  busy,
  hasInvoice,
  outstanding,
  t,
  onConfirm,
  onComplete,
  onCreateInvoice,
  onCollectPayment,
}: {
  nextAction: ReturnType<typeof resolveServiceOrderNextAction>
  busy: string | null
  hasInvoice: boolean
  outstanding: number
  t: (key: string, opts?: { defaultValue?: string }) => string
  onConfirm: () => void
  onComplete: () => void
  onCreateInvoice: () => void
  onCollectPayment: () => void
}) {
  const base = 'rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50'
  switch (nextAction.key) {
    case 'draft':
      return (
        <button type="button" className={`${base} bg-brand-600 hover:bg-brand-700`} onClick={onConfirm}>
          {t('app.services.orders.action_cta.confirm', { defaultValue: 'Подтвердить заказ' })}
        </button>
      )
    case 'mark_completed':
      return (
        <button type="button" className={`${base} bg-brand-600 hover:bg-brand-700`} onClick={onComplete}>
          {t('app.services.orders.action_cta.complete', { defaultValue: 'Отметить выполненным' })}
        </button>
      )
    case 'invoice_needed':
      return (
        <button
          type="button"
          className={`${base} bg-brand-600 hover:bg-brand-700`}
          disabled={busy === 'invoice'}
          onClick={onCreateInvoice}
        >
          {busy === 'invoice'
            ? t('app.services.orders.action_cta.invoicing', { defaultValue: 'Создаём…' })
            : t('app.services.orders.action_cta.invoice', { defaultValue: 'Выставить счёт' })}
        </button>
      )
    case 'collect_payment':
      return (
        <button
          type="button"
          className={`${base} bg-emerald-600 hover:bg-emerald-700`}
          disabled={busy === 'payment' || !hasInvoice || outstanding <= 0}
          onClick={onCollectPayment}
        >
          {busy === 'payment'
            ? t('app.services.orders.action_cta.paying', { defaultValue: 'Отмечаем…' })
            : t('app.services.orders.action_cta.collect_payment', { defaultValue: 'Получить оплату' })}
        </button>
      )
    default:
      return null
  }
}

function describeNextStep(
  action: ReturnType<typeof resolveServiceOrderNextAction>,
  t: (key: string, opts?: { defaultValue?: string; values?: Record<string, string | number> }) => string,
): string {
  const base = 'app.services.orders.next_action'
  switch (action.key) {
    case 'cancelled':
      return t(`${base}.cancelled`, { defaultValue: 'Заказ отменён' })
    case 'draft':
      return t(`${base}.draft`, { defaultValue: 'Подтвердите заказ, чтобы начать выполнение' })
    case 'on_hold':
      return t(`${base}.on_hold`, { defaultValue: 'На паузе — проверьте перед продолжением' })
    case 'invoice_needed':
      return t(`${base}.invoice_needed`, { defaultValue: 'Выставьте счёт по завершённому заказу' })
    case 'collect_payment':
      return t(`${base}.collect_payment`, { defaultValue: 'Получите оплату (есть задолженность)' })
    case 'closed':
      return t(`${base}.closed`, { defaultValue: 'По заказу расчёты закрыты' })
    case 'schedule_slots':
      return t(`${base}.schedule_slots`, { defaultValue: 'Запланируйте слоты для услуг с расписанием' })
    case 'deliver_lines':
      return t(`${base}.deliver_lines`, {
        defaultValue: 'Завершите выполнение {{count}} поз.',
        values: { count: action.count },
      })
    case 'mark_completed':
      return t(`${base}.mark_completed`, { defaultValue: 'Отметьте заказ завершённым после работы' })
    case 'review':
    default:
      return t(`${base}.review`, { defaultValue: 'Проверьте статус заказа' })
  }
}
