import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { listAdditionalServices } from '../../api/additionalServices'
import { createClientLeadServiceOrder } from '../../api/client'
import type { AdditionalService } from '../../api/types'
import { useToast } from '../Toast'
import { useI18n } from '../../i18n'
import { clientDetailPath } from '../../services/platformHandoff'
import { serviceOrderWorkspacePath } from '../../modules/services/utils'
import { catalogExecutionMode } from '../../modules/services/serviceOrderBeneficiary'

type ClientLeadServiceOrderPanelProps = {
  leadId: string
  clientId: string
  clientName: string
  serviceOrderId?: string | null
  /** Catalog service_code carried from a Service Inquiry form route (auto-selected). */
  preselectServiceCode?: string | null
  onOrderCreated?: (orderId: string) => void | Promise<void>
}

function formatMoney(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat('pl-PL', { style: 'currency', currency: currency || 'PLN' }).format(value)
  } catch {
    return `${value.toFixed(2)} ${currency || 'PLN'}`
  }
}

export function ClientLeadServiceOrderPanel({
  leadId,
  clientId,
  clientName,
  serviceOrderId,
  preselectServiceCode,
  onOrderCreated,
}: ClientLeadServiceOrderPanelProps) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [catalog, setCatalog] = useState<AdditionalService[]>([])
  const [loadingCatalog, setLoadingCatalog] = useState(true)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [createdOrderId, setCreatedOrderId] = useState<string | null>(serviceOrderId?.trim() || null)
  const [didPreselect, setDidPreselect] = useState(false)

  const activeOrderId = createdOrderId || serviceOrderId?.trim() || null
  const preselectCode = preselectServiceCode?.trim() || null

  const loadCatalog = useCallback(async () => {
    setLoadingCatalog(true)
    try {
      const rows = await listAdditionalServices(false, false)
      setCatalog(rows.filter((s) => s.is_active && !s.requires_candidate))
    } catch {
      setCatalog([])
    } finally {
      setLoadingCatalog(false)
    }
  }, [])

  useEffect(() => {
    void loadCatalog()
  }, [loadCatalog])

  useEffect(() => {
    if (serviceOrderId?.trim()) setCreatedOrderId(serviceOrderId.trim())
  }, [serviceOrderId])

  useEffect(() => {
    if (didPreselect || !preselectCode || catalog.length === 0) return
    const match = catalog.find((s) => s.code === preselectCode)
    if (match) {
      setSelected((prev) => (prev.size > 0 ? prev : new Set([match.id])))
      setDidPreselect(true)
    }
  }, [catalog, didPreselect, preselectCode])

  const selectedServices = useMemo(
    () => catalog.filter((s) => selected.has(s.id)),
    [catalog, selected],
  )

  const toggle = (serviceId: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(serviceId)) next.delete(serviceId)
      else next.add(serviceId)
      return next
    })
  }

  const handleSubmit = async () => {
    if (selected.size === 0) {
      setError(t('app.client_inquiry.service_order.pick_one', { defaultValue: 'Выберите хотя бы одну услугу' }))
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      const order = await createClientLeadServiceOrder(
        leadId,
        [...selected].map((service_id) => ({ service_id, qty: 1 })),
      )
      const oid = String(order?.id || '').trim()
      if (!oid) throw new Error('order_create_failed')
      setCreatedOrderId(oid)
      await onOrderCreated?.(oid)
      notify({
        title: t('app.client_inquiry.service_order.created', { defaultValue: 'Заказ услуги создан' }),
        variant: 'success',
      })
    } catch (e: unknown) {
      const detail =
        (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (e as Error)?.message ??
        t('app.client_inquiry.service_order.create_failed', { defaultValue: 'Не удалось создать заказ' })
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
    } finally {
      setSubmitting(false)
    }
  }

  if (activeOrderId) {
    return (
      <section className="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-5 shadow-sm">
        <p className="text-sm font-semibold text-emerald-900">
          {t('app.client_inquiry.service_order.linked_title', { defaultValue: 'Заказ услуги создан' })}
        </p>
        <p className="mt-1 text-sm text-emerald-800">
          {t('app.client_inquiry.service_order.linked_hint', {
            defaultValue:
              'Services ведёт выполнение и счёт. Для handoff-строк на карточке заказа появится «Создать подбор».',
          })}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            to={serviceOrderWorkspacePath(activeOrderId, clientId)}
            className="inline-flex items-center justify-center rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
          >
            {t('app.client_inquiry.service_order.open_order', { defaultValue: 'Открыть заказ' })}
          </Link>
          <Link
            to={clientDetailPath(clientId)}
            className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50"
          >
            {t('app.client_inquiry.service_order.open_client', { defaultValue: 'Карточка клиента' })}
          </Link>
        </div>
        <p className="mt-2 text-xs text-slate-600">
          {clientName} · {activeOrderId.slice(0, 8)}…
        </p>
      </section>
    )
  }

  return (
    <section className="rounded-2xl border border-brand-200 bg-white p-5 shadow-sm">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
          {t('app.client_inquiry.service_order.title', { defaultValue: 'Что покупает клиент' })}
        </p>
        <p className="mt-1 text-sm text-slate-700">
          {t('app.client_inquiry.service_order.subtitle', {
            defaultValue:
              'Выберите услуги из каталога — создадим один заказ с несколькими строками. Inline → выполнение и счёт; handoff → запуск исполнителя с карточки заказа.',
          })}
        </p>
        {preselectCode ? (
          <p className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-800">
            {t('app.client_inquiry.service_order.from_inquiry', {
              defaultValue: 'Услуга из заявки Meta: {code}',
              values: { code: preselectCode },
            })}
          </p>
        ) : null}
      </div>

      {loadingCatalog ? (
        <p className="mt-4 text-sm text-slate-500">{t('app.common.loading', { defaultValue: 'Загрузка…' })}</p>
      ) : catalog.length === 0 ? (
        <p className="mt-4 text-sm text-amber-800">
          {t('app.client_inquiry.service_order.empty_catalog', {
            defaultValue: 'В каталоге нет активных услуг. Добавьте услуги в Services → Каталог.',
          })}
        </p>
      ) : (
        <ul className="mt-4 max-h-72 space-y-2 overflow-y-auto pr-1">
          {catalog.map((service) => {
            const mode = catalogExecutionMode(service)
            const checked = selected.has(service.id)
            return (
              <li key={service.id}>
                <label
                  className={[
                    'flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-2.5 transition',
                    checked ? 'border-brand-300 bg-brand-50/50' : 'border-slate-200 bg-slate-50/40 hover:bg-slate-50',
                  ].join(' ')}
                >
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600"
                    checked={checked}
                    onChange={() => toggle(service.id)}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-slate-900">{service.name}</span>
                      <span
                        className={[
                          'rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide',
                          mode === 'handoff' ? 'bg-violet-100 text-violet-800' : 'bg-slate-200 text-slate-700',
                        ].join(' ')}
                      >
                        {mode === 'handoff'
                          ? t('app.services.execution.handoff', { defaultValue: 'Handoff' })
                          : t('app.services.execution.inline', { defaultValue: 'Inline' })}
                      </span>
                    </span>
                    <span className="mt-0.5 block text-xs text-slate-500">
                      {service.code} · {formatMoney(Number(service.base_price || 0), service.currency)}
                    </span>
                  </span>
                </label>
              </li>
            )
          })}
        </ul>
      )}

      {selectedServices.length > 0 ? (
        <p className="mt-3 text-xs font-medium text-slate-600">
          {t('app.client_inquiry.service_order.selected_count', {
            defaultValue: 'Выбрано: {{count}}',
            values: { count: selectedServices.length },
          })}
        </p>
      ) : null}

      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          disabled={submitting || catalog.length === 0}
          onClick={() => void handleSubmit()}
        >
          {submitting
            ? t('app.client_inquiry.service_order.creating', { defaultValue: 'Создаём заказ…' })
            : t('app.client_inquiry.service_order.create', { defaultValue: 'Создать заказ услуги' })}
        </button>
      </div>
    </section>
  )
}
