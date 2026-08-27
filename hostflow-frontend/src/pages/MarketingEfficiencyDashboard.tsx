import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  convertWithRates,
  getFxRates,
  type DisplayCurrency,
  type FxRatesResponse,
} from '../api/fxRates'
import {
  getCampaignPortfolio,
  listCampaigns,
  type CampaignPortfolio,
  type PortfolioCampaignRow,
} from '../api/platformCampaigns'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { useI18n } from '../i18n'
import { formatAnalyticsLoadError } from '../modules/dashboard/analyticsLoad'
import { MarketingEfficiencyFiltersBar } from '../modules/dashboard/components/MarketingEfficiencyFiltersBar'
import {
  MarketingEfficiencyPanel,
  type MarketingCampaignMetric,
  type MarketingDaySeriesPoint,
  type MarketingTotals,
} from '../modules/dashboard/components/MarketingEfficiencyPanel'
import { QUICK_RANGE_OPTIONS } from '../modules/dashboard/constants'
import {
  campaignIdsForPreset,
  parseMetaAdsExtras,
  type MarketingCampaignPresetId,
} from '../modules/dashboard/marketingPresets'
import type { QuickRange } from '../modules/dashboard/types'
import { calcRange } from '../modules/dashboard/utils'

const FX_STORAGE_KEY = 'hf:marketing:display_currency'

function parseMoney(raw?: string | null): number {
  if (raw == null || raw === '') return 0
  const n = Number(String(raw).replace(',', '.'))
  return Number.isFinite(n) ? n : 0
}

function readStoredCurrency(): DisplayCurrency {
  try {
    const raw = String(localStorage.getItem(FX_STORAGE_KEY) || '')
      .trim()
      .toUpperCase()
    if (raw === 'PLN' || raw === 'EUR' || raw === 'USD') return raw
  } catch {
    // ignore
  }
  return 'USD'
}

function recomputeTotals(
  rows: MarketingCampaignMetric[],
  currency: string | null,
): MarketingTotals {
  const spend = rows.reduce((s, r) => s + r.spend, 0)
  const leads = rows.reduce((s, r) => s + r.leads, 0)
  const impressionsParts = rows.map((r) => r.impressions)
  const reachParts = rows.map((r) => r.reach)
  const hasImp = impressionsParts.some((v) => v != null)
  const hasReach = reachParts.some((v) => v != null)
  return {
    spend,
    leads,
    cost_per_lead: leads > 0 ? spend / leads : null,
    impressions: hasImp ? impressionsParts.reduce((s, v) => s + (v ?? 0), 0) : null,
    reach: hasReach ? reachParts.reduce((s, v) => s + (v ?? 0), 0) : null,
    currency,
  }
}

function withBestCpl(rows: MarketingCampaignMetric[]): MarketingCampaignMetric[] {
  let best: number | null = null
  for (const r of rows) {
    if (r.cost_per_lead != null && r.leads > 0) {
      if (best == null || r.cost_per_lead < best) best = r.cost_per_lead
    }
  }
  return rows.map((r) => ({
    ...r,
    is_best_cpl: best != null && r.cost_per_lead != null && r.cost_per_lead === best,
  }))
}

/**
 * Marketing-owned Overview tab: Acquisition portfolio KPIs with multi-select + presets.
 * Mirrors Recruitment efficiency chrome; metrics stay Acquisition-owned (Stage 6).
 */
export default function MarketingEfficiencyDashboard() {
  const { t, locale } = useI18n()
  const loadSeq = useRef(0)

  const initialRange = calcRange('all')
  const [dateFrom, setDateFrom] = useState(initialRange.from)
  const [dateTo, setDateTo] = useState(initialRange.to)
  const [activeRange, setActiveRange] = useState<QuickRange | 'custom'>('all')

  const [loading, setLoading] = useState(true)
  const [errText, setErrText] = useState<string | null>(null)
  const [portfolio, setPortfolio] = useState<CampaignPortfolio | null>(null)
  const [extrasById, setExtrasById] = useState<
    Record<string, { impressions: number | null; reach: number | null }>
  >({})
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [activePreset, setActivePreset] = useState<MarketingCampaignPresetId | null>(null)
  const [initializedSelection, setInitializedSelection] = useState(false)
  const [displayCurrency, setDisplayCurrency] = useState<DisplayCurrency>(() => readStoredCurrency())
  const [fxRates, setFxRates] = useState<FxRatesResponse | null>(null)
  const [fxLoading, setFxLoading] = useState(true)
  const [fxError, setFxError] = useState(false)

  const numberFormatter = useMemo(
    () =>
      new Intl.NumberFormat(locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : 'en-US'),
    [locale],
  )
  const formatNumber = useCallback(
    (value?: number) => numberFormatter.format(value ?? 0),
    [numberFormatter],
  )
  const formatMoney = useCallback(
    (value?: number | null, currency?: string | null) => {
      if (value == null || !Number.isFinite(value)) return '—'
      try {
        return new Intl.NumberFormat(locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : 'en-US', {
          style: 'currency',
          currency: currency || 'USD',
          maximumFractionDigits: 2,
        }).format(value)
      } catch {
        return `${numberFormatter.format(value)} ${currency || 'USD'}`
      }
    },
    [locale, numberFormatter],
  )

  const quickRangeOptions = useMemo(
    () =>
      QUICK_RANGE_OPTIONS.map((value) => ({
        value,
        label: t(`app.dashboard.ranges.${value}`),
      })),
    [t],
  )

  const rangeInvalid = Boolean(dateFrom && dateTo && dateFrom > dateTo)

  const loadFx = useCallback(async () => {
    setFxLoading(true)
    setFxError(false)
    try {
      const rates = await getFxRates()
      setFxRates(rates)
    } catch {
      setFxRates(null)
      setFxError(true)
      // Keep USD selectable even if FX feed fails.
      setDisplayCurrency((prev) => (prev === 'USD' ? prev : 'USD'))
    } finally {
      setFxLoading(false)
    }
  }, [])

  const load = useCallback(async () => {
    if (dateFrom && dateTo && dateFrom > dateTo) {
      setErrText(t('app.dashboard.errors.range_invalid'))
      return
    }

    const seq = ++loadSeq.current
    setLoading(true)
    setErrText(null)
    try {
      const portfolioParams =
        dateFrom || dateTo
          ? {
              ...(dateFrom ? { date_from: dateFrom } : {}),
              ...(dateTo ? { date_to: dateTo } : {}),
            }
          : undefined
      const [folio, campaigns] = await Promise.all([
        getCampaignPortfolio(100, portfolioParams),
        listCampaigns({ limit: 100 }).catch(() => []),
      ])
      if (seq !== loadSeq.current) return

      const extras: Record<string, { impressions: number | null; reach: number | null }> = {}
      for (const c of campaigns) {
        extras[c.id] = parseMetaAdsExtras(c.description)
      }
      setPortfolio(folio)
      setExtrasById(extras)
      if (!initializedSelection) {
        setSelectedIds(folio.campaigns.map((r) => r.campaign_id))
        setInitializedSelection(true)
      }
    } catch (e: unknown) {
      if (seq !== loadSeq.current) return
      setErrText(formatAnalyticsLoadError(e, t))
    } finally {
      if (seq === loadSeq.current) setLoading(false)
    }
  }, [dateFrom, dateTo, initializedSelection, t])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    void loadFx()
  }, [loadFx])

  const sourceCurrency = (portfolio?.currency || 'USD').toUpperCase()

  const allRowsNative: MarketingCampaignMetric[] = useMemo(() => {
    const campaigns: PortfolioCampaignRow[] = portfolio?.campaigns ?? []
    const mapped = campaigns.map((r) => {
      const spend = parseMoney(r.spend)
      const leads = r.leads ?? 0
      const cpl =
        r.cost_per_lead != null && r.cost_per_lead !== ''
          ? parseMoney(r.cost_per_lead)
          : leads > 0
            ? spend / leads
            : null
      const ex = extrasById[r.campaign_id] || { impressions: null, reach: null }
      return {
        campaign_id: r.campaign_id,
        name: r.name,
        spend,
        leads,
        cost_per_lead: cpl,
        impressions: r.impressions != null ? r.impressions : ex.impressions,
        reach: r.reach != null ? r.reach : ex.reach,
        is_best_cpl: Boolean(r.is_best_cpl),
      }
    })
    return withBestCpl(mapped)
  }, [portfolio, extrasById])

  const allRows: MarketingCampaignMetric[] = useMemo(() => {
    if (displayCurrency === sourceCurrency || !fxRates) {
      return allRowsNative
    }
    const converted = allRowsNative.map((r) => {
      const spend = convertWithRates(r.spend, sourceCurrency, displayCurrency, fxRates)
      const cpl =
        r.cost_per_lead != null
          ? convertWithRates(r.cost_per_lead, sourceCurrency, displayCurrency, fxRates)
          : r.leads > 0
            ? spend / r.leads
            : null
      return { ...r, spend, cost_per_lead: cpl }
    })
    return withBestCpl(converted)
  }, [allRowsNative, displayCurrency, fxRates, sourceCurrency])

  const campaignOptions = useMemo(
    () =>
      allRows
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name))
        .map((r) => ({ id: r.campaign_id, label: r.name })),
    [allRows],
  )

  useEffect(() => {
    if (!initializedSelection || allRows.length === 0) return
    const valid = new Set(allRows.map((r) => r.campaign_id))
    setSelectedIds((prev) => {
      const next = prev.filter((id) => valid.has(id))
      if (next.length === prev.length && next.every((id, i) => id === prev[i])) return prev
      return next.length ? next : allRows.map((r) => r.campaign_id)
    })
  }, [allRows, initializedSelection])

  const selectedRows = useMemo(() => {
    if (selectedIds.length === 0) return []
    const set = new Set(selectedIds)
    return withBestCpl(allRows.filter((r) => set.has(r.campaign_id)))
  }, [allRows, selectedIds])

  const totals = useMemo(
    () => recomputeTotals(selectedRows, displayCurrency),
    [selectedRows, displayCurrency],
  )

  const series: MarketingDaySeriesPoint[] = useMemo(() => {
    const points = portfolio?.series_by_campaign ?? []
    if (!points.length || selectedIds.length === 0) return []
    const selected = new Set(selectedIds)
    const byDay = new Map<string, MarketingDaySeriesPoint>()
    for (const p of points) {
      if (!selected.has(p.campaign_id)) continue
      const spendNative = parseMoney(p.spend)
      const spend =
        displayCurrency === sourceCurrency || !fxRates
          ? spendNative
          : convertWithRates(spendNative, sourceCurrency, displayCurrency, fxRates)
      const prev = byDay.get(p.day) || {
        day: p.day,
        spend: 0,
        leads: 0,
        impressions: 0,
        reach: 0,
      }
      prev.spend += spend
      prev.leads += p.leads ?? 0
      prev.impressions += p.impressions ?? 0
      prev.reach += p.reach ?? 0
      byDay.set(p.day, prev)
    }
    return [...byDay.values()].sort((a, b) => a.day.localeCompare(b.day))
  }, [portfolio?.series_by_campaign, selectedIds, displayCurrency, sourceCurrency, fxRates])

  const applyQuickRange = (range: QuickRange) => {
    const next = calcRange(range)
    setActiveRange(range)
    setDateFrom(next.from)
    setDateTo(next.to)
  }

  const onToggleCampaign = (id: string) => {
    setActivePreset(null)
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const onSelectAll = () => {
    setActivePreset(null)
    setSelectedIds(allRows.map((r) => r.campaign_id))
  }

  const onClearSelection = () => {
    setActivePreset(null)
    setSelectedIds([])
  }

  const onApplyPreset = (presetId: MarketingCampaignPresetId) => {
    const ids = campaignIdsForPreset(allRows, presetId)
    setActivePreset(presetId)
    setSelectedIds(ids)
  }

  const onDisplayCurrencyChange = (currency: DisplayCurrency) => {
    if (currency !== 'USD' && !fxRates) return
    setDisplayCurrency(currency)
    try {
      localStorage.setItem(FX_STORAGE_KEY, currency)
    } catch {
      // ignore
    }
  }

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.dashboard.marketing.title')}
          subtitle={t('app.dashboard.marketing.subtitle')}
          kind="browse"
          secondaryActions={
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => {
                void load()
                void loadFx()
              }}
              disabled={loading || fxLoading || rangeInvalid}
            >
              {loading || fxLoading
                ? t('app.dashboard.refresh.loading')
                : t('app.dashboard.refresh.action')}
            </button>
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pb-4">
        <MarketingEfficiencyFiltersBar
          t={t}
          quickRangeOptions={quickRangeOptions}
          activeRange={activeRange}
          applyQuickRange={applyQuickRange}
          dateFrom={dateFrom}
          setDateFrom={setDateFrom}
          dateTo={dateTo}
          setDateTo={setDateTo}
          setActiveRange={setActiveRange}
          selectedIds={selectedIds}
          campaignOptions={campaignOptions}
          onToggleCampaign={onToggleCampaign}
          onSelectAll={onSelectAll}
          onClearSelection={onClearSelection}
          onApplyPreset={onApplyPreset}
          activePreset={activePreset}
          displayCurrency={displayCurrency}
          onDisplayCurrencyChange={onDisplayCurrencyChange}
          fxAsOf={fxRates?.as_of ?? null}
          fxProvider={fxRates?.provider ?? null}
          fxLoading={fxLoading}
          loading={loading}
          selectedCount={selectedIds.length}
          formatNumber={formatNumber}
        />

        {errText ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {errText}
          </div>
        ) : null}

        {fxError && displayCurrency === 'USD' ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            {t('app.dashboard.marketing.fx.error')}
          </div>
        ) : null}

        <MarketingEfficiencyPanel
          t={t}
          formatNumber={formatNumber}
          formatMoney={formatMoney}
          rows={selectedRows}
          totals={totals}
          series={series}
          loading={loading}
        />
      </div>
    </PageShell>
  )
}
