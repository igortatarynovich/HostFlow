/**
 * Marketing Workspace — campaign roster (TABLE_V1 DataTable).
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CRM_APP_PATHS, marketingCampaignPath } from '../../app/crmAppPaths'
import {
  currentFlight,
  getCampaignPortfolio,
  getLiveIntakeMonitor,
  launchFlight,
  listCampaigns,
  pauseFlight,
  resumeFlight,
  type Campaign,
  type CampaignPortfolio,
  type PortfolioCampaignRow,
} from '../../api/platformCampaigns'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { Chip } from '../../components/ui/Chip'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { PageHeader } from '../../components/nav/PageHeader'
import {
  DataTable,
  PageShell,
  PageShellHeader,
  Toolbar,
  type DataTableColumn,
} from '../../components/layout'
import { useI18n } from '../../i18n'
import { formatDateTime } from '../../utils/dateFormat'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import {
  destinationSummary,
  primaryForm,
  primarySource,
  statusLabel,
  statusSemantic,
} from './marketingPresentation'
import { MarketingWorkspaceNav } from './MarketingWorkspaceNav'

type RosterFilter = 'all' | 'active' | 'paused' | 'completed'

type CampaignRosterRow = {
  campaign: Campaign
  status: string
  formTitle: string
  sourceLabel: string
  destination: string
  launchedLabel: string
  received: number | null
  costPerLead: string | null
  currency: string | null
}

const ROSTER_FILTERS: RosterFilter[] = ['all', 'active', 'paused', 'completed']
const LIST_LIMIT = 100

function rosterStatus(campaign: Campaign): string {
  const flight = currentFlight(campaign)
  return String(flight?.status || campaign.status || '').toLowerCase()
}

function matchesRoster(status: string, filter: RosterFilter): boolean {
  if (filter === 'all') return true
  if (filter === 'active') return status === 'active'
  if (filter === 'paused') return status === 'paused'
  return status === 'completed' || status === 'archived'
}

function portfolioByCampaign(portfolio: CampaignPortfolio | null): Map<string, PortfolioCampaignRow> {
  const map = new Map<string, PortfolioCampaignRow>()
  for (const row of portfolio?.campaigns ?? []) {
    map.set(row.campaign_id, row)
  }
  return map
}

export default function MarketingCampaignsPage() {
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const [items, setItems] = useState<Campaign[]>([])
  const [portfolio, setPortfolio] = useState<CampaignPortfolio | null>(null)
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [actingId, setActingId] = useState<string | null>(null)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [query, setQuery] = useState('')
  const [rosterFilter, setRosterFilter] = useState<RosterFilter>('all')

  const loadCounts = useCallback(async (campaigns: Campaign[]) => {
    const entries = await Promise.all(
      campaigns.map(async (c) => {
        const flight = currentFlight(c)
        if (!flight) return [c.id, 0] as const
        try {
          // Same SoT as detail KPI «Заявки»: Flight-attributed people, not Activity.
          const mon = await getLiveIntakeMonitor(c.id, flight.id, { limit: 1 })
          return [c.id, mon.counters?.submissions ?? 0] as const
        } catch {
          return [c.id, 0] as const
        }
      }),
    )
    const next: Record<string, number> = {}
    for (const [id, received] of entries) {
      next[id] = received
    }
    setCounts(next)
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [rows, folio] = await Promise.all([
        listCampaigns({ limit: LIST_LIMIT }),
        getCampaignPortfolio(50).catch(() => null),
      ])
      setItems(rows)
      setPortfolio(folio)
      void loadCounts(rows)
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.errors.load'),
          t,
        ),
      )
      setItems([])
      setPortfolio(null)
    } finally {
      setLoading(false)
    }
  }, [loadCounts, t])

  useEffect(() => {
    void load()
  }, [load])

  const runCommand = useCallback(async (campaign: Campaign, kind: 'launch' | 'pause' | 'resume') => {
    const flight = currentFlight(campaign)
    if (!flight) return
    setActingId(campaign.id)
    setError(null)
    try {
      const fn = kind === 'launch' ? launchFlight : kind === 'pause' ? pauseFlight : resumeFlight
      const result = await fn(campaign.id, flight.id)
      setItems((prev) => prev.map((row) => (row.id === campaign.id ? result.campaign : row)))
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.errors.command'),
          t,
        ),
      )
    } finally {
      setActingId(null)
    }
  }, [t])

  const rows = useMemo((): CampaignRosterRow[] => {
    const folioMap = portfolioByCampaign(portfolio)
    const q = query.trim().toLowerCase()
    const built: CampaignRosterRow[] = []
    for (const campaign of items) {
      const status = rosterStatus(campaign)
      if (!matchesRoster(status, rosterFilter)) continue
      const flight = currentFlight(campaign)
      const form = primaryForm(flight)
      const source = primarySource(flight)
      const sourceLabel = source?.name || source?.provider || (form ? t('app.marketing.list.public_form') : '—')
      const destination = destinationSummary(campaign, t)
      const launchedLabel = flight?.starts_at
        ? formatDateTime(flight.starts_at, locale)
        : t('app.marketing.list.not_launched')
      if (q) {
        const hay = [campaign.name, form?.title || '', sourceLabel, destination].join(' ').toLowerCase()
        if (!hay.includes(q)) continue
      }
      const folio = folioMap.get(campaign.id)
      built.push({
        campaign,
        status,
        formTitle: form?.title || '—',
        sourceLabel,
        destination,
        launchedLabel,
        received: counts[campaign.id] ?? null,
        costPerLead: folio?.cost_per_lead ?? null,
        currency: folio?.currency || portfolio?.currency || null,
      })
    }
    return built
  }, [counts, items, locale, portfolio, query, rosterFilter, t])

  const showPriceColumn = useMemo(
    () => rows.some((row) => Boolean(row.costPerLead)),
    [rows],
  )

  const columns = useMemo((): DataTableColumn<CampaignRosterRow>[] => {
    const cols: DataTableColumn<CampaignRosterRow>[] = [
      {
        key: 'campaign',
        header: t('app.marketing.list.columns.campaign'),
        minWidth: 180,
        render: (row) => (
          <span className="font-medium text-slate-900" data-testid={`marketing-campaign-name-${row.campaign.id}`}>
            {row.campaign.name}
          </span>
        ),
      },
      {
        key: 'status',
        header: t('app.marketing.list.columns.status'),
        render: (row) => (
          <StatusBadge label={statusLabel(row.status, t)} semantic={statusSemantic(row.status)} />
        ),
      },
      {
        key: 'applications',
        header: t('app.marketing.list.columns.applications'),
        align: 'right',
        tabularNums: true,
        compact: true,
        render: (row) => (row.received == null ? '…' : row.received),
      },
      {
        key: 'form',
        header: t('app.marketing.list.columns.form'),
        render: (row) => <span className="text-slate-700">{row.formTitle}</span>,
      },
      {
        key: 'source',
        header: t('app.marketing.list.columns.source'),
        render: (row) => <span className="text-slate-700">{row.sourceLabel}</span>,
      },
      {
        key: 'destination',
        header: t('app.marketing.list.columns.destination'),
        render: (row) => <span className="text-slate-700">{row.destination}</span>,
      },
      {
        key: 'launch',
        header: t('app.marketing.list.columns.launch'),
        render: (row) => <span className="text-slate-600">{row.launchedLabel}</span>,
      },
    ]

    if (showPriceColumn) {
      cols.push({
        key: 'price',
        header: t('app.marketing.list.columns.price'),
        align: 'right',
        tabularNums: true,
        compact: true,
        render: (row) =>
          row.costPerLead ? (
            <span className="text-slate-900">
              {row.costPerLead}
              {row.currency ? ` ${row.currency}` : ''}
            </span>
          ) : (
            <span className="text-slate-500">{t('app.marketing.list.price_not_loaded')}</span>
          ),
      })
    }

    cols.push({
      key: 'actions',
      header: t('app.marketing.list.columns.actions'),
      align: 'right',
      render: (row) => {
        const busy = actingId === row.campaign.id
        const flight = currentFlight(row.campaign)
        return (
          <div className="flex flex-wrap justify-end gap-2" onClick={(e) => e.stopPropagation()}>
            <Link to={marketingCampaignPath(row.campaign.id)} className="btn-secondary btn-sm">
              {t('app.marketing.list.open')}
            </Link>
            {row.status === 'planned' ? (
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={busy || !flight}
                onClick={() => void runCommand(row.campaign, 'launch')}
              >
                {t('app.marketing.detail.start')}
              </button>
            ) : null}
            {row.status === 'active' ? (
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={busy || !flight}
                onClick={() => void runCommand(row.campaign, 'pause')}
              >
                {t('app.marketing.detail.pause')}
              </button>
            ) : null}
            {row.status === 'paused' ? (
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={busy || !flight}
                onClick={() => void runCommand(row.campaign, 'resume')}
              >
                {t('app.marketing.detail.resume')}
              </button>
            ) : null}
          </div>
        )
      },
    })

    return cols
  }, [actingId, runCommand, showPriceColumn, t])

  const emptyState =
    items.length === 0 && !error ? (
      <div className="mx-auto max-w-md">
        <p className="text-sm font-medium text-slate-800">{t('app.marketing.empty_title')}</p>
        <p className="mt-1 text-sm text-slate-600">{t('app.marketing.empty_body')}</p>
        <Link to={CRM_APP_PATHS.marketingNew} className="btn-primary btn-sm mt-4 inline-flex">
          {t('app.marketing.actions.create')}
        </Link>
      </div>
    ) : (
      t('app.marketing.list.empty_filtered')
    )

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          kind="browse"
          primaryAction={
            <Link to={CRM_APP_PATHS.marketingNew} className="btn-primary btn-sm">
              {t('app.marketing.actions.create')}
            </Link>
          }
          secondaryActions={
            <button type="button" className="btn-secondary btn-sm" onClick={() => void load()} disabled={loading}>
              {loading ? t('common.loading') : t('common.actions.refresh')}
            </button>
          }
        />
        <MarketingWorkspaceNav />
        {error ? <div className="mt-3"><ErrorRecoveryBanner info={error} onRetry={() => void load()} /></div> : null}

        {portfolio && portfolio.campaigns.length > 0 ? (
          <section
            className="mt-3 rounded-xl border border-slate-200 bg-white px-4 py-3"
            data-testid="marketing-campaign-portfolio"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-sm font-semibold text-slate-900">
                {t('app.marketing.portfolio.title')}
              </h2>
              <p className="text-xs text-slate-500">
                {t('app.marketing.portfolio.subtitle')}
                {portfolio.scan_capped ? t('app.marketing.portfolio.capped') : ''}
              </p>
            </div>
            <div
              className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6"
              data-testid="marketing-campaign-portfolio-totals"
            >
              <div>
                <div className="text-xs text-slate-500">{t('app.marketing.metrics.spend')}</div>
                <div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
                  {portfolio.spend}
                  {portfolio.currency ? ` ${portfolio.currency}` : ''}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">{t('app.marketing.metrics.leads')}</div>
                <div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
                  {portfolio.leads}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">{t('app.marketing.metrics.cpl')}</div>
                <div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
                  {portfolio.cost_per_lead != null ? portfolio.cost_per_lead : '—'}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">{t('app.marketing.metrics.cac_proxy')}</div>
                <div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
                  {portfolio.cost_per_outcome != null ? portfolio.cost_per_outcome : '—'}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">{t('app.marketing.metrics.value')}</div>
                <div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
                  {portfolio.outcome_value != null ? portfolio.outcome_value : '—'}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">{t('app.marketing.metrics.roi')}</div>
                <div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
                  {portfolio.roi != null ? portfolio.roi : '—'}
                </div>
              </div>
            </div>
          </section>
        ) : null}
      </PageShellHeader>

      <Toolbar>
        <div className="flex flex-wrap items-center gap-2">
          <input
            className="input w-56"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('app.marketing.list.search_placeholder')}
            data-testid="marketing-campaigns-search"
            aria-label={t('app.marketing.list.search_placeholder')}
          />
          <div className="flex flex-wrap items-center gap-1.5" data-testid="marketing-campaigns-filters">
            {ROSTER_FILTERS.map((key) => (
              <Chip
                key={key}
                behavior="selectable"
                size="sm"
                selected={rosterFilter === key}
                selectedAppearance="soft"
                label={t(`app.marketing.list.filters.${key}`)}
                onClick={() => setRosterFilter(key)}
              />
            ))}
          </div>
        </div>
      </Toolbar>

      <div className="flex min-h-0 flex-1 flex-col" data-testid="marketing-campaigns-table">
        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(row) => row.campaign.id}
          loading={loading}
          onRowClick={(row) => navigate(marketingCampaignPath(row.campaign.id))}
          emptyState={emptyState}
          ariaLabel={t('app.marketing.list.aria')}
          footer={t('app.marketing.list.footer_visible', { values: { count: String(rows.length) } })}
        />
      </div>
    </PageShell>
  )
}
