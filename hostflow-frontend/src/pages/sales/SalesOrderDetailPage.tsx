import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  BILLING_TRIGGERS,
  createSalesOrderLine,
  getSalesOrder,
  updateSalesOrder,
  updateSalesOrderLine,
  type BillingTrigger,
  type SalesOrder,
  type SalesOrderLine,
} from '../../api/salesOrders'
import { listCompanies } from '../../api/client'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { SALES_ORDERS_PATH } from '../../app/salesPaths'
import { useI18n } from '../../i18n'

const triggerLabel = (code: string) => code.replace(/_/g, ' ')

export default function SalesOrderDetailPage() {
  const { t } = useI18n()
  const { orderId = '' } = useParams<{ orderId: string }>()
  const [order, setOrder] = useState<SalesOrder | null>(null)
  const [companyName, setCompanyName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const [lineTitle, setLineTitle] = useState('')
  const [lineQty, setLineQty] = useState('1')
  const [lineRole, setLineRole] = useState('')
  const [lineLocation, setLineLocation] = useState('')
  const [lineRate, setLineRate] = useState('')
  const [lineTrigger, setLineTrigger] = useState<BillingTrigger>('headcount_completed')
  const [savingLine, setSavingLine] = useState(false)
  const [savingStatus, setSavingStatus] = useState(false)

  const load = useCallback(async () => {
    if (!orderId) return
    setLoading(true)
    setError(null)
    try {
      const data = await getSalesOrder(orderId)
      setOrder(data)
      const cosRaw = await listCompanies({ limit: 500 }).catch(() => [])
      const cos = Array.isArray((cosRaw as { items?: unknown })?.items)
        ? (cosRaw as { items: Array<{ id?: string; name?: string }> }).items
        : Array.isArray(cosRaw)
          ? (cosRaw as Array<{ id?: string; name?: string }>)
          : []
      const hit = cos.find((c) => String(c.id) === String(data.company_id))
      setCompanyName(hit?.name ? String(hit.name) : data.company_id)
    } catch (e) {
      setOrder(null)
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [orderId])

  useEffect(() => {
    void load()
  }, [load])

  const onAddLine = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!order || !lineTitle.trim()) return
    setSavingLine(true)
    setMessage(null)
    setError(null)
    try {
      await createSalesOrderLine(order.id, {
        title: lineTitle.trim(),
        quantity_needed: Math.max(1, Number(lineQty) || 1),
        role_label: lineRole.trim() || undefined,
        location: lineLocation.trim() || undefined,
        unit_rate: lineRate !== '' ? Number(lineRate) : undefined,
        billing_trigger: lineTrigger,
      })
      setLineTitle('')
      setLineQty('1')
      setLineRole('')
      setLineLocation('')
      setLineRate('')
      setLineTrigger('headcount_completed')
      setMessage(t('app.sales_orders.detail.line_added', { defaultValue: 'Линия добавлена' }))
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSavingLine(false)
    }
  }

  const onStatusChange = async (status: string) => {
    if (!order) return
    setSavingStatus(true)
    setError(null)
    try {
      const updated = await updateSalesOrder(order.id, { status })
      setOrder(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSavingStatus(false)
    }
  }

  const onLineStatus = async (line: SalesOrderLine, status: string) => {
    setError(null)
    try {
      await updateSalesOrderLine(line.id, { status })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  if (loading) {
    return (
      <div className="px-4 py-6 text-sm text-slate-500 sm:px-6">
        {t('common.loading', { defaultValue: 'Загрузка…' })}
      </div>
    )
  }

  if (!order) {
    return (
      <div className="px-4 py-6 sm:px-6">
        <p className="text-sm text-rose-700">{error || t('app.sales_orders.detail.not_found', { defaultValue: 'Заказ не найден' })}</p>
        <Link to={SALES_ORDERS_PATH} className="mt-3 inline-block text-sm text-brand-700 hover:underline">
          ← {t('app.sales_orders.create.back', { defaultValue: 'К списку заказов' })}
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 overflow-y-auto px-4 py-4 sm:px-6" data-testid="sales-order-detail">
      <div>
        <Link to={SALES_ORDERS_PATH} className="text-sm text-slate-600 hover:text-brand-700">
          ← {t('app.sales_orders.create.back', { defaultValue: 'К списку заказов' })}
        </Link>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">{order.title}</h2>
            <p className="mt-1 text-sm text-slate-600">
              {companyName}
              {order.currency ? ` · ${order.currency}` : ''}
              {order.payment_term_days != null ? ` · ${order.payment_term_days}d` : ''}
            </p>
          </div>
          <label className="text-sm text-slate-600">
            {t('app.sales_orders.detail.status', { defaultValue: 'Статус' })}
            <select
              className="input ml-2 w-auto"
              value={String(order.status)}
              disabled={savingStatus}
              onChange={(e) => void onStatusChange(e.target.value)}
              data-testid="sales-order-status"
            >
              <option value="open">open</option>
              <option value="in_progress">in_progress</option>
              <option value="completed">completed</option>
              <option value="cancelled">cancelled</option>
            </select>
          </label>
        </div>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          {t('app.sales_orders.detail.snapshot', { defaultValue: 'Снимок сделки' })}
        </h3>
        <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">{t('app.sales_orders.create.payment_model', { defaultValue: 'Модель оплаты' })}</dt>
            <dd className="font-medium text-slate-900">{order.payment_model || '—'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">{t('app.sales_orders.create.vat', { defaultValue: 'VAT %' })}</dt>
            <dd className="font-medium text-slate-900">{order.vat_rate ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">{t('app.sales_orders.create.guarantee', { defaultValue: 'Гарантия, дней' })}</dt>
            <dd className="font-medium text-slate-900">{order.guarantee_days ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">{t('app.sales_orders.detail.invoice_policy', { defaultValue: 'Право на счёт' })}</dt>
            <dd className="font-medium text-slate-900">{order.invoice_right_policy || '—'}</dd>
          </div>
          {order.billing_notes ? (
            <div className="sm:col-span-2">
              <dt className="text-slate-500">{t('app.sales_orders.create.notes', { defaultValue: 'Коммерческие заметки' })}</dt>
              <dd className="mt-1 whitespace-pre-wrap text-slate-800">{order.billing_notes}</dd>
            </div>
          ) : null}
        </dl>
      </section>

      <section>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-base font-semibold text-slate-900">
            {t('app.sales_orders.detail.lines_title', { defaultValue: 'Order Lines' })}
          </h3>
          <Link
            to={CRM_APP_PATHS.vacancyNew}
            className="text-sm text-brand-700 hover:underline"
          >
            {t('app.sales_orders.detail.create_vacancy', { defaultValue: 'Создать вакансию →' })}
          </Link>
        </div>
        <p className="mt-1 text-sm text-slate-600">
          {t('app.sales_orders.detail.lines_hint', {
            defaultValue: '1 линия = 1 вакансия. Свободная линия появляется в форме вакансии.',
          })}
        </p>

        {(order.lines || []).length === 0 ? (
          <p className="mt-3 rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-4 text-sm text-slate-600">
            {t('app.sales_orders.detail.no_lines', { defaultValue: 'Линий пока нет — добавьте первую ниже.' })}
          </p>
        ) : (
          <ul className="mt-3 divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-200 bg-white">
            {(order.lines || []).map((line) => (
              <li key={line.id} className="px-4 py-3" data-testid={`sales-order-line-${line.id}`}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900">{line.title}</p>
                    <p className="mt-0.5 text-sm text-slate-500">
                      qty {line.quantity_needed}
                      {line.location ? ` · ${line.location}` : ''}
                      {line.unit_rate != null ? ` · ${line.unit_rate}` : ''}
                      {' · '}
                      {triggerLabel(String(line.billing_trigger))}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      {line.vacancy_id
                        ? t('app.sales_orders.detail.linked_vacancy', {
                            defaultValue: 'Вакансия привязана',
                          })
                        : t('app.sales_orders.detail.unlinked', {
                            defaultValue: 'Свободна для вакансии',
                          })}
                    </p>
                  </div>
                  <select
                    className="input w-auto text-sm"
                    value={String(line.status)}
                    onChange={(e) => void onLineStatus(line, e.target.value)}
                    aria-label="line status"
                  >
                    <option value="open">open</option>
                    <option value="in_progress">in_progress</option>
                    <option value="completed">completed</option>
                    <option value="cancelled">cancelled</option>
                  </select>
                </div>
              </li>
            ))}
          </ul>
        )}

        <form
          className="mt-4 space-y-3 rounded-xl border border-slate-200 bg-white p-4"
          onSubmit={onAddLine}
          data-testid="sales-order-add-line"
        >
          <h4 className="text-sm font-semibold text-slate-800">
            {t('app.sales_orders.detail.add_line', { defaultValue: 'Добавить Order Line' })}
          </h4>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block sm:col-span-2">
              <div className="label">{t('app.sales_orders.detail.line_title', { defaultValue: 'Название / роль' })} *</div>
              <input
                className="input"
                value={lineTitle}
                onChange={(e) => setLineTitle(e.target.value)}
                required
                data-testid="sales-order-line-title"
              />
            </label>
            <label className="block">
              <div className="label">{t('app.sales_orders.detail.qty', { defaultValue: 'Количество' })}</div>
              <input
                className="input"
                type="number"
                min={1}
                max={9999}
                value={lineQty}
                onChange={(e) => setLineQty(e.target.value)}
              />
            </label>
            <label className="block">
              <div className="label">{t('app.sales_orders.detail.trigger', { defaultValue: 'Billing trigger' })}</div>
              <select
                className="input"
                value={lineTrigger}
                onChange={(e) => setLineTrigger(e.target.value as BillingTrigger)}
                data-testid="sales-order-line-trigger"
              >
                {BILLING_TRIGGERS.map((code) => (
                  <option key={code} value={code}>
                    {triggerLabel(code)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <div className="label">{t('app.sales_orders.detail.role', { defaultValue: 'Role label' })}</div>
              <input className="input" value={lineRole} onChange={(e) => setLineRole(e.target.value)} />
            </label>
            <label className="block">
              <div className="label">{t('app.vacancies.detail.fields.location', { defaultValue: 'Локация' })}</div>
              <input className="input" value={lineLocation} onChange={(e) => setLineLocation(e.target.value)} />
            </label>
            <label className="block">
              <div className="label">{t('app.sales_orders.detail.rate', { defaultValue: 'Ставка' })}</div>
              <input
                className="input"
                type="number"
                step="0.01"
                value={lineRate}
                onChange={(e) => setLineRate(e.target.value)}
              />
            </label>
          </div>
          <button type="submit" className="btn-primary" disabled={savingLine} data-testid="sales-order-line-submit">
            {savingLine
              ? t('common.saving', { defaultValue: 'Сохранение…' })
              : t('app.sales_orders.detail.add_line_submit', { defaultValue: 'Добавить линию' })}
          </button>
        </form>
      </section>

      {message ? (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">{message}</p>
      ) : null}
      {error ? (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</p>
      ) : null}
    </div>
  )
}
