import type { Dispatch, SetStateAction } from 'react'
import type { TranslateFn } from '../../../i18n'
import {
  DASHBOARD_WIDGET_CATALOG,
  type DashboardFilterId,
  type DashboardWidgetId,
} from '../types'
import type { LoadOverrides, QuickRange } from '../types'

export interface FilterOption {
  id: string
  label: string
}

export interface StageOption {
  code: string
  label: string
}

export interface QuickRangeOption {
  value: QuickRange
  label: string
}

export interface DashboardFiltersBarProps {
  t: TranslateFn
  isFilterVisible: (id: DashboardFilterId) => boolean

  quickRangeOptions: QuickRangeOption[]
  activeRange: QuickRange | 'custom'
  applyQuickRange: (range: QuickRange) => void

  dateFrom: string
  setDateFrom: Dispatch<SetStateAction<string>>
  dateTo: string
  setDateTo: Dispatch<SetStateAction<string>>
  setActiveRange: Dispatch<SetStateAction<QuickRange | 'custom'>>

  dateField: 'created' | 'updated'
  setDateField: Dispatch<SetStateAction<'created' | 'updated'>>
  load: (overrides?: LoadOverrides) => void

  vacancyFilter: string
  vacancyOptions: FilterOption[]
  handleVacancyChange: (value: string) => void

  companyFilter: string
  companyOptions: FilterOption[]
  handleCompanyChange: (value: string) => void

  managerFilter: string
  managerOptions: FilterOption[]
  handleManagerChange: (value: string) => void

  candidateFilter: string
  setCandidateFilter: Dispatch<SetStateAction<string>>
  handleCandidateFilterApply: (raw: string) => void

  stagesFilter: string[]
  stageOptions: StageOption[]
  handleStagesChange: (codes: string[]) => void

  stageView: 'all' | 'agency' | 'client'
  setStageView: Dispatch<SetStateAction<'all' | 'agency' | 'client'>>
  isClientRole: boolean

  compareWithPrevious: boolean
  setCompareWithPrevious: Dispatch<SetStateAction<boolean>>

  handleResetFilters: () => void
  handleSavePreset: () => void
  handleLoadPreset: () => void
  savedPreset: Record<string, unknown> | null

  visibleWidgets: Set<string>
  toggleWidget: (id: DashboardWidgetId) => void

  visibleFilters: Set<string>
  toggleFilter: (id: DashboardFilterId) => void

  loading: boolean
  periodTotal: number
  formatNumber: (value?: number) => string
}

const ALL_FILTER_IDS: DashboardFilterId[] = [
  'period',
  'dateRange',
  'dateField',
  'vacancy',
  'company',
  'manager',
  'candidate',
  'stages',
  'compare',
  'presets',
  'widgets',
]

export function DashboardFiltersBar(props: DashboardFiltersBarProps) {
  const {
    t,
    isFilterVisible,
    quickRangeOptions,
    activeRange,
    applyQuickRange,
    dateFrom,
    setDateFrom,
    dateTo,
    setDateTo,
    setActiveRange,
    dateField,
    setDateField,
    load,
    vacancyFilter,
    vacancyOptions,
    handleVacancyChange,
    companyFilter,
    companyOptions,
    handleCompanyChange,
    managerFilter,
    managerOptions,
    handleManagerChange,
    candidateFilter,
    setCandidateFilter,
    handleCandidateFilterApply,
    stagesFilter,
    stageOptions,
    handleStagesChange,
    stageView,
    setStageView,
    isClientRole,
    compareWithPrevious,
    setCompareWithPrevious,
    handleResetFilters,
    handleSavePreset,
    handleLoadPreset,
    savedPreset,
    visibleWidgets,
    toggleWidget,
    visibleFilters,
    toggleFilter,
    loading,
    periodTotal,
    formatNumber,
  } = props

  return (
    <div className="card p-4 space-y-4">
      <div className="flex flex-wrap items-end gap-3 gap-y-2">
        {isFilterVisible('period') && (
          <label className="flex flex-col text-xs gap-0.5">
            <span className="text-slate-500">{t('app.dashboard.filters.period')}</span>
            <div className="flex gap-1">
              {quickRangeOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={`px-2 py-1 rounded text-xs ${
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
        )}
        {isFilterVisible('dateRange') && (
          <>
            <label className="flex flex-col text-xs gap-0.5">
              <span className="text-slate-500">{t('app.dashboard.filters.from')}</span>
              <input
                type="date"
                className="input input-sm w-32"
                autoComplete="off"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value)
                  setActiveRange('custom')
                }}
              />
            </label>
            <label className="flex flex-col text-xs gap-0.5">
              <span className="text-slate-500">{t('app.dashboard.filters.to')}</span>
              <input
                type="date"
                className="input input-sm w-32"
                autoComplete="off"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value)
                  setActiveRange('custom')
                }}
              />
            </label>
          </>
        )}
        {isFilterVisible('dateField') && (
          <label className="flex flex-col text-xs gap-0.5">
            <span className="text-slate-500">{t('app.dashboard.filters.date_field')}</span>
            <select
              className="input input-sm w-28"
              value={dateField}
              onChange={(e) => {
                const next = e.target.value === 'updated' ? 'updated' : 'created'
                setDateField(next)
                load({ field: next })
              }}
            >
              <option value="created">{t('app.dashboard.filters.field_created')}</option>
              <option value="updated">{t('app.dashboard.filters.field_updated')}</option>
            </select>
          </label>
        )}
        {isFilterVisible('vacancy') && (
          <label className="flex flex-col text-xs gap-0.5">
            <span className="text-slate-500">{t('app.dashboard.filters.vacancy')}</span>
            <select
              className="input input-sm w-40"
              value={vacancyFilter}
              onChange={(e) => handleVacancyChange(e.target.value)}
            >
              <option value="">{t('app.dashboard.filters.all_vacancies')}</option>
              {vacancyOptions.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        )}
        {isFilterVisible('company') && (
          <label className="flex flex-col text-xs gap-0.5">
            <span className="text-slate-500">{t('app.dashboard.filters.company')}</span>
            <select
              className="input input-sm w-40"
              value={companyFilter}
              onChange={(e) => handleCompanyChange(e.target.value)}
            >
              <option value="">{t('app.dashboard.filters.all_companies')}</option>
              {companyOptions.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        )}
        {isFilterVisible('manager') && (
          <label className="flex flex-col text-xs gap-0.5">
            <span className="text-slate-500">{t('app.dashboard.filters.manager')}</span>
            <select
              className="input input-sm w-40"
              value={managerFilter}
              onChange={(e) => handleManagerChange(e.target.value)}
            >
              <option value="">{t('app.dashboard.filters.all_managers')}</option>
              {managerOptions.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        )}
        {isFilterVisible('candidate') && (
          <label className="flex flex-col text-xs gap-0.5">
            <span className="text-slate-500">{t('app.dashboard.filters.candidate')}</span>
            <input
              type="text"
              className="input input-sm w-44 font-mono"
              value={candidateFilter}
              onChange={(e) => setCandidateFilter(e.target.value)}
              onBlur={(e) => handleCandidateFilterApply(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  handleCandidateFilterApply((e.target as HTMLInputElement).value)
                  ;(e.target as HTMLInputElement).blur()
                }
              }}
              placeholder={t('app.dashboard.filters.candidate_placeholder')}
              autoComplete="off"
            />
          </label>
        )}
        {isFilterVisible('stages') && (
          <label className="flex flex-col text-xs gap-0.5">
            <span className="text-slate-500">{t('app.dashboard.filters.stages')}</span>
            <select
              className="input input-sm w-32"
              multiple
              size={2}
              value={stagesFilter}
              onChange={(e) => {
                const selected = Array.from(e.target.selectedOptions, (o) => o.value)
                handleStagesChange(selected)
              }}
            >
              {stageOptions.map((opt) => (
                <option key={opt.code} value={opt.code}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="flex flex-col text-xs gap-0.5">
          <span className="text-slate-500">{t('app.dashboard.filters.stage_view')}</span>
          <select
            className="input input-sm w-32"
            value={stageView}
            onChange={(e) =>
              setStageView((e.target.value as 'all' | 'agency' | 'client') || 'all')
            }
          >
            {!isClientRole && (
              <option value="all">{t('app.dashboard.filters.stage_view_all')}</option>
            )}
            {!isClientRole && (
              <option value="agency">{t('app.dashboard.filters.stage_view_agency')}</option>
            )}
            <option value="client">{t('app.dashboard.filters.stage_view_client')}</option>
            {isClientRole && (
              <option value="all">{t('app.dashboard.filters.stage_view_all')}</option>
            )}
          </select>
        </label>
        {isFilterVisible('compare') && (
          <label className="flex items-center gap-2 text-xs cursor-pointer py-1">
            <input
              type="checkbox"
              checked={compareWithPrevious}
              onChange={(e) => {
                const v = e.target.checked
                setCompareWithPrevious(v)
                load({ compare: v })
              }}
            />
            <span className="text-slate-600">{t('app.dashboard.filters.compare_previous')}</span>
          </label>
        )}
        {isFilterVisible('presets') && (
          <div className="flex items-center gap-1 ml-2">
            <button type="button" className="btn-secondary btn-sm text-xs" onClick={handleResetFilters}>
              {t('app.dashboard.filters.reset')}
            </button>
            <button type="button" className="btn-secondary btn-sm text-xs" onClick={handleSavePreset}>
              {t('app.dashboard.filters.save_preset')}
            </button>
            <button
              type="button"
              className="btn-secondary btn-sm text-xs"
              onClick={handleLoadPreset}
              disabled={!savedPreset}
              title={savedPreset ? '' : t('app.dashboard.filters.no_preset')}
            >
              {t('app.dashboard.filters.load_preset')}
            </button>
          </div>
        )}
        {isFilterVisible('widgets') && (
          <details className="relative group ml-auto">
            <summary className="btn-secondary btn-sm cursor-pointer list-none text-xs">
              {t('app.dashboard.filters.widgets')}
            </summary>
            <div className="absolute right-0 top-full mt-1 z-20 bg-white border border-slate-200 rounded-lg shadow-lg py-2 min-w-[180px] max-h-[280px] overflow-y-auto">
              {DASHBOARD_WIDGET_CATALOG.map((id) => (
                <label
                  key={id}
                  className="flex items-center gap-2 px-3 py-1.5 hover:bg-slate-50 cursor-pointer text-sm"
                >
                  <input
                    type="checkbox"
                    checked={visibleWidgets.has(id)}
                    onChange={() => toggleWidget(id)}
                  />
                  {t(`app.dashboard.widgets.labels.${id}`)}
                </label>
              ))}
            </div>
          </details>
        )}
        <details className="relative group">
          <summary className="btn-secondary btn-sm cursor-pointer list-none text-xs text-slate-500">
            {t('app.dashboard.filters.configure')}
          </summary>
          <div className="absolute left-0 top-full mt-1 z-20 bg-white border border-slate-200 rounded-lg shadow-lg py-2 min-w-[180px] max-h-[280px] overflow-y-auto">
            {ALL_FILTER_IDS.map((fid) => (
              <label
                key={fid}
                className="flex items-center gap-2 px-3 py-1.5 hover:bg-slate-50 cursor-pointer text-sm"
              >
                <input
                  type="checkbox"
                  checked={visibleFilters.has(fid)}
                  onChange={() => toggleFilter(fid)}
                />
                {t(`app.dashboard.filters.labels.${fid}`)}
              </label>
            ))}
          </div>
        </details>
      </div>
      <div className="flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-2">
        <span>
          {t('app.dashboard.filters.sample', { values: { count: formatNumber(periodTotal) } })}
          {dateFrom && dateTo && (
            <span className="ml-2"> • {dateFrom} — {dateTo}</span>
          )}
        </span>
        {loading && <span>{t('common.loading')}</span>}
      </div>
    </div>
  )
}
