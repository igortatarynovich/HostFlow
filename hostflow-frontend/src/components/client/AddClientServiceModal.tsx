import { useCallback, useEffect, useMemo, useState } from 'react'

import { addClientService, listAdditionalServices } from '../../api/additionalServices'
import type { AdditionalService, AdditionalServiceOrder } from '../../api/types'
import { Modal } from '../Modal'
import { useToast } from '../Toast'
import { useI18n } from '../../i18n'
import { catalogExecutionMode } from '../../modules/services/serviceOrderBeneficiary'

function formatMoney(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat('pl-PL', { style: 'currency', currency: currency || 'PLN' }).format(value)
  } catch {
    return `${value.toFixed(2)} ${currency || 'PLN'}`
  }
}

/**
 * "Добавить услугу" for an existing client. Reuses the same catalog the sales
 * loop uses; on submit calls the create-or-append endpoint so the Service Order
 * is born once. Same component serves the first sale and every later one.
 */
export function AddClientServiceModal({
  open,
  companyId,
  onClose,
  onAdded,
}: {
  open: boolean
  companyId: string
  onClose: () => void
  onAdded?: (order: AdditionalServiceOrder) => void | Promise<void>
}) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [catalog, setCatalog] = useState<AdditionalService[]>([])
  const [loadingCatalog, setLoadingCatalog] = useState(true)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
    if (open) {
      setSelected(new Set())
      setError(null)
      void loadCatalog()
    }
  }, [open, loadCatalog])

  const selectedCount = selected.size

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
      const order = await addClientService(
        companyId,
        [...selected].map((service_id) => ({ service_id, qty: 1 })),
      )
      notify({
        title: t('app.client_workspace.add_service.done', { defaultValue: 'Услуга добавлена в заказ' }),
        variant: 'success',
      })
      await onAdded?.(order)
      onClose()
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

  const catalogEmpty = useMemo(() => !loadingCatalog && catalog.length === 0, [loadingCatalog, catalog])

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title={t('app.client_workspace.add_service.title', { defaultValue: 'Добавить услугу' })}
    >
      <p className="text-sm text-slate-600">
        {t('app.client_workspace.add_service.subtitle', {
          defaultValue:
            'Выберите услуги из каталога. Если у клиента есть открытый заказ — добавим строку, иначе создадим новый.',
        })}
      </p>

      {loadingCatalog ? (
        <p className="mt-4 text-sm text-slate-500">{t('app.common.loading', { defaultValue: 'Загрузка…' })}</p>
      ) : catalogEmpty ? (
        <p className="mt-4 text-sm text-amber-800">
          {t('app.client_inquiry.service_order.empty_catalog', {
            defaultValue: 'В каталоге нет активных услуг. Добавьте услуги в Services → Каталог.',
          })}
        </p>
      ) : (
        <ul className="mt-4 max-h-80 space-y-2 overflow-y-auto pr-1">
          {catalog.map((service) => {
            const mode = catalogExecutionMode(service)
            const checked = selected.has(service.id)
            return (
              <li key={service.id}>
                <label
                  className={[
                    'flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-3 transition',
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
                          mode === 'handoff' ? 'bg-blue-100 text-blue-800' : 'bg-slate-200 text-slate-700',
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

      {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}

      <div className="mt-4 flex flex-wrap items-center justify-end gap-2">
        <button
          type="button"
          className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
          onClick={onClose}
        >
          {t('common.actions.cancel', { defaultValue: 'Отмена' })}
        </button>
        <button
          type="button"
          className="rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          disabled={submitting || catalogEmpty || selectedCount === 0}
          onClick={() => void handleSubmit()}
        >
          {submitting
            ? t('app.client_workspace.add_service.saving', { defaultValue: 'Добавляем…' })
            : selectedCount > 0
              ? t('app.client_workspace.add_service.submit_n', {
                  defaultValue: 'Добавить ({{count}})',
                  values: { count: selectedCount },
                })
              : t('app.client_workspace.add_service.submit', { defaultValue: 'Добавить услугу' })}
        </button>
      </div>
    </Modal>
  )
}
