import type { Dispatch, SetStateAction } from 'react'
import type { TranslateFn } from '../../../i18n'
import type { QuickRange } from '../types'

export interface FilterOption {
  id: string
  label: string
}

export interface QuickRangeOption {
  value: QuickRange
  label: string
}

export interface RecruitmentEfficiencyFiltersBarProps {
  t: TranslateFn
  quickRangeOptions: QuickRangeOption[]
  activeRange: QuickRange | 'custom'
  applyQuickRange: (range: QuickRange) => void
  dateFrom: string
  setDateFrom: Dispatch<SetStateAction<string>>
  dateTo: string
  setDateTo: Dispatch<SetStateAction<string>>
  setActiveRange: Dispatch<SetStateAction<QuickRange | 'custom'>>
  companyFilter: string
  companyOptions: FilterOption[]
  onCompanyChange: (value: string) => void
  vacancyFilter: string
  vacancyOptions: FilterOption[]
  onVacancyChange: (value: string) => void
  loading: boolean
  periodTotal: number
  formatNumber: (value?: number) => string
}

export function RecruitmentEfficiencyFiltersBar({
  t,
  quickRangeOptions,
  activeRange,
  applyQuickRange,
  dateFrom,
  setDateFrom,
  dateTo,
  setDateTo,
  setActiveRange,
  companyFilter,
  companyOptions,
  onCompanyChange,
  vacancyFilter,
  vacancyOptions,
  onVacancyChange,
  loading,
  periodTotal,
  formatNumber,
}: RecruitmentEfficiencyFiltersBarProps) {
  return (
    <div className="card space-y-3 p-4">
      <div className="flex flex-wrap items-end gap-3 gap-y-2">
        <label className="flex flex-col gap-0.5 text-xs">
          <span className="text-slate-500">{t('app.dashboard.efficiency.filters.client')}</span>
          <select
            className="input input-sm min-w-[180px]"
            value={companyFilter}
            onChange={(e) => onCompanyChange(e.target.value)}
          >
            <option value="">{t('app.dashboard.efficiency.filters.all_clients')}</option>
            {companyOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>

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
          />
        </label>

        <label className="flex flex-col gap-0.5 text-xs">
          <span className="text-slate-500">{t('app.dashboard.filters.vacancy')}</span>
          <select
            className="input input-sm min-w-[200px]"
            value={vacancyFilter}
            onChange={(e) => onVacancyChange(e.target.value)}
          >
            <option value="">{t('app.dashboard.filters.all_vacancies')}</option>
            {vacancyOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="flex items-center justify-between border-t border-slate-100 pt-2 text-xs text-slate-500">
        <span>
          {t('app.dashboard.filters.sample', { values: { count: formatNumber(periodTotal) } })}
          {dateFrom && dateTo ? (
            <span className="ml-2">
              • {dateFrom} — {dateTo}
            </span>
          ) : null}
        </span>
        {loading ? <span>{t('common.loading')}</span> : null}
      </div>
    </div>
  )
}
