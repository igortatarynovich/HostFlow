import type { FormEvent } from 'react'

import type { AdditionalService } from '../../api/types'
import { useI18n } from '../../i18n'
import { DataTable, Toolbar, type DataTableColumn } from '../../components/layout'
import { catalogExecutionMode } from './serviceOrderBeneficiary'
import type { NewServiceFormState } from './types'

export type CatalogTabProps = {
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
  onGoToOrders?: () => void
}

function formatAmount(value: number | null | undefined) {
  if (value == null || Number.isNaN(Number(value))) return '—'
  return Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function CatalogTab({
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
  onGoToOrders,
}: CatalogTabProps) {
  const { t } = useI18n()

  const columns: DataTableColumn<AdditionalService>[] = [
    {
      key: 'code',
      header: t('app.services.catalog.table.code'),
      cellClassName: 'font-mono',
      render: (svc) => svc.code,
    },
    {
      key: 'name',
      header: t('app.services.catalog.table.name'),
      render: (svc) => (
        <>
          <div>{svc.name}</div>
          <span className="mt-0.5 inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-600">
            {catalogExecutionMode(svc as Parameters<typeof catalogExecutionMode>[0]) === 'handoff'
              ? t('app.services.execution.handoff', { defaultValue: 'Handoff' })
              : t('app.services.execution.inline', { defaultValue: 'Inline' })}
          </span>
        </>
      ),
    },
    {
      key: 'category',
      header: t('app.services.catalog.table.category'),
      cellClassName: 'text-slate-600',
      render: (svc) => svc.category || '—',
    },
    {
      key: 'price',
      header: t('app.services.catalog.table.price'),
      render: (svc) => formatAmount(svc.base_price),
    },
    {
      key: 'orders',
      header: t('app.services.catalog.table.orders_count'),
      align: 'right',
      tabularNums: true,
      render: (svc) => svc.metrics_orders_count ?? 0,
    },
    {
      key: 'revenue',
      header: t('app.services.catalog.table.revenue_completed'),
      align: 'right',
      tabularNums: true,
      render: (svc) => formatAmount(svc.metrics_revenue_completed ?? 0),
    },
    {
      key: 'schedule',
      header: t('app.services.catalog.table.schedule'),
      render: (svc) => (svc.requires_schedule ? t('app.services.words.yes') : t('app.services.words.no')),
    },
    {
      key: 'candidate',
      header: t('app.services.catalog.table.candidate'),
      render: (svc) => (svc.requires_candidate ? t('app.services.words.yes') : t('app.services.words.no')),
    },
    {
      key: 'status',
      header: t('app.services.catalog.table.status'),
      render: (svc) => (
        <span
          className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${
            svc.is_active ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-700'
          }`}
        >
          {svc.is_active ? t('app.services.catalog.table.badges.active') : t('app.services.catalog.table.badges.archived')}
        </span>
      ),
    },
  ]

  if (canManage) {
    columns.push({
      key: 'actions',
      header: '',
      align: 'right',
      render: (svc) => (
        <button type="button" onClick={() => onToggleActive(svc)} className="btn-secondary btn-xs">
          {svc.is_active ? t('app.services.catalog.table.actions.archive') : t('app.services.catalog.table.actions.activate')}
        </button>
      ),
    })
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <Toolbar>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input type="checkbox" checked={includeInactive} onChange={onToggleInclude} />
          {t('app.services.catalog.show_archived')}
        </label>
      </Toolbar>

      {canManage && (
        <form id="services-new-service" className="mx-4 mb-2 space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm" onSubmit={onSubmit}>
          <h2 className="text-lg font-semibold">{t('app.services.catalog.new_service.title')}</h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
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
                  placeholder={t('app.services.catalog.new_service.placeholders.cost_currency', { defaultValue: 'PLN' })}
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
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-slate-700">
                  {t('app.services.catalog.new_service.labels.execution_mode', { defaultValue: 'Исполнение' })}
                </label>
                <select
                  className="input mt-1"
                  value={formState.executionMode}
                  onChange={(e) =>
                    onFormChange({
                      ...formState,
                      executionMode: e.target.value === 'handoff' ? 'handoff' : 'inline',
                    })
                  }
                >
                  <option value="inline">{t('app.services.execution.inline', { defaultValue: 'Inline (в Services)' })}</option>
                  <option value="handoff">{t('app.services.execution.handoff', { defaultValue: 'Handoff (другой модуль)' })}</option>
                </select>
              </div>
              {formState.executionMode === 'handoff' ? (
                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    {t('app.services.catalog.new_service.labels.handoff_action', { defaultValue: 'Handoff action' })}
                  </label>
                  <input
                    className="input mt-1 font-mono text-sm"
                    value={formState.handoffAction}
                    onChange={(e) => onFormChange({ ...formState, handoffAction: e.target.value })}
                    placeholder="recruitment.create_search"
                  />
                </div>
              ) : null}
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-500">{t('app.services.catalog.new_service.hint')}</span>
            <button type="submit" className="btn-primary">
              {t('app.services.catalog.new_service.submit')}
            </button>
          </div>
          {message && <div className="text-sm text-brand-700">{message}</div>}
        </form>
      )}

      <DataTable
        columns={columns}
        rows={services}
        rowKey={(svc) => svc.id}
        loading={loading}
        rowClassName={(svc) => (!svc.is_active ? 'bg-slate-50' : undefined)}
        emptyState={
          <div className="flex flex-col items-center gap-3">
            <span>{t('app.services.catalog.table.empty')}</span>
            {onGoToOrders ? (
              <button type="button" className="btn-secondary btn-sm" onClick={onGoToOrders}>
                {t('app.services.catalog.table.empty_cta_orders', { defaultValue: 'Go to orders' })}
              </button>
            ) : null}
          </div>
        }
        ariaLabel={t('app.services.tabs.catalog', { defaultValue: 'Catalog' })}
      />
      {message && !canManage && <div className="mx-4 mt-2 text-sm text-brand-700">{message}</div>}
    </div>
  )
}
