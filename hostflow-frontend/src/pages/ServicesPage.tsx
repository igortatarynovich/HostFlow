import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import {
  addServiceSchedule,
  createAdditionalService,
  createServiceOrder,
  deliverServiceItem,
  updateAdditionalService,
  updateServiceOrder,
} from '../api/additionalServices'
import type {
  AdditionalService,
  AdditionalServiceItem,
  AdditionalServiceOrder,
  AdditionalServiceOrderSummary,
  Candidate,
  Company,
  ServiceItemStatus,
  ServiceOrderStatus,
  ServiceScheduleStatus,
  Vacancy,
} from '../api/types'
import { useAdditionalServiceCatalog, useServiceOrder, useServiceOrderSummary, useServiceOrders } from '../hooks/useAdditionalServices'
import { usePermissions } from '../hooks/usePermissions'
import { searchCandidates } from '../api/candidates'
import { listCompanies } from '../api/client'
import { listVacancies } from '../api/vacancies'
import { getAnalyticsProfileSummary, getServicesAnalyticsOverview, type ServicesAnalyticsOverview } from '../api/analytics'
import { useI18n } from '../i18n'
import { ORDER_STATUSES, SCHEDULE_STATUSES, ITEM_STATUSES, DOCUMENT_STATUSES } from '../modules/services/constants'
import type { NewServiceFormState, NewOrderFormState } from '../modules/services/types'
import { formatAmount } from '../modules/services/utils'
import EmptyStatePanel from '../components/EmptyStatePanel'
import { useBusinessTerminology } from '../hooks/useBusinessTerminology'

const initialServiceState: NewServiceFormState = {
  code: '',
  name: '',
  category: '',
  basePrice: '0',
  estimatedCost: '0',
  costCurrency: 'PLN',
  vatRate: '23',
  resultDocumentType: '',
  requiresSchedule: false,
  requiresCandidate: true,
}

const initialOrderState: NewOrderFormState = {
  candidateId: '',
  vacancyId: '',
  companyId: '',
  notes: '',
  serviceId: '',
  serviceCode: '',
  qty: '1',
  unitPrice: '',
  estimatedCost: '',
  actualCost: '',
  costCurrency: 'PLN',
  vatRate: '',
  currency: 'PLN',
}

export function ServicesPage() {
  const { t } = useI18n()
  const { openEntityLabel } = useBusinessTerminology()
  const navigate = useNavigate()
  const { can } = usePermissions()
  const [tab, setTab] = useState<'analytics' | 'orders' | 'catalog'>('orders')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [catalogForm, setCatalogForm] = useState<NewServiceFormState>(initialServiceState)
  const [catalogMessage, setCatalogMessage] = useState<string | null>(null)
  const [ordersMessage, setOrdersMessage] = useState<string | null>(null)
  const [orderForm, setOrderForm] = useState<NewOrderFormState>(initialOrderState)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [profileSummary, setProfileSummary] = useState<Awaited<ReturnType<typeof getAnalyticsProfileSummary>> | null>(null)
  const [analyticsOverview, setAnalyticsOverview] = useState<ServicesAnalyticsOverview | null>(null)
  const [analyticsDays, setAnalyticsDays] = useState<30 | 90 | 180>(90)
  const [analyticsTrendBucket, setAnalyticsTrendBucket] = useState<'week' | 'month'>('month')
  const [analyticsSliceBy, setAnalyticsSliceBy] = useState<'client' | 'item' | 'status' | 'manager'>('client')
  const [ordersDrilldown, setOrdersDrilldown] = useState<
    | null
    | { kind: 'order'; orderId: string }
    | { kind: 'client'; ownerKind: string; ownerId?: string | null }
    | { kind: 'item'; serviceId?: string | null; label: string }
    | { kind: 'manager'; label: string }
    | { kind: 'status'; status: string }
    | { kind: 'trend'; bucket: string }
  >(null)

  const catalogHook = useAdditionalServiceCatalog(includeInactive)

  const orderQuery = useMemo(() => {
    if (statusFilter === 'all') return {}
    return { status: statusFilter as ServiceOrderStatus }
  }, [statusFilter])

  const ordersHook = useServiceOrders(orderQuery)
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null)
  const orderDetailHook = useServiceOrder(selectedOrderId)
  const orderSummaryHook = useServiceOrderSummary(selectedOrderId)

  useEffect(() => {
    if (!selectedOrderId && ordersHook.orders.length > 0) {
      setSelectedOrderId(ordersHook.orders[0].id)
    }
  }, [ordersHook.orders, selectedOrderId])

  useEffect(() => {
    let active = true
    getAnalyticsProfileSummary()
      .then((data) => {
        if (active) setProfileSummary(data)
      })
      .catch(() => {
        if (active) setProfileSummary(null)
      })
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    let active = true
    getServicesAnalyticsOverview({ days: analyticsDays, trend_bucket: analyticsTrendBucket, slice_by: analyticsSliceBy })
      .then((data) => {
        if (active) setAnalyticsOverview(data)
      })
      .catch(() => {
        if (active) setAnalyticsOverview(null)
      })
    return () => {
      active = false
    }
  }, [ordersHook.orders, catalogHook.services, analyticsDays, analyticsTrendBucket, analyticsSliceBy])

  const handleCreateService = async (event: FormEvent) => {
    event.preventDefault()
    setCatalogMessage(null)
    if (!catalogForm.code.trim() || !catalogForm.name.trim()) {
      setCatalogMessage(t('app.services.catalog.messages.missing_fields'))
      return
    }
    try {
      await createAdditionalService({
        code: catalogForm.code.trim(),
        name: catalogForm.name.trim(),
        category: catalogForm.category.trim() || undefined,
        base_price: Number.parseFloat(catalogForm.basePrice) || 0,
        estimated_cost: Number.parseFloat(catalogForm.estimatedCost) || 0,
        cost_currency: catalogForm.costCurrency.trim() || 'PLN',
        vat_rate: Number.parseFloat(catalogForm.vatRate) || 0,
        result_document_type: catalogForm.resultDocumentType.trim() || undefined,
        requires_schedule: catalogForm.requiresSchedule,
        requires_candidate: catalogForm.requiresCandidate,
      })
      setCatalogForm(initialServiceState)
      setCatalogMessage(t('app.services.catalog.messages.create_success'))
      await catalogHook.reload()
    } catch (err: any) {
      setCatalogMessage(err?.response?.data?.detail || t('app.services.catalog.messages.create_error'))
    }
  }

  const handleToggleServiceActive = async (service: AdditionalService) => {
    try {
      await updateAdditionalService(service.id, { is_active: !service.is_active })
      await catalogHook.reload()
    } catch (err) {
      setCatalogMessage(t('app.services.catalog.messages.status_error'))
    }
  }

  const handleCreateOrder = async (event: FormEvent) => {
    event.preventDefault()
    setOrdersMessage(null)

    const owners = [orderForm.candidateId, orderForm.vacancyId, orderForm.companyId].filter((v) => v.trim())
    if (owners.length !== 1) {
      setOrdersMessage(t('app.services.orders.messages.owner_required'))
      return
    }

    if (!orderForm.serviceId.trim() && !orderForm.serviceCode.trim()) {
      setOrdersMessage(t('app.services.orders.messages.service_required'))
      return
    }

    try {
      await createServiceOrder({
        candidate_id: orderForm.candidateId.trim() || undefined,
        vacancy_id: orderForm.vacancyId.trim() || undefined,
        company_id: orderForm.companyId.trim() || undefined,
        currency: orderForm.currency.trim() || 'PLN',
        notes: orderForm.notes.trim() || undefined,
        items: [
          {
            service_id: orderForm.serviceId.trim() || undefined,
            service_code: orderForm.serviceCode.trim() || undefined,
            qty: Number.parseFloat(orderForm.qty) || 1,
            unit_price: orderForm.unitPrice ? Number.parseFloat(orderForm.unitPrice) : undefined,
            estimated_cost: orderForm.estimatedCost ? Number.parseFloat(orderForm.estimatedCost) : undefined,
            actual_cost: orderForm.actualCost ? Number.parseFloat(orderForm.actualCost) : undefined,
            cost_currency: orderForm.costCurrency.trim() || undefined,
            cost_source: 'manual_order_form',
            vat_rate: orderForm.vatRate ? Number.parseFloat(orderForm.vatRate) : undefined,
          },
        ],
      })
      setOrderForm(initialOrderState)
      setOrdersMessage(t('app.services.orders.messages.created'))
      await ordersHook.reload()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (typeof detail === 'string') {
        setOrdersMessage(detail)
      } else if (detail?.reason === 'documents_missing') {
        setOrdersMessage(
          t('app.services.orders.messages.missing_docs', { values: { list: (detail.missing || []).join(', ') } }),
        )
      } else {
        setOrdersMessage(t('app.services.orders.messages.create_error'))
      }
    }
  }

  const handleUpdateOrderStatus = async (orderId: string, status: ServiceOrderStatus) => {
    try {
      await updateServiceOrder(orderId, { status })
      await Promise.all([ordersHook.reload(), orderDetailHook.reload(), orderSummaryHook.reload()])
      setOrdersMessage(t('app.services.orders.messages.status_updated'))
    } catch (err) {
      setOrdersMessage(t('app.services.orders.messages.status_error'))
    }
  }

  const handleScheduleSubmit = async (itemId: string, event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    try {
      await addServiceSchedule(itemId, {
        provider: String(data.get('provider') || ''),
        slot_start: String(data.get('slot_start') || ''),
        slot_end: String(data.get('slot_end') || ''),
        location: String(data.get('location') || ''),
        status: String(data.get('status') || 'reserved') as ServiceScheduleStatus,
      })
      form.reset()
      await Promise.all([ordersHook.reload(), orderDetailHook.reload(), orderSummaryHook.reload()])
      setOrdersMessage(t('app.services.orders.messages.schedule_updated'))
    } catch (err) {
      setOrdersMessage(t('app.services.orders.messages.schedule_error'))
    }
  }

  const handleDeliverItem = async (item: AdditionalServiceItem, event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    try {
      await deliverServiceItem(item.id, {
        status: 'delivered',
        result_document: item.result_document_type
          ? {
              document_type: item.result_document_type,
              status: String(data.get('doc_status') || 'approved'),
              issued_at: String(data.get('issued_at') || ''),
              expires_at: String(data.get('expires_at') || ''),
            }
          : undefined,
      })
      form.reset()
      await Promise.all([ordersHook.reload(), orderDetailHook.reload(), orderSummaryHook.reload()])
      setOrdersMessage(t('app.services.orders.messages.delivered'))
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (detail?.reason === 'documents_missing') {
        setOrdersMessage(
          t('app.services.orders.messages.missing_docs', { values: { list: (detail.missing || []).join(', ') } }),
        )
      } else {
        setOrdersMessage(t('app.services.orders.messages.deliver_error'))
      }
    }
  }

  const serviceInsights = useMemo(() => {
    const visibleOrders = ordersHook.orders.length
    let activeOrders = 0
    let deliveredOrders = 0
    let totalRevenue = 0
    let deliveredRevenue = 0
    let estimatedCost = 0
    let actualCost = 0
    let confirmedCostItems = 0
    let totalCostItems = 0
    ordersHook.orders.forEach((order: AdditionalServiceOrder) => {
      const status = order.status
      const amount = Number(order.total_amount ?? 0)
      order.items.forEach((item) => {
        totalCostItems += 1
        estimatedCost += Number(item.estimated_cost ?? 0)
        if (typeof item.actual_cost === 'number') {
          actualCost += Number(item.actual_cost)
          confirmedCostItems += 1
        }
      })
      if (status === 'delivered') {
        deliveredOrders += 1
        deliveredRevenue += amount
      }
      const terminal = status === 'delivered' || status === 'cancelled' || status === 'refunded'
      if (!terminal) activeOrders += 1
      totalRevenue += amount
    })
    const catalogActive = catalogHook.services.filter((svc) => svc.is_active).length
    const pipelineValue = totalRevenue - deliveredRevenue
    const averageCheck = deliveredOrders ? deliveredRevenue / deliveredOrders : 0
    const costCoverage = totalCostItems ? Math.round((confirmedCostItems / totalCostItems) * 100) : 0
    const grossProfit = totalRevenue - (actualCost || estimatedCost)
    const grossMargin = totalRevenue > 0 ? Math.round((grossProfit / totalRevenue) * 100) : 0
    return {
      visibleOrders,
      activeOrders,
      deliveredOrders,
      totalRevenue,
      averageCheck,
      pipelineValue,
      catalogActive,
      grossProfit,
      grossMargin,
      estimatedCost,
      actualCost,
      costCoverage,
    }
  }, [ordersHook.orders, catalogHook.services])

  const serviceHeroCards = [
    {
      key: 'visible',
      label: t('app.services.hero.orders_visible'),
      value: serviceInsights.visibleOrders,
      hint: t('app.services.hero.orders_visible_hint', { values: { count: serviceInsights.visibleOrders } }),
    },
    {
      key: 'active',
      label: t('app.services.hero.orders_active'),
      value: serviceInsights.activeOrders,
      hint: t('app.services.hero.orders_active_hint'),
    },
    {
      key: 'delivered',
      label: t('app.services.hero.orders_delivered'),
      value: serviceInsights.deliveredOrders,
      hint: t('app.services.hero.orders_delivered_hint'),
    },
    {
      key: 'revenue',
      label: t('app.services.hero.orders_revenue'),
      value: formatAmount(serviceInsights.pipelineValue),
      hint: t('app.services.hero.orders_revenue_hint'),
    },
    {
      key: 'catalog',
      label: t('app.services.hero.catalog_active'),
      value: serviceInsights.catalogActive,
      hint: t('app.services.hero.catalog_hint', { values: { total: catalogHook.services.length } }),
    },
    {
      key: 'profit',
      label: t('app.services.hero.gross_profit', { defaultValue: 'Gross profit' }),
      value: formatAmount(serviceInsights.grossProfit),
      hint: t('app.services.hero.gross_profit_hint', {
        defaultValue: 'Margin {{margin}}% · cost coverage {{coverage}}%',
        values: { margin: serviceInsights.grossMargin, coverage: serviceInsights.costCoverage },
      }),
    },
  ]

  const tabs = (
    <div className="flex flex-wrap gap-2">
      {(['orders', 'catalog', 'analytics'] as const).map((key) => (
        <button
          key={key}
          type="button"
          className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
            tab === key ? 'bg-white text-brand-700 shadow-sm' : 'bg-white/20 text-white/90 hover:bg-white/30'
          }`}
          onClick={() => setTab(key)}
        >
          {t(`app.services.tabs.${key}`)}
        </button>
      ))}
    </div>
  )

  const heroSection = (
    <section className="rounded-3xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-6 text-white shadow-card">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-1">
          <p className="text-2xl font-semibold">{t('app.services.title')}</p>
          <p className="text-sm text-white/80">{t('app.services.hero.subtitle')}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {tabs}
        </div>
      </div>
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {serviceHeroCards.map((card) => (
          <div key={card.key} className="rounded-2xl border border-white/30 bg-white/10 p-4">
            <div className="text-sm text-white/80">{card.label}</div>
            <div className="text-2xl font-semibold">{card.value}</div>
            <div className="text-xs text-white/70">{card.hint}</div>
          </div>
        ))}
      </div>
    </section>
  )

  return (
    <div className="space-y-4">
      {heroSection}

      {tab === 'catalog' && (
        <CatalogTab
          services={catalogHook.services}
          loading={catalogHook.loading}
          includeInactive={includeInactive}
          onToggleInclude={() => setIncludeInactive((prev) => !prev)}
          canManage={can('services.catalog.manage')}
          formState={catalogForm}
          onFormChange={setCatalogForm}
          onSubmit={handleCreateService}
          onToggleActive={handleToggleServiceActive}
          message={catalogMessage}
        />
      )}
      {tab === 'orders' && (
        <OrdersTab
          statusFilter={statusFilter}
          onStatusFilterChange={setStatusFilter}
          orders={ordersHook.orders}
          loading={ordersHook.loading}
          message={ordersMessage}
          selectedOrderId={selectedOrderId}
          onSelectOrder={setSelectedOrderId}
          order={orderDetailHook.order}
          summary={orderSummaryHook.summary}
          canManage={can('services.orders.manage')}
          onStatusUpdate={handleUpdateOrderStatus}
          onScheduleSubmit={handleScheduleSubmit}
          onDeliverItem={handleDeliverItem}
          orderForm={orderForm}
          onOrderFormChange={setOrderForm}
          onCreateOrder={handleCreateOrder}
          services={catalogHook.services}
          openEntityLabel={openEntityLabel}
          drilldown={ordersDrilldown}
          analyticsTrendBucket={analyticsTrendBucket}
          onClearDrilldown={() => setOrdersDrilldown(null)}
        />
      )}
      {tab === 'analytics' && (
        <ServicesAnalyticsTab
          analytics={analyticsOverview}
          profileSummary={profileSummary}
          analyticsDays={analyticsDays}
          analyticsTrendBucket={analyticsTrendBucket}
          analyticsSliceBy={analyticsSliceBy}
          onAnalyticsDaysChange={setAnalyticsDays}
          onAnalyticsTrendBucketChange={setAnalyticsTrendBucket}
          onAnalyticsSliceByChange={setAnalyticsSliceBy}
          onOpenClient={(companyId) => {
            if (companyId) navigate(`/app/clients/${companyId}`)
          }}
          onOpenInvoices={(params) => {
            const search = new URLSearchParams()
            if (params.companyId) search.set('company_id', params.companyId)
            if (params.serviceOrderId) search.set('service_order_id', params.serviceOrderId)
            if (params.status) search.set('status', params.status)
            navigate(`/app/invoices${search.toString() ? `?${search.toString()}` : ''}`)
          }}
          onDrilldown={(next) => {
            setOrdersDrilldown(next)
            if (next.kind === 'status') {
              setStatusFilter(next.status)
            } else {
              setStatusFilter('all')
            }
            if (next.kind === 'order') {
              setSelectedOrderId(next.orderId)
            } else {
              setSelectedOrderId(null)
            }
            setTab('orders')
          }}
          formatStatus={(status) => t(`app.services.status.order.${status}`)}
        />
      )}
    </div>
  )
}

type CatalogTabProps = {
  services: AdditionalService[]
  loading: boolean
  includeInactive: boolean
  onToggleInclude: () => void
  canManage: boolean
  formState: NewServiceFormState
  onFormChange: (next: NewServiceFormState) => void
  onSubmit: (ev: FormEvent) => void
  onToggleActive: (service: AdditionalService) => void
  message: string | null
}

function CatalogTab({
  services,
  loading,
  includeInactive,
  onToggleInclude,
  canManage,
  formState,
  onFormChange,
  onSubmit,
  onToggleActive,
  message,
}: CatalogTabProps) {
  const { t } = useI18n()
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={includeInactive} onChange={onToggleInclude} />
            {t('app.services.catalog.show_archived')}
          </label>
        </div>
      </div>

      {canManage && (
        <form className="app-surface space-y-3 p-4" onSubmit={onSubmit}>
          <h2 className="text-lg font-semibold">{t('app.services.catalog.new_service.title')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700">{t('app.services.catalog.new_service.labels.code')}</label>
              <input
                className="input mt-1"
                value={formState.code}
                onChange={(e) => onFormChange({ ...formState, code: e.target.value })}
                placeholder={t('app.services.catalog.new_service.placeholders.code')}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">{t('app.services.catalog.new_service.labels.name')}</label>
              <input
                className="input mt-1"
                value={formState.name}
                onChange={(e) => onFormChange({ ...formState, name: e.target.value })}
                placeholder={t('app.services.catalog.new_service.placeholders.name')}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">{t('app.services.catalog.new_service.labels.category')}</label>
              <input
                className="input mt-1"
                value={formState.category}
                onChange={(e) => onFormChange({ ...formState, category: e.target.value })}
                placeholder={t('app.services.catalog.new_service.placeholders.category')}
              />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="block text-sm font-medium text-slate-700">{t('app.services.catalog.new_service.labels.price')}</label>
                <input
                  className="input mt-1"
                  value={formState.basePrice}
                  onChange={(e) => onFormChange({ ...formState, basePrice: e.target.value })}
                  placeholder={t('app.services.catalog.new_service.placeholders.price')}
                  type="number"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">
                  {t('app.services.catalog.new_service.labels.estimated_cost', { defaultValue: 'Est. cost' })}
                </label>
                <input
                  className="input mt-1"
                  value={formState.estimatedCost}
                  onChange={(e) => onFormChange({ ...formState, estimatedCost: e.target.value })}
                  placeholder={t('app.services.catalog.new_service.placeholders.estimated_cost', { defaultValue: '210' })}
                  type="number"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">{t('app.services.catalog.new_service.labels.vat')}</label>
                <input
                  className="input mt-1"
                  value={formState.vatRate}
                  onChange={(e) => onFormChange({ ...formState, vatRate: e.target.value })}
                  placeholder={t('app.services.catalog.new_service.placeholders.vat')}
                  type="number"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-sm font-medium text-slate-700">
                  {t('app.services.catalog.new_service.labels.cost_currency', { defaultValue: 'Cost currency' })}
                </label>
                <input
                  className="input mt-1"
                  value={formState.costCurrency}
                  onChange={(e) => onFormChange({ ...formState, costCurrency: e.target.value.toUpperCase() })}
                  placeholder="PLN"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">{t('app.services.catalog.new_service.labels.document')}</label>
                <input
                  className="input mt-1"
                  value={formState.resultDocumentType}
                  onChange={(e) => onFormChange({ ...formState, resultDocumentType: e.target.value })}
                  placeholder={t('app.services.catalog.new_service.placeholders.document')}
                />
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={formState.requiresSchedule}
                onChange={(e) => onFormChange({ ...formState, requiresSchedule: e.target.checked })}
              />
              {t('app.services.catalog.new_service.labels.requires_schedule')}
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={formState.requiresCandidate}
                onChange={(e) => onFormChange({ ...formState, requiresCandidate: e.target.checked })}
              />
              {t('app.services.catalog.new_service.labels.requires_candidate')}
            </label>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-500">{t('app.services.catalog.new_service.hint')}</span>
            <button
              type="submit"
              className="btn-primary"
            >
              {t('app.services.catalog.new_service.submit')}
            </button>
          </div>
          {message && <div className="text-sm text-brand-700">{message}</div>}
        </form>
      )}

      <div className="overflow-auto rounded-lg border border-slate-200">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50/90 text-left">
            <tr>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">{t('app.services.catalog.table.code')}</th>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">{t('app.services.catalog.table.name')}</th>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">{t('app.services.catalog.table.category')}</th>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">{t('app.services.catalog.table.price')}</th>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">{t('app.services.catalog.table.schedule')}</th>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">{t('app.services.catalog.table.candidate')}</th>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">{t('app.services.catalog.table.status')}</th>
              {canManage && <th className="border-b border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600" />}
            </tr>
          </thead>
          <tbody className="bg-white">
            {loading ? (
              <tr>
                <td colSpan={canManage ? 8 : 7} className="px-4 py-4 text-center text-slate-500">
                  {t('app.services.catalog.table.loading')}
                </td>
              </tr>
            ) : services.length === 0 ? (
              <tr>
                <td colSpan={canManage ? 8 : 7} className="px-4 py-4 text-center text-slate-500">
                  {t('app.services.catalog.table.empty')}
                </td>
              </tr>
            ) : (
              services.map((svc) => (
                <tr
                  key={svc.id}
                  className={[
                    'border-t border-slate-100 transition',
                    svc.is_active ? 'hover:bg-brand-50/40' : 'bg-slate-50',
                  ].join(' ')}
                >
                  <td className="border-r border-slate-200 px-4 py-2 font-mono text-sm">{svc.code}</td>
                  <td className="border-r border-slate-200 px-4 py-2">{svc.name}</td>
                  <td className="border-r border-slate-200 px-4 py-2 text-slate-600">{svc.category || '—'}</td>
                  <td className="border-r border-slate-200 px-4 py-2">{formatAmount(svc.base_price)}</td>
                  <td className="border-r border-slate-200 px-4 py-2">{svc.requires_schedule ? t('app.services.words.yes') : t('app.services.words.no')}</td>
                  <td className="border-r border-slate-200 px-4 py-2">{svc.requires_candidate ? t('app.services.words.yes') : t('app.services.words.no')}</td>
                  <td className="border-r border-slate-200 px-4 py-2">
                    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${svc.is_active ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-700'}`}>
                      {svc.is_active ? t('app.services.catalog.table.badges.active') : t('app.services.catalog.table.badges.archived')}
                    </span>
                  </td>
                  {canManage && (
                    <td className="px-4 py-2 text-right">
                      <button
                        type="button"
                        onClick={() => onToggleActive(svc)}
                        className="btn-secondary btn-xs"
                      >
                        {svc.is_active ? t('app.services.catalog.table.actions.archive') : t('app.services.catalog.table.actions.activate')}
                      </button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {message && !canManage && <div className="text-sm text-brand-700">{message}</div>}
    </div>
  )
}

type OrdersTabProps = {
  statusFilter: string
  onStatusFilterChange: (value: string) => void
  orders: AdditionalServiceOrder[]
  loading: boolean
  message: string | null
  selectedOrderId: string | null
  onSelectOrder: (value: string | null) => void
  order: AdditionalServiceOrder | null
  summary: AdditionalServiceOrderSummary | null
  canManage: boolean
  onStatusUpdate: (orderId: string, status: ServiceOrderStatus) => void
  onScheduleSubmit: (itemId: string, event: FormEvent<HTMLFormElement>) => void
  onDeliverItem: (item: AdditionalServiceItem, event: FormEvent<HTMLFormElement>) => void
  orderForm: NewOrderFormState
  onOrderFormChange: (value: NewOrderFormState) => void
  onCreateOrder: (event: FormEvent) => void
  services: AdditionalService[]
  openEntityLabel: string
  drilldown: null | { kind: 'order'; orderId: string } | { kind: 'client'; ownerKind: string; ownerId?: string | null } | { kind: 'item'; serviceId?: string | null; label: string } | { kind: 'manager'; label: string } | { kind: 'status'; status: string } | { kind: 'trend'; bucket: string }
  analyticsTrendBucket: 'week' | 'month'
  onClearDrilldown: () => void
}

type OrderOwnerChoice = 'candidate' | 'vacancy' | 'company'

function OrdersTab({
  statusFilter,
  onStatusFilterChange,
  orders,
  loading,
  message,
  selectedOrderId,
  onSelectOrder,
  order,
  summary,
  canManage,
  onStatusUpdate,
  onScheduleSubmit,
  onDeliverItem,
  orderForm,
  onOrderFormChange,
  onCreateOrder,
  services,
  openEntityLabel,
  drilldown,
  analyticsTrendBucket,
  onClearDrilldown,
}: OrdersTabProps) {
  const { t } = useI18n()
  const orderStatusLabels = useMemo(() => {
    const map: Record<string, string> = {}
    ORDER_STATUSES.forEach((status) => {
      map[status] = t(`app.services.status.order.${status}`)
    })
    return map
  }, [t])
  const availableServices = useMemo(() => services.map((svc) => ({ id: svc.id, label: `${svc.name} (${svc.code})` })), [services])
  const serviceLookup = useMemo(() => new Map(services.map((svc) => [svc.id, svc])), [services])
  const [ownerChoice, setOwnerChoice] = useState<OrderOwnerChoice>('candidate')
  const [candidateQuery, setCandidateQuery] = useState('')
  const [candidateResults, setCandidateResults] = useState<Candidate[]>([])
  const [candidateLoading, setCandidateLoading] = useState(false)
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null)
  const [vacancyQuery, setVacancyQuery] = useState('')
  const [vacancyResults, setVacancyResults] = useState<Vacancy[]>([])
  const [vacancyLoading, setVacancyLoading] = useState(false)
  const [selectedVacancy, setSelectedVacancy] = useState<Vacancy | null>(null)
  const [companyQuery, setCompanyQuery] = useState('')
  const [companyResults, setCompanyResults] = useState<Company[]>([])
  const [companyLoading, setCompanyLoading] = useState(false)
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const ownerOptions = useMemo(
    () => [
      {
        key: 'candidate' as OrderOwnerChoice,
        label: t('app.services.orders.new.owner.options.candidate'),
        description: t('app.services.orders.new.owner.descriptions.candidate'),
      },
      {
        key: 'vacancy' as OrderOwnerChoice,
        label: t('app.services.orders.new.owner.options.vacancy'),
        description: t('app.services.orders.new.owner.descriptions.vacancy'),
      },
      {
        key: 'company' as OrderOwnerChoice,
        label: t('app.services.orders.new.owner.options.company'),
        description: t('app.services.orders.new.owner.descriptions.company'),
      },
    ],
    [t],
  )

  useEffect(() => {
    if (ownerChoice !== 'candidate' || !candidateQuery.trim()) {
      setCandidateResults([])
      setCandidateLoading(false)
      return
    }

    let active = true
    setCandidateLoading(true)
    const handle = window.setTimeout(async () => {
      try {
        const results = await searchCandidates({ q: candidateQuery, limit: 10 })
        if (active) {
          setCandidateResults(results)
        }
      } catch (err) {
        if (active) {
          console.warn('[services] candidate search failed', err)
          setCandidateResults([])
        }
      } finally {
        if (active) {
          setCandidateLoading(false)
        }
      }
    }, 250)

    return () => {
      active = false
      window.clearTimeout(handle)
    }
  }, [candidateQuery, ownerChoice])

  useEffect(() => {
    if (!orderForm.candidateId) {
      setSelectedCandidate(null)
    }
  }, [orderForm.candidateId])

  const handleOwnerChoiceChange = (choice: OrderOwnerChoice) => {
    if (choice === ownerChoice) return
    setOwnerChoice(choice)
    onOrderFormChange({
      ...orderForm,
      candidateId: choice === 'candidate' ? orderForm.candidateId : '',
      vacancyId: choice === 'vacancy' ? orderForm.vacancyId : '',
      companyId: choice === 'company' ? orderForm.companyId : '',
    })
    if (choice !== 'candidate') {
      setSelectedCandidate(null)
      setCandidateQuery('')
      setCandidateResults([])
    }
    if (choice !== 'vacancy') {
      setSelectedVacancy(null)
      setVacancyQuery('')
      setVacancyResults([])
    }
    if (choice !== 'company') {
      setSelectedCompany(null)
      setCompanyQuery('')
      setCompanyResults([])
    }
  }

  const handleCandidateSelect = (candidate: Candidate) => {
    setSelectedCandidate(candidate)
    setCandidateQuery('')
    setCandidateResults([])
    onOrderFormChange({
      ...orderForm,
      candidateId: candidate.id,
      vacancyId: '',
      companyId: '',
    })
    setOwnerChoice('candidate')
    setSelectedVacancy(null)
    setSelectedCompany(null)
  }

  const clearCandidateSelection = () => {
    setSelectedCandidate(null)
    setCandidateQuery('')
    setCandidateResults([])
    onOrderFormChange({ ...orderForm, candidateId: '' })
  }

  const showCandidateResults = ownerChoice === 'candidate' && candidateQuery.trim().length >= 2

  useEffect(() => {
    if (ownerChoice !== 'vacancy' || !vacancyQuery.trim()) {
      setVacancyResults([])
      setVacancyLoading(false)
      return
    }
    let active = true
    setVacancyLoading(true)
    const handle = window.setTimeout(async () => {
      try {
        const results = await listVacancies({ q: vacancyQuery.trim(), limit: 10 })
        if (active) {
          setVacancyResults(Array.isArray(results) ? results : [])
        }
      } catch (err) {
        if (active) {
          console.warn('[services] vacancy search failed', err)
          setVacancyResults([])
        }
      } finally {
        if (active) {
          setVacancyLoading(false)
        }
      }
    }, 250)
    return () => {
      active = false
      window.clearTimeout(handle)
    }
  }, [vacancyQuery, ownerChoice])

  useEffect(() => {
    if (!orderForm.vacancyId) {
      setSelectedVacancy(null)
    }
  }, [orderForm.vacancyId])

  const handleVacancySelect = (vacancy: Vacancy) => {
    setSelectedVacancy(vacancy)
    setVacancyQuery('')
    setVacancyResults([])
    onOrderFormChange({
      ...orderForm,
      vacancyId: vacancy.id,
      candidateId: '',
      companyId: '',
    })
    setOwnerChoice('vacancy')
    setSelectedCandidate(null)
    setSelectedCompany(null)
  }

  const clearVacancySelection = () => {
    setSelectedVacancy(null)
    setVacancyQuery('')
    setVacancyResults([])
    onOrderFormChange({ ...orderForm, vacancyId: '' })
  }

  const showVacancyResults = ownerChoice === 'vacancy' && vacancyQuery.trim().length >= 2

  useEffect(() => {
    if (ownerChoice !== 'company' || !companyQuery.trim()) {
      setCompanyResults([])
      setCompanyLoading(false)
      return
    }
    let active = true
    setCompanyLoading(true)
    const handle = window.setTimeout(async () => {
      try {
        const results = await listCompanies({ limit: 10, search: companyQuery.trim() })
        if (active) {
          setCompanyResults(Array.isArray(results) ? results : [])
        }
      } catch (err) {
        if (active) {
          console.warn('[services] company search failed', err)
          setCompanyResults([])
        }
      } finally {
        if (active) {
          setCompanyLoading(false)
        }
      }
    }, 250)
    return () => {
      active = false
      window.clearTimeout(handle)
    }
  }, [companyQuery, ownerChoice])

  useEffect(() => {
    if (!orderForm.companyId) {
      setSelectedCompany(null)
    }
  }, [orderForm.companyId])

  const handleCompanySelect = (company: Company) => {
    setSelectedCompany(company)
    setCompanyQuery('')
    setCompanyResults([])
    onOrderFormChange({
      ...orderForm,
      companyId: company.id,
      candidateId: '',
      vacancyId: '',
    })
    setOwnerChoice('company')
    setSelectedCandidate(null)
    setSelectedVacancy(null)
  }

  const clearCompanySelection = () => {
    setSelectedCompany(null)
    setCompanyQuery('')
    setCompanyResults([])
    onOrderFormChange({ ...orderForm, companyId: '' })
  }

  const showCompanyResults = ownerChoice === 'company' && companyQuery.trim().length >= 2

  const trendBucketForDate = (value: string) => {
    const dt = new Date(value)
    if (Number.isNaN(dt.getTime())) return ''
    if (analyticsTrendBucket === 'week') {
      const tmp = new Date(Date.UTC(dt.getUTCFullYear(), dt.getUTCMonth(), dt.getUTCDate()))
      const dayNum = tmp.getUTCDay() || 7
      tmp.setUTCDate(tmp.getUTCDate() + 4 - dayNum)
      const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1))
      const weekNo = Math.ceil((((tmp.getTime() - yearStart.getTime()) / 86400000) + 1) / 7)
      return `${tmp.getUTCFullYear()}-W${String(weekNo).padStart(2, '0')}`
    }
    return `${dt.getUTCFullYear()}-${String(dt.getUTCMonth() + 1).padStart(2, '0')}`
  }

  const managerLabelForOrder = (order: AdditionalServiceOrder) => {
    return order.assigned_to ? `Manager ${order.assigned_to.slice(0, 8)}` : 'Unassigned'
  }

  const visibleOrders = useMemo(() => {
    if (!drilldown) return orders
    return orders.filter((order) => {
      if (drilldown.kind === 'order') return order.id === drilldown.orderId
      if (drilldown.kind === 'client') {
        if (drilldown.ownerKind === 'company') return order.company_id === drilldown.ownerId
        if (drilldown.ownerKind === 'candidate') return order.candidate_id === drilldown.ownerId
        if (drilldown.ownerKind === 'vacancy') return order.vacancy_id === drilldown.ownerId
        return false
      }
      if (drilldown.kind === 'item') {
        return order.items.some((item) => (drilldown.serviceId ? item.service_id === drilldown.serviceId : (item.service?.name || item.service?.code) === drilldown.label))
      }
      if (drilldown.kind === 'manager') return managerLabelForOrder(order) === drilldown.label
      if (drilldown.kind === 'status') return order.status === drilldown.status
      if (drilldown.kind === 'trend') return trendBucketForDate(order.created_at) === drilldown.bucket
      return true
    })
  }, [orders, drilldown, analyticsTrendBucket])

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
      <div className="space-y-4">
        {canManage && (
          <form className="app-surface space-y-3 p-4" onSubmit={onCreateOrder}>
            <h2 className="text-lg font-semibold">{t('app.services.orders.new.title')}</h2>
            <p className="text-sm text-slate-500">{t('app.services.orders.new.hint')}</p>
            <div className="space-y-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('app.services.orders.new.owner.title')}
                </p>
                <p className="text-xs text-slate-500">{t('app.services.orders.new.owner.hint')}</p>
                <div className="mt-2 grid gap-2 sm:grid-cols-3">
                  {ownerOptions.map((option) => (
                    <button
                      key={option.key}
                      type="button"
                      className={[
                        'rounded-lg border px-3 py-3 text-left transition',
                        ownerChoice === option.key
                          ? 'border-brand-300 bg-brand-50 text-brand-900 shadow-sm'
                          : 'border-slate-200 text-slate-600 hover:border-brand-200',
                      ].join(' ')}
                      onClick={() => handleOwnerChoiceChange(option.key)}
                    >
                      <div className="text-sm font-semibold">{option.label}</div>
                      <div className="text-xs text-slate-500">{option.description}</div>
                    </button>
                  ))}
                </div>
              </div>

              {ownerChoice === 'candidate' && (
                <div>
                  <label className="block text-sm font-medium text-slate-700">{t('app.services.orders.new.fields.candidate')}</label>
                  <input
                    className="input mt-1 text-sm"
                    placeholder={t('app.services.orders.new.placeholders.candidate_search')}
                    value={candidateQuery}
                    onChange={(e) => setCandidateQuery(e.target.value)}
                  />
                  {candidateLoading && showCandidateResults && (
                    <div className="mt-1 text-xs text-slate-500">{t('app.services.orders.new.states.searching')}</div>
                  )}
                  {showCandidateResults && !candidateLoading && (
                    <div className="mt-2 max-h-48 overflow-auto rounded-lg border border-slate-200 bg-white shadow-sm">
                      {candidateResults.length === 0 ? (
                        <div className="px-3 py-2 text-xs text-slate-500">{t('app.services.orders.new.states.no_results')}</div>
                      ) : (
                        <ul className="divide-y divide-slate-100 text-sm">
                          {candidateResults.map((cand) => (
                            <li key={cand.id}>
                              <button
                                type="button"
                                className="flex w-full flex-col items-start px-3 py-2 hover:bg-brand-50"
                                onClick={() => handleCandidateSelect(cand)}
                              >
                                <span className="font-medium text-slate-800">
                                  {cand.first_name} {cand.last_name} ({cand.short_id || cand.id.slice(0, 8)})
                                </span>
                                <span className="text-xs text-slate-500">
                                  {cand.phone || cand.email || t('app.services.orders.new.states.no_contacts')}
                                </span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                  {selectedCandidate && (
                    <div className="alert-info mt-3 flex items-start justify-between gap-2">
                      <div>
                        <div className="font-semibold">
                          {selectedCandidate.first_name} {selectedCandidate.last_name}
                        </div>
                        <div className="text-xs text-brand-700">
                          ID: <span className="font-mono">{selectedCandidate.id}</span>
                        </div>
                        {selectedCandidate.company_name && (
                          <div className="text-xs text-brand-700">
                            {t('app.services.orders.new.selected.company', {
                              values: { name: selectedCandidate.company_name },
                            })}
                          </div>
                        )}
                        {selectedCandidate.vacancy_name && (
                          <div className="text-xs text-brand-700">
                            {t('app.services.orders.new.selected.vacancy', {
                              values: { name: selectedCandidate.vacancy_name },
                            })}
                          </div>
                        )}
                      </div>
                      <button type="button" className="btn-secondary btn-xs" onClick={clearCandidateSelection}>
                        {t('common.actions.clear')}
                      </button>
                    </div>
                  )}
                  <div className="mt-1 text-xs text-slate-500">
                    {orderForm.candidateId
                      ? t('app.services.orders.new.current_candidate', {
                          values: { id: orderForm.candidateId },
                        })
                      : t('app.services.orders.new.current_candidate_empty')}
                  </div>
                </div>
              )}

              {ownerChoice === 'vacancy' && (
                <div>
                  <label className="block text-sm font-medium text-slate-700">{t('app.services.orders.new.fields.vacancy')}</label>
                  <input
                    className="input mt-1 text-sm"
                    placeholder={t('app.services.orders.new.placeholders.vacancy_search')}
                    value={vacancyQuery}
                    onChange={(e) => setVacancyQuery(e.target.value)}
                  />
                  {vacancyLoading && showVacancyResults && (
                    <div className="mt-1 text-xs text-slate-500">{t('app.services.orders.new.states.searching')}</div>
                  )}
                  {showVacancyResults && !vacancyLoading && (
                    <div className="mt-2 max-h-48 overflow-auto rounded-lg border border-slate-200 bg-white shadow-sm">
                      {vacancyResults.length === 0 ? (
                        <div className="px-3 py-2 text-xs text-slate-500">{t('app.services.orders.new.states.no_results')}</div>
                      ) : (
                        <ul className="divide-y divide-slate-100 text-sm">
                          {vacancyResults.map((vac) => (
                            <li key={vac.id}>
                              <button
                                type="button"
                                className="flex w-full flex-col items-start px-3 py-2 hover:bg-brand-50"
                                onClick={() => handleVacancySelect(vac)}
                              >
                                <span className="font-medium text-slate-800">{vac.title}</span>
                                <span className="text-xs text-slate-500">
                                  {vac.company_name || t('common.labels.unnamed')}
                                  {vac.location ? ` • ${vac.location}` : ''}
                                </span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                  {selectedVacancy && (
                    <div className="alert-info mt-3 flex items-start justify-between gap-2">
                      <div>
                        <div className="font-semibold">{selectedVacancy.title}</div>
                        {selectedVacancy.company_name && (
                          <div className="text-xs text-brand-700">
                            {t('app.services.orders.new.selected.company', {
                              values: { name: selectedVacancy.company_name },
                            })}
                          </div>
                        )}
                        {selectedVacancy.location && (
                          <div className="text-xs text-brand-700">{selectedVacancy.location}</div>
                        )}
                      </div>
                      <button type="button" className="btn-secondary btn-xs" onClick={clearVacancySelection}>
                        {t('common.actions.clear')}
                      </button>
                    </div>
                  )}
                  <div className="mt-1 text-xs text-slate-500">
                    {orderForm.vacancyId
                      ? t('app.services.orders.new.current_vacancy', { values: { id: orderForm.vacancyId } })
                      : t('app.services.orders.new.current_vacancy_empty')}
                  </div>
                </div>
              )}

              {ownerChoice === 'company' && (
                <div>
                  <label className="block text-sm font-medium text-slate-700">{t('app.services.orders.new.fields.company')}</label>
                  <input
                    className="input mt-1 text-sm"
                    placeholder={t('app.services.orders.new.placeholders.company_search')}
                    value={companyQuery}
                    onChange={(e) => setCompanyQuery(e.target.value)}
                  />
                  {companyLoading && showCompanyResults && (
                    <div className="mt-1 text-xs text-slate-500">{t('app.services.orders.new.states.searching')}</div>
                  )}
                  {showCompanyResults && !companyLoading && (
                    <div className="mt-2 max-h-48 overflow-auto rounded-lg border border-slate-200 bg-white shadow-sm">
                      {companyResults.length === 0 ? (
                        <div className="px-3 py-2 text-xs text-slate-500">{t('app.services.orders.new.states.no_results')}</div>
                      ) : (
                        <ul className="divide-y divide-slate-100 text-sm">
                          {companyResults.map((company) => (
                            <li key={company.id}>
                              <button
                                type="button"
                                className="flex w-full flex-col items-start px-3 py-2 hover:bg-brand-50"
                                onClick={() => handleCompanySelect(company)}
                              >
                                <span className="font-medium text-slate-800">{company.name || company.legal_name || t('common.labels.unnamed')}</span>
                                {(company.city || company.country_code) && (
                                  <span className="text-xs text-slate-500">
                                    {[company.city, company.country_code].filter(Boolean).join(', ')}
                                  </span>
                                )}
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                  {selectedCompany && (
                    <div className="alert-info mt-3 flex items-start justify-between gap-2">
                      <div>
                        <div className="font-semibold">{selectedCompany.name || selectedCompany.legal_name || t('common.labels.unnamed')}</div>
                        {(selectedCompany.city || selectedCompany.country_code) && (
                          <div className="text-xs text-brand-700">
                            {[selectedCompany.city, selectedCompany.country_code].filter(Boolean).join(', ')}
                          </div>
                        )}
                        {selectedCompany.email && <div className="text-xs text-brand-700">{selectedCompany.email}</div>}
                      </div>
                      <button type="button" className="btn-secondary btn-xs" onClick={clearCompanySelection}>
                        {t('common.actions.clear')}
                      </button>
                    </div>
                  )}
                  <div className="mt-1 text-xs text-slate-500">
                    {orderForm.companyId
                      ? t('app.services.orders.new.current_company', { values: { id: orderForm.companyId } })
                      : t('app.services.orders.new.current_company_empty')}
                  </div>
                </div>
              )}
            </div>
            <div className="space-y-2">
              <select
                className="input text-sm"
                value={orderForm.serviceId}
                onChange={(e) => {
                  const serviceId = e.target.value
                  const selected = serviceLookup.get(serviceId)
                  onOrderFormChange({
                    ...orderForm,
                    serviceId,
                    serviceCode: '',
                    unitPrice: selected ? String(selected.base_price ?? '') : orderForm.unitPrice,
                    estimatedCost: selected ? String(selected.estimated_cost ?? '') : orderForm.estimatedCost,
                    costCurrency: selected ? String(selected.cost_currency || selected.currency || 'PLN') : orderForm.costCurrency,
                    vatRate: selected ? String(selected.vat_rate ?? '') : orderForm.vatRate,
                    currency: selected ? String(selected.currency || 'PLN') : orderForm.currency,
                  })
                }}
              >
                <option value="">{t('app.services.orders.new.placeholders.service_id')}</option>
                {availableServices.map((svc) => (
                  <option key={svc.id} value={svc.id}>{svc.label}</option>
                ))}
              </select>
              <input
                className="input text-sm"
                placeholder={t('app.services.orders.new.placeholders.service_code')}
                value={orderForm.serviceCode}
                onChange={(e) => onOrderFormChange({ ...orderForm, serviceCode: e.target.value, serviceId: '' })}
              />
              <div className="grid grid-cols-3 gap-2">
                <input
                  className="input text-sm"
                  placeholder={t('app.services.orders.new.placeholders.qty')}
                  type="number"
                  value={orderForm.qty}
                  onChange={(e) => onOrderFormChange({ ...orderForm, qty: e.target.value })}
                />
                <input
                  className="input text-sm"
                  placeholder={t('app.services.orders.new.placeholders.unit_price')}
                  type="number"
                  value={orderForm.unitPrice}
                  onChange={(e) => onOrderFormChange({ ...orderForm, unitPrice: e.target.value })}
                />
                <input
                  className="input text-sm"
                  placeholder={t('app.services.orders.new.placeholders.vat')}
                  type="number"
                  value={orderForm.vatRate}
                  onChange={(e) => onOrderFormChange({ ...orderForm, vatRate: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-3 gap-2">
                <input
                  className="input text-sm"
                  placeholder={t('app.services.orders.new.placeholders.estimated_cost', { defaultValue: 'Estimated cost' })}
                  type="number"
                  value={orderForm.estimatedCost}
                  onChange={(e) => onOrderFormChange({ ...orderForm, estimatedCost: e.target.value })}
                />
                <input
                  className="input text-sm"
                  placeholder={t('app.services.orders.new.placeholders.actual_cost', { defaultValue: 'Actual cost' })}
                  type="number"
                  value={orderForm.actualCost}
                  onChange={(e) => onOrderFormChange({ ...orderForm, actualCost: e.target.value })}
                />
                <input
                  className="input text-sm"
                  placeholder={t('app.services.orders.new.placeholders.cost_currency', { defaultValue: 'Cost currency' })}
                  value={orderForm.costCurrency}
                  onChange={(e) => onOrderFormChange({ ...orderForm, costCurrency: e.target.value.toUpperCase() })}
                />
              </div>
            </div>
            <textarea
              className="textarea text-sm"
              placeholder={t('app.services.orders.new.placeholders.notes')}
              rows={3}
              value={orderForm.notes}
              onChange={(e) => onOrderFormChange({ ...orderForm, notes: e.target.value })}
            />
            <button type="submit" className="btn-primary w-full justify-center">
              {t('app.services.orders.new.submit')}
            </button>
            {message && <div className="text-sm text-brand-700">{message}</div>}
          </form>
        )}

        <div className="app-surface p-0 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
            <h2 className="text-lg font-semibold">{t('app.services.orders.list.title')}</h2>
            <div className="flex items-center gap-2">
              {drilldown && (
                <button type="button" className="btn-secondary btn-xs" onClick={onClearDrilldown}>
                  {t('app.services.analytics.drilldown.clear', { defaultValue: 'Clear drilldown' })}
                </button>
              )}
              <select
                className="input w-auto py-1 text-sm"
                value={statusFilter}
                onChange={(e) => onStatusFilterChange(e.target.value)}
              >
                <option value="all">{t('app.services.orders.filters.status_all')}</option>
                {ORDER_STATUSES.map((status) => (
                  <option key={status} value={status}>{orderStatusLabels[status] ?? status}</option>
                ))}
              </select>
            </div>
          </div>
          {drilldown && (
            <div className="border-b border-slate-200 bg-brand-50 px-4 py-2 text-xs text-brand-800">
              {t('app.services.analytics.drilldown.active', { defaultValue: 'Analytics drilldown is active. Orders list is scoped to the selected metric.' })}
            </div>
          )}
          <div className="max-h-[420px] overflow-auto px-4 py-3">
            {loading ? (
              <div className="px-4 py-6 text-center text-sm text-slate-500">{t('app.services.orders.list.loading')}</div>
            ) : visibleOrders.length === 0 ? (
              <div className="px-2 py-4">
                <EmptyStatePanel
                  compact
                  title={t('app.services.orders.list.empty_title', { defaultValue: 'No service orders yet' })}
                  description={t('app.services.orders.list.empty_desc', {
                    defaultValue: 'Create your first order using the form above and assign it to client, vacancy or candidate.',
                  })}
                  primaryAction={{
                    label: openEntityLabel,
                    to: '/app/clients',
                  }}
                  secondaryAction={{
                    label: t('app.services.orders.list.empty_cta_leads', { defaultValue: 'Open leads' }),
                    to: '/app/leads',
                  }}
                />
              </div>
            ) : (
              <ul className="space-y-3">
                {visibleOrders.map((ord) => (
                  <li key={ord.id}>
                    <button
                      type="button"
                      onClick={() => onSelectOrder(ord.id)}
                      className={[
                        'w-full rounded-2xl border px-4 py-3 text-left transition',
                        selectedOrderId === ord.id
                          ? 'border-brand-200 bg-brand-50'
                          : 'border-slate-100 bg-white hover:bg-brand-50/40',
                      ].join(' ')}
                    >
                      <div className="flex items-baseline justify-between">
                       <span className="text-sm font-medium text-brand-700">{ord.id.slice(0, 8)}…</span>
                        <span className="text-xs uppercase tracking-wide text-slate-500">
                          {orderStatusLabels[ord.status] ?? ord.status}
                        </span>
                     </div>
                     <div className="mt-1 text-sm text-slate-600">
                        {ord.candidate_id
                          ? t('app.services.orders.list.owner.candidate', { values: { id: ord.candidate_id.slice(0, 8) } })
                          : ord.company_id
                          ? t('app.services.orders.list.owner.company', { values: { id: ord.company_id.slice(0, 8) } })
                          : ord.vacancy_id
                          ? t('app.services.orders.list.owner.vacancy', { values: { id: ord.vacancy_id.slice(0, 8) } })
                          : t('app.services.orders.list.owner.none')}
                     </div>
                      <div className="mt-1 text-xs text-slate-400">
                        {t('app.services.orders.list.meta', {
                          values: { count: ord.items.length, amount: formatAmount(ord.total_amount) },
                        })}
                      </div>
                   </button>
                 </li>
               ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      <div className="app-surface p-4 space-y-4">
        {!selectedOrderId || !order ? (
          <div className="text-sm text-slate-500">{t('app.services.orders.detail.placeholder')}</div>
        ) : (
          <OrderDetail
            order={order}
            summary={summary}
            canManage={canManage}
            onStatusUpdate={onStatusUpdate}
            onScheduleSubmit={onScheduleSubmit}
            onDeliverItem={onDeliverItem}
          />
        )}
        {message && <div className="text-sm text-brand-700">{message}</div>}
      </div>
    </div>
  )
}

type ServicesAnalyticsTabProps = {
  analytics: ServicesAnalyticsOverview | null
  profileSummary: Awaited<ReturnType<typeof getAnalyticsProfileSummary>> | null
  analyticsDays: 30 | 90 | 180
  analyticsTrendBucket: 'week' | 'month'
  analyticsSliceBy: 'client' | 'item' | 'status' | 'manager'
  onAnalyticsDaysChange: (value: 30 | 90 | 180) => void
  onAnalyticsTrendBucketChange: (value: 'week' | 'month') => void
  onAnalyticsSliceByChange: (value: 'client' | 'item' | 'status' | 'manager') => void
  onOpenClient: (companyId?: string | null) => void
  onOpenInvoices: (params: { companyId?: string | null; serviceOrderId?: string | null; status?: string | null }) => void
  onDrilldown: (value:
    | { kind: 'order'; orderId: string }
    | { kind: 'client'; ownerKind: string; ownerId?: string | null }
    | { kind: 'item'; serviceId?: string | null; label: string }
    | { kind: 'manager'; label: string }
    | { kind: 'status'; status: string }
    | { kind: 'trend'; bucket: string }
  ) => void
  formatStatus: (status: string) => string
}

const DAY_MS = 24 * 60 * 60 * 1000

function ServicesAnalyticsTab({
  analytics,
  profileSummary,
  analyticsDays,
  analyticsTrendBucket,
  analyticsSliceBy,
  onAnalyticsDaysChange,
  onAnalyticsTrendBucketChange,
  onAnalyticsSliceByChange,
  onOpenClient,
  onOpenInvoices,
  onDrilldown,
  formatStatus,
}: ServicesAnalyticsTabProps) {
  const { t } = useI18n()

  const servicesBusinessCards = useMemo(() => {
    if (!profileSummary || profileSummary.business_type !== 'services') return []
    const kpis = profileSummary.kpis || {}
    return [
      {
        key: 'clients_total',
        label: t('app.services.analytics.profile.clients_total', { defaultValue: 'Clients' }),
        value: Number(kpis.clients_total || 0),
      },
      {
        key: 'counterparties_total',
        label: t('app.services.analytics.profile.counterparties_total', { defaultValue: 'Counterparties' }),
        value: Number(kpis.counterparties_total || 0),
      },
    ]
  }, [profileSummary, t])

  const unknownCompanyClassification = useMemo(() => {
    if (!profileSummary || profileSummary.business_type !== 'services') return 0
    return Number(profileSummary.datasets?.unknown_company_classification || 0)
  }, [profileSummary])

  const describeOwner = (ownerKind: string) => {
    if (ownerKind === 'candidate') return t('app.services.analytics.owner.candidate')
    if (ownerKind === 'vacancy') return t('app.services.analytics.owner.vacancy')
    if (ownerKind === 'company') return t('app.services.analytics.owner.company')
    return t('app.services.analytics.owner.unknown')
  }

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="text-sm font-semibold">{t('app.services.analytics.controls.title', { defaultValue: 'Analytics view' })}</div>
            <div className="text-xs text-slate-500">{t('app.services.analytics.controls.subtitle', { defaultValue: 'Change period, trend granularity and slice dimension.' })}</div>
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            <select className="input text-sm" value={analyticsDays} onChange={(e) => onAnalyticsDaysChange(Number(e.target.value) as 30 | 90 | 180)}>
              <option value={30}>{t('app.services.analytics.controls.days_30', { defaultValue: 'Last 30 days' })}</option>
              <option value={90}>{t('app.services.analytics.controls.days_90', { defaultValue: 'Last 90 days' })}</option>
              <option value={180}>{t('app.services.analytics.controls.days_180', { defaultValue: 'Last 180 days' })}</option>
            </select>
            <select className="input text-sm" value={analyticsTrendBucket} onChange={(e) => onAnalyticsTrendBucketChange(e.target.value as 'week' | 'month')}>
              <option value="week">{t('app.services.analytics.controls.trend_week', { defaultValue: 'Trend by week' })}</option>
              <option value="month">{t('app.services.analytics.controls.trend_month', { defaultValue: 'Trend by month' })}</option>
            </select>
            <select className="input text-sm" value={analyticsSliceBy} onChange={(e) => onAnalyticsSliceByChange(e.target.value as 'client' | 'item' | 'status' | 'manager')}>
              <option value="client">{t('app.services.analytics.controls.slice_client', { defaultValue: 'Slice by client' })}</option>
              <option value="item">{t('app.services.analytics.controls.slice_item', { defaultValue: 'Slice by item' })}</option>
              <option value="status">{t('app.services.analytics.controls.slice_status', { defaultValue: 'Slice by status' })}</option>
              <option value="manager">{t('app.services.analytics.controls.slice_manager', { defaultValue: 'Slice by manager' })}</option>
            </select>
          </div>
        </div>
      </div>

      {servicesBusinessCards.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2">
          {servicesBusinessCards.map((card) => (
            <div key={card.key} className="card p-4">
              <div className="text-sm font-semibold">{card.label}</div>
              <div className="mt-2 text-3xl font-semibold">{card.value}</div>
            </div>
          ))}
        </div>
      )}
      {unknownCompanyClassification > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {t('app.services.analytics.profile.unknown_company_classification', {
            defaultValue: 'Unclassified companies: {{count}}. Set company type (client/counterparty) for accurate analytics.',
            values: { count: unknownCompanyClassification },
          })}
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-4">
        <div className="card p-4">
          <div className="text-sm font-semibold">{t('app.services.analytics.last30.title')}</div>
          <div className="mt-2 text-3xl font-semibold">{analytics?.last30.total ?? 0}</div>
          <p className="text-xs text-slate-500">{t('app.services.analytics.last30.subtitle')}</p>
          <dl className="mt-4 space-y-1 text-sm text-slate-600">
            <div className="flex justify-between">
              <dt>{t('app.services.analytics.last30.delivered')}</dt>
              <dd className="font-medium">{analytics?.last30.delivered ?? 0}</dd>
            </div>
            <div className="flex justify-between">
              <dt>{t('app.services.analytics.last30.cancelled')}</dt>
              <dd className="font-medium">{analytics?.last30.cancelled ?? 0}</dd>
            </div>
            <div className="flex justify-between">
              <dt>{t('app.services.analytics.last30.rate')}</dt>
              <dd className="font-medium">{analytics?.last30.cancellation_rate ?? 0}%</dd>
            </div>
          </dl>
        </div>
        <div className="card p-4">
          <div className="text-sm font-semibold">{t('app.services.analytics.profitability.gross_profit', { defaultValue: 'Gross profit' })}</div>
          <div className="mt-2 text-3xl font-semibold">{formatAmount(analytics?.totals.gross_profit ?? 0)}</div>
          <p className="text-xs text-slate-500">
            {t('app.services.analytics.profitability.gross_margin', {
              defaultValue: 'Margin {{margin}}%',
              values: { margin: analytics?.totals.gross_margin ?? 0 },
            })}
          </p>
        </div>
        <div className="card p-4">
          <div className="text-sm font-semibold">{t('app.services.analytics.profitability.cost_basis', { defaultValue: 'Cost basis' })}</div>
          <div className="mt-2 text-3xl font-semibold">
            {formatAmount((analytics?.totals.actual_cost || 0) || (analytics?.totals.estimated_cost || 0))}
          </div>
          <p className="text-xs text-slate-500">
            {t('app.services.analytics.profitability.coverage', {
              defaultValue: 'Confirmed cost coverage {{coverage}}%',
              values: { coverage: analytics?.totals.cost_coverage ?? 0 },
            })}
          </p>
        </div>
        <div className="card p-4">
          <div className="text-sm font-semibold">{t('app.services.analytics.profitability.data_quality', { defaultValue: 'Data quality' })}</div>
          <dl className="mt-4 space-y-1 text-sm text-slate-600">
            <div className="flex justify-between">
              <dt>{t('app.services.analytics.profitability.confirmed', { defaultValue: 'Confirmed' })}</dt>
              <dd className="font-medium">{analytics?.data_quality.confirmed_items ?? 0}</dd>
            </div>
            <div className="flex justify-between">
              <dt>{t('app.services.analytics.profitability.estimated', { defaultValue: 'Estimated' })}</dt>
              <dd className="font-medium">{analytics?.data_quality.estimated_items ?? 0}</dd>
            </div>
            <div className="flex justify-between">
              <dt>{t('app.services.analytics.profitability.missing', { defaultValue: 'Missing' })}</dt>
              <dd className="font-medium">{analytics?.data_quality.missing_items ?? 0}</dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold">{t('app.services.analytics.status_breakdown.title')}</div>
            <div className="text-xs text-slate-500">{t('app.services.analytics.status_breakdown.subtitle')}</div>
          </div>
          {(analytics?.status_breakdown.length ?? 0) > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>{t('app.services.analytics.status_breakdown.status')}</th>
                  <th className="text-right">{t('app.services.analytics.status_breakdown.count')}</th>
                </tr>
              </thead>
              <tbody>
                {analytics?.status_breakdown.map((row) => (
                  <tr key={row.status} className="cursor-pointer hover:bg-brand-50/40" onClick={() => onDrilldown({ kind: 'status', status: row.status })}>
                    <td>{formatStatus(row.status)}</td>
                    <td className="text-right font-medium">{row.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-sm text-slate-500">{t('app.services.analytics.status_breakdown.empty')}</div>
          )}
        </div>
        <div className="card p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold">{t('app.services.analytics.top_services.title')}</div>
            <div className="text-xs text-slate-500">{t('app.services.analytics.top_services.subtitle')}</div>
          </div>
          {(analytics?.top_items.length ?? 0) > 0 ? (
            <ul className="space-y-2 text-sm">
              {analytics?.top_items.map((service) => (
                <li key={service.label}>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1 text-left hover:bg-brand-50/40"
                    onClick={() => onDrilldown({ kind: 'item', serviceId: service.service_id, label: service.label })}
                  >
                  <div>
                    <p className="font-medium">{service.label}</p>
                    <p className="text-xs text-slate-500">
                      {t('app.services.analytics.top_services.pending', { values: { count: service.pending } })} · {formatAmount(service.profit)}
                    </p>
                  </div>
                  <span className="text-sm font-semibold">{service.total}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-slate-500">{t('app.services.analytics.top_services.empty')}</div>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold">{t('app.services.analytics.trends.title', { defaultValue: 'Trends' })}</div>
            <div className="text-xs text-slate-500">{t('app.services.analytics.trends.subtitle', { defaultValue: 'Revenue and profit by period bucket' })}</div>
          </div>
          {(analytics?.trends.length ?? 0) > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>{t('app.services.analytics.trends.bucket', { defaultValue: 'Bucket' })}</th>
                  <th className="text-right">{t('app.services.analytics.trends.orders', { defaultValue: 'Orders' })}</th>
                  <th className="text-right">{t('app.services.analytics.trends.delivered', { defaultValue: 'Delivered' })}</th>
                  <th className="text-right">{t('app.services.analytics.trends.revenue', { defaultValue: 'Revenue' })}</th>
                  <th className="text-right">{t('app.services.analytics.trends.profit', { defaultValue: 'Profit' })}</th>
                </tr>
              </thead>
              <tbody>
              {analytics?.trends.map((row) => (
                  <tr key={row.bucket} className="cursor-pointer hover:bg-brand-50/40" onClick={() => onDrilldown({ kind: 'trend', bucket: row.bucket })}>
                    <td>{row.bucket}</td>
                    <td className="text-right">{row.orders}</td>
                    <td className="text-right">{row.delivered}</td>
                    <td className="text-right">{formatAmount(row.revenue)}</td>
                    <td className="text-right">{formatAmount(row.profit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-sm text-slate-500">{t('app.services.analytics.trends.empty', { defaultValue: 'No trend data yet' })}</div>
          )}
        </div>

        <div className="card p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold">{t('app.services.analytics.slices.title', { defaultValue: 'Slice view' })}</div>
            <div className="text-xs text-slate-500">{t('app.services.analytics.slices.subtitle', { defaultValue: 'Pivot-like ranking by selected dimension' })}</div>
          </div>
          {(analytics?.slices.length ?? 0) > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>{t('app.services.analytics.slices.dimension', { defaultValue: 'Dimension' })}</th>
                  <th className="text-right">{t('app.services.analytics.slices.orders', { defaultValue: 'Orders' })}</th>
                  <th className="text-right">{t('app.services.analytics.slices.revenue', { defaultValue: 'Revenue' })}</th>
                  <th className="text-right">{t('app.services.analytics.slices.profit', { defaultValue: 'Profit' })}</th>
                </tr>
              </thead>
              <tbody>
              {analytics?.slices.map((row) => (
                  <tr
                    key={row.label}
                    className="cursor-pointer hover:bg-brand-50/40"
                    onClick={() => {
                      if (row.slice_kind === 'item') onDrilldown({ kind: 'item', label: row.label })
                      else if (row.slice_kind === 'status' && row.slice_value) onDrilldown({ kind: 'status', status: row.slice_value })
                      else if (row.slice_kind === 'manager') onDrilldown({ kind: 'manager', label: row.label })
                      else onDrilldown({ kind: 'client', ownerKind: row.owner_kind || 'company', ownerId: row.slice_value })
                    }}
                  >
                    <td>{row.label}</td>
                    <td className="text-right">{row.orders}</td>
                    <td className="text-right">{formatAmount(row.revenue)}</td>
                    <td className="text-right">{formatAmount(row.profit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-sm text-slate-500">{t('app.services.analytics.slices.empty', { defaultValue: 'No slice data yet' })}</div>
          )}
        </div>
      </div>

      <div className="card p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-semibold">{t('app.services.analytics.top_clients.title', { defaultValue: 'Top clients' })}</div>
          <div className="text-xs text-slate-500">{t('app.services.analytics.top_clients.subtitle', { defaultValue: 'Ranked by profit and revenue' })}</div>
        </div>
        {(analytics?.top_clients.length ?? 0) > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th>{t('app.services.analytics.top_clients.client', { defaultValue: 'Client' })}</th>
                <th className="text-right">{t('app.services.analytics.top_clients.orders', { defaultValue: 'Orders' })}</th>
                <th className="text-right">{t('app.services.analytics.top_clients.revenue', { defaultValue: 'Revenue' })}</th>
                <th className="text-right">{t('app.services.analytics.top_clients.profit', { defaultValue: 'Profit' })}</th>
                <th className="text-right">{t('common.labels.actions', { defaultValue: 'Actions' })}</th>
              </tr>
            </thead>
            <tbody>
              {analytics?.top_clients.map((client) => (
                <tr
                  key={client.label}
                  className="cursor-pointer hover:bg-brand-50/40"
                  onClick={() => onDrilldown({ kind: 'client', ownerKind: client.owner_kind, ownerId: client.owner_id })}
                >
                  <td>{client.label}</td>
                  <td className="text-right">{client.orders}</td>
                  <td className="text-right">{formatAmount(client.revenue)}</td>
                  <td className="text-right">{formatAmount(client.profit)}</td>
                  <td className="text-right">
                    <div className="flex justify-end gap-2">
                      {client.owner_kind === 'company' && client.owner_id && (
                        <button
                          type="button"
                          className="btn-secondary btn-xs"
                          onClick={(event) => {
                            event.stopPropagation()
                            onOpenClient(client.owner_id)
                          }}
                        >
                          {t('app.services.analytics.actions.open_client', { defaultValue: 'Open client' })}
                        </button>
                      )}
                      {client.owner_kind === 'company' && client.owner_id && (
                        <button
                          type="button"
                          className="btn-secondary btn-xs"
                          onClick={(event) => {
                            event.stopPropagation()
                            onOpenInvoices({ companyId: client.owner_id })
                          }}
                        >
                          {t('app.services.analytics.actions.open_invoices', { defaultValue: 'Open invoices' })}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-sm text-slate-500">{t('app.services.analytics.top_clients.empty', { defaultValue: 'No client data yet' })}</div>
        )}
      </div>

      <div className="card p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-semibold">{t('app.services.analytics.hot_services.title')}</div>
          <div className="text-xs text-slate-500">{t('app.services.analytics.hot_services.subtitle')}</div>
        </div>
        {(analytics?.hot_orders.length ?? 0) > 0 ? (
          <ul className="divide-y divide-slate-100 text-sm">
            {analytics?.hot_orders.map((entry) => (
              <li key={entry.order_id} className="rounded-lg py-3 hover:bg-brand-50/40">
                <button
                  type="button"
                  className="flex w-full flex-col gap-1 text-left"
                  onClick={() => onDrilldown({ kind: 'order', orderId: entry.order_id })}
                >
                <div className="flex items-center justify-between">
                  <span className="font-medium">{entry.label}</span>
                  <span className="text-xs text-slate-500">{formatStatus(entry.status)}</span>
                </div>
                <div className="text-xs text-slate-500">
                  {t(`app.services.analytics.hot_services.reason.${entry.reason}`)} · {describeOwner(entry.owner_kind)}
                </div>
                </button>
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    className="btn-secondary btn-xs"
                    onClick={() => onOpenInvoices({ serviceOrderId: entry.order_id })}
                  >
                    {t('app.services.analytics.actions.open_invoices', { defaultValue: 'Open invoices' })}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="text-sm text-slate-500">{t('app.services.analytics.hot_services.empty')}</div>
        )}
      </div>
    </div>
  )
}

type OrderDetailProps = {
  order: AdditionalServiceOrder
  summary: AdditionalServiceOrderSummary | null
  canManage: boolean
  onStatusUpdate: (orderId: string, status: ServiceOrderStatus) => void
  onScheduleSubmit: (itemId: string, event: FormEvent<HTMLFormElement>) => void
  onDeliverItem: (item: AdditionalServiceItem, event: FormEvent<HTMLFormElement>) => void
}

function OrderDetail({ order, summary, canManage, onStatusUpdate, onScheduleSubmit, onDeliverItem }: OrderDetailProps) {
  const { t } = useI18n()
  const blockingIds = new Set(summary?.blocking_items.map((item) => item.id) ?? [])
  const missingDocs = summary?.missing_documents ?? {}
  const orderStatusLabels = useMemo(() => {
    const map: Record<string, string> = {}
    ORDER_STATUSES.forEach((status) => {
      map[status] = t(`app.services.status.order.${status}`)
    })
    return map
  }, [t])
  const scheduleStatusLabels = useMemo(() => {
    const map: Record<string, string> = {}
    SCHEDULE_STATUSES.forEach((status) => {
      map[status] = t(`app.services.status.schedule.${status}`)
    })
    return map
  }, [t])
  const itemStatusLabels = useMemo(() => {
    const map: Record<string, string> = {}
    ITEM_STATUSES.forEach((status) => {
      map[status] = t(`app.services.status.item.${status}`)
    })
    return map
  }, [t])
  const documentStatusLabels = useMemo(() => {
    const map: Record<string, string> = {}
    DOCUMENT_STATUSES.forEach((status) => {
      map[status] = t(`app.services.status.document.${status}`)
    })
    return map
  }, [t])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-slate-500">{t('app.services.orders.detail.order_label')}</div>
          <div className="text-lg font-semibold tracking-tight">{order.id}</div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-500">{t('app.services.orders.detail.status_label')}</span>
          {canManage ? (
            <select
              className="input w-auto py-1 text-sm"
              value={order.status}
              onChange={(e) => onStatusUpdate(order.id, e.target.value as ServiceOrderStatus)}
            >
              {ORDER_STATUSES.map((status) => (
                <option key={status} value={status}>{orderStatusLabels[status] ?? status}</option>
              ))}
            </select>
          ) : (
            <span className="text-sm font-medium uppercase">{orderStatusLabels[order.status] ?? order.status}</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <div className="text-slate-500">{t('app.services.orders.detail.owner_label')}</div>
          <div className="font-medium">
            {order.candidate_id
              ? t('app.services.orders.detail.owner.candidate', { values: { id: order.candidate_id } })
              : order.vacancy_id
              ? t('app.services.orders.detail.owner.vacancy', { values: { id: order.vacancy_id } })
              : order.company_id
              ? t('app.services.orders.detail.owner.company', { values: { id: order.company_id } })
              : t('app.services.orders.detail.owner.none')}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <div className="text-slate-500">{t('app.services.orders.detail.amount_label')}</div>
          <div className="font-medium">
            {formatAmount(order.total_amount)}
            {typeof order.vat_total === 'number' && (
              <span className="ml-1 text-xs text-slate-500">
                {t('app.services.orders.detail.vat_label', { values: { vat: order.vat_total.toFixed(2) } })}
              </span>
            )}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <div className="text-slate-500">{t('app.services.orders.detail.items_label')}</div>
          <div className="font-medium">{order.items.length}</div>
        </div>
      </div>

      <div className="space-y-4">
        {order.items.map((item) => {
          const isBlocking = blockingIds.has(item.id)
          const missing = missingDocs[item.id] || []
          return (
            <div key={item.id} className="border border-slate-200 rounded-lg p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="text-sm text-slate-500">{t('app.services.orders.detail.item.service_label')}</div>
                  <div className="text-base font-semibold">{item.service?.name || item.service_id}</div>
                  <div className="text-xs text-slate-400">{item.service?.code}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-slate-500">{t('app.services.orders.detail.item.status_label')}</div>
                  <div className="text-sm font-medium uppercase">{itemStatusLabels[item.status] ?? item.status}</div>
                  <div className="text-xs text-slate-500">
                    {t('app.services.orders.detail.item.amount_label', { values: { amount: formatAmount(item.amount) } })}
                  </div>
                </div>
              </div>

              {isBlocking && (
                <div className="mt-3 rounded bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-700">
                  {t('app.services.orders.detail.item.blocking_hint')}
                </div>
              )}

              {missing.length > 0 && (
                <div className="mt-3 alert-error">
                  {t('app.services.orders.detail.item.missing_docs', { values: { list: missing.join(', ') } })}
                </div>
              )}

              <div className="mt-4 space-y-3">
                <div>
                  <div className="text-sm font-medium text-slate-700">{t('app.services.orders.detail.schedule.title')}</div>
                  {item.schedules && item.schedules.length > 0 ? (
                    <ul className="mt-2 space-y-2 text-sm text-slate-600">
                      {item.schedules.map((sched) => (
                        <li key={sched.id}>
                          <div className="flex items-center justify-between">
                            <span>
                              {sched.slot_start
                                ? new Date(sched.slot_start).toLocaleString()
                                : t('app.services.orders.detail.schedule.no_date')}
                            </span>
                            <span className="text-xs uppercase">{scheduleStatusLabels[sched.status] ?? sched.status}</span>
                          </div>
                          {sched.location && <div className="text-xs text-slate-400">{sched.location}</div>}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="mt-1 text-xs text-slate-400">
                      {t('app.services.orders.detail.schedule.empty')}
                    </div>
                  )}

                  {canManage && (
                    <form className="mt-3 grid grid-cols-1 md:grid-cols-5 gap-2" onSubmit={(e) => onScheduleSubmit(item.id, e)}>
                      <input
                        name="provider"
                        className="input py-1 text-xs"
                        placeholder={t('app.services.orders.detail.schedule.form.provider_placeholder')}
                      />
                      <input name="slot_start" type="datetime-local" className="input py-1 text-xs" />
                      <input name="slot_end" type="datetime-local" className="input py-1 text-xs" />
                      <input
                        name="location"
                        className="input py-1 text-xs"
                        placeholder={t('app.services.orders.detail.schedule.form.location_placeholder')}
                      />
                      <select name="status" className="input py-1 text-xs">
                        {SCHEDULE_STATUSES.map((status) => (
                          <option key={status} value={status}>{scheduleStatusLabels[status] ?? status}</option>
                        ))}
                      </select>
                      <button type="submit" className="btn-secondary btn-xs md:col-span-5 justify-center">
                        {t('app.services.orders.detail.schedule.form.submit')}
                      </button>
                    </form>
                  )}
                </div>

                {canManage && item.status !== 'delivered' && (
                  <form className="space-y-2" onSubmit={(e) => onDeliverItem(item, e)}>
                    <div className="text-sm font-medium text-slate-700">{t('app.services.orders.detail.complete.title')}</div>
                    {item.result_document_type && (
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
                        <input
                          name="issued_at"
                          type="date"
                          className="input py-1"
                          placeholder={t('app.services.orders.detail.complete.issued_placeholder')}
                        />
                        <input
                          name="expires_at"
                          type="date"
                          className="input py-1"
                          placeholder={t('app.services.orders.detail.complete.expires_placeholder')}
                        />
                        <select name="doc_status" className="input py-1">
                          {DOCUMENT_STATUSES.map((status) => (
                            <option key={status} value={status}>{documentStatusLabels[status] ?? status}</option>
                          ))}
                        </select>
                      </div>
                    )}
                    <button type="submit" className="btn-primary btn-xs">
                      {t('app.services.orders.detail.complete.submit')}
                    </button>
                  </form>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
