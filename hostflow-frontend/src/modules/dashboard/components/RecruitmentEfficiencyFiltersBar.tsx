import type { Dispatch, SetStateAction } from 'react'
import { AnalyticsFilterBar } from '../../../components/analytics'
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
    <AnalyticsFilterBar
      periodLabel={t('app.dashboard.filters.period')}
      quickRanges={quickRangeOptions}
      activeRange={activeRange}
      onQuickRange={applyQuickRange}
      fromLabel={t('app.dashboard.filters.from')}
      toLabel={t('app.dashboard.filters.to')}
      dateFrom={dateFrom}
      dateTo={dateTo}
      onDateFrom={(value) => {
        setDateFrom(value)
        setActiveRange('custom')
      }}
      onDateTo={(value) => {
        setDateTo(value)
        setActiveRange('custom')
      }}
      dimensions={[
        {
          id: 'client',
          label: t('app.dashboard.efficiency.filters.client'),
          value: companyFilter,
          options: companyOptions,
          allLabel: t('app.dashboard.efficiency.filters.all_clients'),
          onChange: onCompanyChange,
        },
        {
          id: 'vacancy',
          label: t('app.dashboard.filters.vacancy'),
          value: vacancyFilter,
          options: vacancyOptions,
          allLabel: t('app.dashboard.filters.all_vacancies'),
          onChange: onVacancyChange,
        },
      ]}
      sampleText={`${t('app.dashboard.filters.sample', { values: { count: formatNumber(periodTotal) } })}${
        dateFrom && dateTo ? ` • ${dateFrom} — ${dateTo}` : ''
      }`}
      loading={loading}
      loadingLabel={t('common.loading')}
    />
  )
}
