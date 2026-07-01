import type { FormEvent } from 'react'

import type { AdditionalService } from '../../api/types'
import { useI18n } from '../../i18n'
import { formatAmount } from './utils'
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

      <div className="overflow-auto rounded-lg border border-slate-200">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50/90 text-left">
            <tr>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">{t('app.services.catalog.table.code')}</th>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">{t('app.services.catalog.table.name')}</th>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">{t('app.services.catalog.table.category')}</th>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">{t('app.services.catalog.table.price')}</th>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">
                {t('app.services.catalog.table.orders_count')}
              </th>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">
                {t('app.services.catalog.table.revenue_completed')}
              </th>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">{t('app.services.catalog.table.schedule')}</th>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">{t('app.services.catalog.table.candidate')}</th>
              <th className="border-b border-r border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600">{t('app.services.catalog.table.status')}</th>
              {canManage && <th className="border-b border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600" />}
            </tr>
          </thead>
          <tbody className="bg-white">
            {loading ? (
              <tr>
                <td colSpan={canManage ? 10 : 9} className="px-4 py-4 text-center text-slate-500">
                  {t('app.services.catalog.table.loading')}
                </td>
              </tr>
            ) : services.length === 0 ? (
              <tr>
                <td colSpan={canManage ? 10 : 9} className="px-4 py-6 text-center text-slate-500">
                  <div className="flex flex-col items-center gap-3">
                    <span>{t('app.services.catalog.table.empty')}</span>
                    {onGoToOrders ? (
                      <button type="button" className="btn-secondary btn-sm" onClick={onGoToOrders}>
                        {t('app.services.catalog.table.empty_cta_orders', { defaultValue: 'Go to orders' })}
                      </button>
                    ) : null}
                  </div>
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
                  <td className="border-r border-slate-200 px-4 py-2 tabular-nums">{svc.metrics_orders_count ?? 0}</td>
                  <td className="border-r border-slate-200 px-4 py-2 tabular-nums">
                    {formatAmount(svc.metrics_revenue_completed ?? 0)}
                  </td>
                  <td className="border-r border-slate-200 px-4 py-2">{svc.requires_schedule ? t('app.services.words.yes') : t('app.services.words.no')}</td>
                  <td className="border-r border-slate-200 px-4 py-2">{svc.requires_candidate ? t('app.services.words.yes') : t('app.services.words.no')}</td>
                  <td className="border-r border-slate-200 px-4 py-2">
                    <span
                      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${
                        svc.is_active ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {svc.is_active ? t('app.services.catalog.table.badges.active') : t('app.services.catalog.table.badges.archived')}
                    </span>
                  </td>
                  {canManage && (
                    <td className="px-4 py-2 text-right">
                      <button type="button" onClick={() => onToggleActive(svc)} className="btn-secondary btn-xs">
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
