import type { LegacyRef } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { TranslateFn } from '../../../i18n'
import { CRM_APP_PATHS } from '../../../app/crmAppPaths'
import { toCSV } from '../../candidates/candidateUtils'
import type { DashboardWidgetId, PivotDimension } from '../types'

export interface PivotRow {
  key: string
  total: number
  breakdown: Record<string, number>
  filterParams: Record<string, string>
}

export interface PivotData {
  rows: PivotRow[]
  secondaryKeys: string[]
}

export interface DimensionOption {
  value: PivotDimension
  label: string
}

interface DashboardPivotPanelsProps {
  t: TranslateFn
  formatNumber: (n: number) => string
  isWidgetVisible: (widgetId: DashboardWidgetId) => boolean
  pivotPrimary: PivotDimension
  pivotSecondary: PivotDimension | 'none'
  setPivotPrimary: (v: PivotDimension) => void
  setPivotSecondary: (v: PivotDimension | 'none') => void
  pivotData: PivotData
  dimensionOptions: DimensionOption[]
  primaryLabel: string
  secondaryLabel: string
  pivotChartContainerRef: LegacyRef<HTMLDivElement>
  isPivotChartContainerReady: boolean
}

export function DashboardPivotPanels({
  t,
  formatNumber,
  isWidgetVisible,
  pivotPrimary,
  pivotSecondary,
  setPivotPrimary,
  setPivotSecondary,
  pivotData,
  dimensionOptions,
  primaryLabel,
  secondaryLabel,
  pivotChartContainerRef,
  isPivotChartContainerReady,
}: DashboardPivotPanelsProps) {
  return (
    <>
      {isWidgetVisible('pivot') && (
        <div className="border-t border-slate-100 pt-4 mt-2 sm:border-0 sm:pt-0">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <div className="text-sm font-semibold">{t('app.dashboard.pivot.title')}</div>
              <div className="text-xs text-slate-500">
                {primaryLabel}
                {pivotSecondary !== 'none' && ` → ${secondaryLabel}`}
              </div>
            </div>
            <div className="flex flex-wrap gap-3 text-sm items-end">
              <label className="flex flex-col gap-1">
                {t('app.dashboard.pivot.group_by')}
                <select
                  className="input text-sm"
                  value={pivotPrimary}
                  onChange={(e) => setPivotPrimary(e.target.value as PivotDimension)}
                >
                  {dimensionOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1">
                {t('app.dashboard.pivot.subgroup')}
                <select
                  className="input text-sm"
                  value={pivotSecondary}
                  onChange={(e) => setPivotSecondary((e.target.value || 'none') as PivotDimension | 'none')}
                >
                  <option value="none">{t('app.dashboard.labels.no_subgroup')}</option>
                  {dimensionOptions.map((option) => (
                    <option key={`sec-${option.value}`} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              {pivotData.rows.length > 0 && (
                <button
                  type="button"
                  className="btn-secondary text-sm"
                  onClick={() => {
                    const headers = [
                      { key: 'key', title: primaryLabel },
                      ...pivotData.secondaryKeys.map((k) => ({ key: k, title: k })),
                      { key: 'total', title: t('app.dashboard.pivot.total') },
                    ]
                    const rows = pivotData.rows.map((row) => ({
                      key: row.key,
                      ...Object.fromEntries(pivotData.secondaryKeys.map((k) => [k, row.breakdown[k] ?? 0])),
                      total: row.total,
                    }))
                    const csv = toCSV(rows, headers)
                    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = `dashboard_pivot_${new Date().toISOString().slice(0, 10)}.csv`
                    a.click()
                    URL.revokeObjectURL(url)
                  }}
                >
                  {t('app.dashboard.pivot.export')}
                </button>
              )}
            </div>
          </div>
          {pivotData.rows.length ? (
            <div className="overflow-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-slate-500">
                    <th className="py-2 pr-4">{primaryLabel}</th>
                    {pivotData.secondaryKeys.map((key) => (
                      <th key={`sec-head-${key}`} className="py-2 pr-4 text-right">
                        {key}
                      </th>
                    ))}
                    <th className="py-2 text-right">{t('app.dashboard.pivot.total')}</th>
                  </tr>
                </thead>
                <tbody>
                  {pivotData.rows.map((row) => {
                    const params =
                      row.filterParams && Object.keys(row.filterParams).length > 0
                        ? new URLSearchParams(row.filterParams).toString()
                        : ''
                    const href = params ? `${CRM_APP_PATHS.candidates}?${params}` : null
                    return (
                      <tr key={`pivot-${row.key}`} className="border-t border-slate-100">
                        <td className="py-2 pr-4 whitespace-nowrap">
                          {href ? (
                            <Link to={href} className="text-brand-600 hover:underline">
                              {row.key}
                            </Link>
                          ) : (
                            row.key
                          )}
                        </td>
                        {pivotSecondary !== 'none' &&
                          pivotData.secondaryKeys.map((key) => (
                            <td key={`sec-${row.key}-${key}`} className="py-2 pr-4 text-right">
                              {formatNumber(row.breakdown[key] ?? 0)}
                            </td>
                          ))}
                        {pivotSecondary === 'none' && (
                          <td className="py-2 pr-4 text-right">{formatNumber(row.total)}</td>
                        )}
                        {pivotSecondary !== 'none' && (
                          <td className="py-2 text-right font-semibold">
                            {formatNumber(row.total)}
                          </td>
                        )}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-sm text-slate-500">{t('app.dashboard.pivot.empty')}</div>
          )}
        </div>
      )}

      {isWidgetVisible('pivotChart') && pivotData.rows.length > 0 && (
        <div className="card min-w-0 p-4 space-y-3">
          <div>
            <div className="text-sm font-semibold">{t('app.dashboard.pivot.chart_title')}</div>
            <div className="text-xs text-slate-500">
              {primaryLabel}
              {pivotSecondary !== 'none' && ` × ${secondaryLabel}`}
            </div>
          </div>
          <div ref={pivotChartContainerRef} className="h-64 w-full min-w-0 shrink-0 overflow-hidden">
            {isPivotChartContainerReady ? (
              <ResponsiveContainer width="100%" height={256} minHeight={200} minWidth={0}>
                <BarChart
                  data={pivotData.rows.slice(0, 15).map((r) => ({
                    name: r.key.length > 20 ? r.key.slice(0, 18) + '…' : r.key,
                    total: r.total,
                    ...(pivotSecondary !== 'none' && pivotData.secondaryKeys.length > 0
                      ? Object.fromEntries(
                          pivotData.secondaryKeys.slice(0, 5).map((k) => [k, r.breakdown[k] ?? 0]),
                        )
                      : {}),
                  }))}
                  margin={{ top: 8, right: 8, left: 0, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v) => (v?.length > 12 ? v.slice(0, 10) + '…' : v)}
                  />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={((v: number) => formatNumber(v)) as never} />
                  {pivotSecondary === 'none' ? (
                    <Bar dataKey="total" fill="rgb(99 102 241)" radius={[4, 4, 0, 0]} />
                  ) : (
                    pivotData.secondaryKeys.slice(0, 5).map((key, i) => {
                      const colors = [
                        'rgb(99 102 241)',
                        'rgb(34 197 94)',
                        'rgb(234 179 8)',
                        'rgb(239 68 68)',
                        'rgb(168 85 247)',
                      ]
                      return (
                        <Bar
                          key={key}
                          dataKey={key}
                          fill={colors[i % colors.length]}
                          stackId="stack"
                          radius={i === pivotData.secondaryKeys.length - 1 ? [4, 4, 0, 0] : 0}
                        />
                      )
                    })
                  )}
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-64 items-center justify-center text-xs text-slate-500">
                {t('common.loading')}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
