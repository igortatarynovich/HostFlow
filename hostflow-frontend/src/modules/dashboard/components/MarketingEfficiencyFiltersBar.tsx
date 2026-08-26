import type { Dispatch, SetStateAction } from 'react'
import type { TranslateFn } from '../../../i18n'
import { DISPLAY_CURRENCIES, type DisplayCurrency } from '../../../api/fxRates'
import {
  MARKETING_CAMPAIGN_PRESETS,
  type MarketingCampaignPresetId,
} from '../marketingPresets'
import type { QuickRange } from '../types'

export type MarketingCampaignOption = {
  id: string
  label: string
}

export interface QuickRangeOption {
  value: QuickRange
  label: string
}

export interface MarketingEfficiencyFiltersBarProps {
  t: TranslateFn
  quickRangeOptions: QuickRangeOption[]
  activeRange: QuickRange | 'custom'
  applyQuickRange: (range: QuickRange) => void
  dateFrom: string
  setDateFrom: Dispatch<SetStateAction<string>>
  dateTo: string
  setDateTo: Dispatch<SetStateAction<string>>
  setActiveRange: Dispatch<SetStateAction<QuickRange | 'custom'>>
  selectedIds: string[]
  campaignOptions: MarketingCampaignOption[]
  onToggleCampaign: (id: string) => void
  onSelectAll: () => void
  onClearSelection: () => void
  onApplyPreset: (presetId: MarketingCampaignPresetId) => void
  activePreset: MarketingCampaignPresetId | null
  displayCurrency: DisplayCurrency
  onDisplayCurrencyChange: (currency: DisplayCurrency) => void
  fxAsOf: string | null
  fxProvider: string | null
  fxLoading: boolean
  loading: boolean
  selectedCount: number
  formatNumber: (value?: number) => string
}

export function MarketingEfficiencyFiltersBar({
  t,
  quickRangeOptions,
  activeRange,
  applyQuickRange,
  dateFrom,
  setDateFrom,
  dateTo,
  setDateTo,
  setActiveRange,
  selectedIds,
  campaignOptions,
  onToggleCampaign,
  onSelectAll,
  onClearSelection,
  onApplyPreset,
  activePreset,
  displayCurrency,
  onDisplayCurrencyChange,
  fxAsOf,
  fxProvider,
  fxLoading,
  loading,
  selectedCount,
  formatNumber,
}: MarketingEfficiencyFiltersBarProps) {
  const selectedSet = new Set(selectedIds)

  return (
    <div className="card space-y-3 p-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-0.5 text-xs">
          <span className="text-slate-500">{t('app.dashboard.filters.period')}</span>
          <div className="flex flex-wrap gap-1">
            {quickRangeOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                className={`rounded px-2 py-1 text-xs ${
                  activeRange === option.value
                    ? 'bg-brand-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
                onClick={() => applyQuickRange(option.value)}
                disabled={loading}
              >
                {option.label}
              </button>
            ))}
          </div>
        </label>

        <label className="flex flex-col gap-0.5 text-xs">
          <span className="text-slate-500">{t('app.dashboard.filters.from')}</span>
          <input
            type="date"
            className="input input-sm w-36"
            autoComplete="off"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value)
              setActiveRange('custom')
            }}
            disabled={loading}
          />
        </label>
        <label className="flex flex-col gap-0.5 text-xs">
          <span className="text-slate-500">{t('app.dashboard.filters.to')}</span>
          <input
            type="date"
            className="input input-sm w-36"
            autoComplete="off"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value)
              setActiveRange('custom')
            }}
            disabled={loading}
          />
        </label>

        <label className="flex flex-col gap-0.5 text-xs">
          <span className="text-slate-500">{t('app.dashboard.marketing.filters.currency')}</span>
          <div className="flex flex-wrap gap-1">
            {DISPLAY_CURRENCIES.map((code) => {
              const active = displayCurrency === code
              return (
                <button
                  key={code}
                  type="button"
                  className={`rounded px-3 py-1 text-xs font-semibold tabular-nums ${
                    active
                      ? 'bg-brand-600 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                  onClick={() => onDisplayCurrencyChange(code)}
                  disabled={loading || (fxLoading && code !== 'USD')}
                  aria-pressed={active}
                >
                  {code}
                </button>
              )
            })}
          </div>
          <span className="mt-0.5 text-[11px] text-slate-400">
            {fxLoading
              ? t('app.dashboard.marketing.fx.loading')
              : fxAsOf
                ? t('app.dashboard.marketing.fx.as_of', {
                    values: {
                      date: fxAsOf,
                      provider: fxProvider || 'NBP',
                    },
                  })
                : t('app.dashboard.marketing.fx.unavailable')}
          </span>
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-slate-500">
          {t('app.dashboard.marketing.filters.presets')}
        </span>
        {MARKETING_CAMPAIGN_PRESETS.map((preset) => {
          const active = activePreset === preset.id
          return (
            <button
              key={preset.id}
              type="button"
              className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                active
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
              onClick={() => onApplyPreset(preset.id)}
              disabled={loading}
            >
              {t(`app.dashboard.marketing.presets.${preset.id}`)}
            </button>
          )
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-slate-500">
          {t('app.dashboard.marketing.filters.campaigns')}
        </span>
        <button
          type="button"
          className="rounded px-2 py-1 text-xs text-brand-700 hover:bg-brand-50"
          onClick={onSelectAll}
          disabled={loading}
        >
          {t('app.dashboard.marketing.filters.select_all')}
        </button>
        <button
          type="button"
          className="rounded px-2 py-1 text-xs text-slate-600 hover:bg-slate-100"
          onClick={onClearSelection}
          disabled={loading}
        >
          {t('app.dashboard.marketing.filters.clear')}
        </button>
        <span className="ml-auto text-xs text-slate-500">
          {loading
            ? t('app.dashboard.refresh.loading')
            : t('app.dashboard.marketing.filters.selected', {
                values: {
                  count: formatNumber(selectedCount),
                  total: formatNumber(campaignOptions.length),
                },
              })}
          {dateFrom && dateTo ? (
            <span className="ml-2">
              • {dateFrom} — {dateTo}
            </span>
          ) : null}
        </span>
      </div>

      <div
        className="max-h-44 space-y-1 overflow-y-auto rounded-lg border border-slate-100 bg-slate-50/80 p-2"
        role="group"
        aria-label={t('app.dashboard.marketing.filters.campaigns')}
      >
        {campaignOptions.length === 0 ? (
          <p className="px-1 py-2 text-xs text-slate-500">
            {t('app.dashboard.marketing.empty_campaigns')}
          </p>
        ) : (
          campaignOptions.map((opt) => {
            const checked = selectedSet.has(opt.id)
            return (
              <label
                key={opt.id}
                className="flex cursor-pointer items-start gap-2 rounded px-2 py-1 text-sm hover:bg-white"
              >
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={checked}
                  onChange={() => onToggleCampaign(opt.id)}
                  disabled={loading}
                />
                <span className="min-w-0 flex-1 leading-tight text-slate-800">{opt.label}</span>
              </label>
            )
          })
        )}
      </div>
    </div>
  )
}
