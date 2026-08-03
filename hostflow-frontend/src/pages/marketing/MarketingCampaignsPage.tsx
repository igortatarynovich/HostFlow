/**
 * Marketing Workspace — campaign list (product surface for Flights).
 */
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
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
} from '../../api/platformCampaigns'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import { useI18n } from '../../i18n'
import { formatDateTime } from '../../utils/dateFormat'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import {
  destinationSummary,
  primaryForm,
  primarySource,
  statusLabel,
  statusTone,
} from './marketingPresentation'

type RowMeta = { received: number }

export default function MarketingCampaignsPage() {
  const { t, locale } = useI18n()
  const [items, setItems] = useState<Campaign[]>([])
  const [portfolio, setPortfolio] = useState<CampaignPortfolio | null>(null)
  const [counts, setCounts] = useState<Record<string, RowMeta>>({})
  const [loading, setLoading] = useState(true)
  const [actingId, setActingId] = useState<string | null>(null)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)

  const loadCounts = useCallback(async (campaigns: Campaign[]) => {
    const entries = await Promise.all(
      campaigns.map(async (c) => {
        const flight = currentFlight(c)
        if (!flight) return [c.id, { received: 0 }] as const
        try {
          // Same SoT as detail KPI «Заявки»: Flight-attributed people, not Activity.
          const mon = await getLiveIntakeMonitor(c.id, flight.id, { limit: 1 })
          return [c.id, { received: mon.counters?.submissions ?? 0 }] as const
        } catch {
          return [c.id, { received: 0 }] as const
        }
      }),
    )
    const next: Record<string, RowMeta> = {}
    for (const [id, funnel] of entries) {
      next[id] = { received: funnel.received }
    }
    setCounts(next)
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [rows, folio] = await Promise.all([
        listCampaigns({ limit: 100 }),
        getCampaignPortfolio(50).catch(() => null),
      ])
      setItems(rows)
      setPortfolio(folio)
      void loadCounts(rows)
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.errors.load', { defaultValue: 'Не удалось загрузить кампании' }),
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

  async function runCommand(campaign: Campaign, kind: 'launch' | 'pause' | 'resume') {
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
          t('app.marketing.errors.command', { defaultValue: 'Не удалось выполнить действие' }),
          t,
        ),
      )
    } finally {
      setActingId(null)
    }
  }

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.marketing.title', { defaultValue: 'Маркетинг' })}
          subtitle={t('app.marketing.subtitle', {
            defaultValue: 'Кампании, формы и запуск Flight — от идеи до входящих заявок.',
          })}
          kind="browse"
          primaryAction={
            <Link to={CRM_APP_PATHS.marketingNew} className="btn-primary btn-sm">
              {t('app.marketing.actions.create', { defaultValue: 'Создать кампанию' })}
            </Link>
          }
          secondaryActions={
            <button type="button" className="btn-secondary btn-sm" onClick={() => void load()} disabled={loading}>
              {loading ? t('common.loading') : t('common.actions.refresh')}
            </button>
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
        {error ? <ErrorRecoveryBanner info={error} onRetry={() => void load()} /> : null}

        {portfolio && portfolio.campaigns.length > 0 ? (
          <section
            className="rounded-xl border border-slate-200 bg-white px-4 py-4"
            data-testid="marketing-campaign-portfolio"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-sm font-semibold text-slate-900">
                {t('app.marketing.portfolio.title', { defaultValue: 'Portfolio KPI' })}
              </h2>
              <p className="text-xs text-slate-500">
                {t('app.marketing.portfolio.subtitle', {
                  defaultValue: 'Сводка по кампаниям компании (только чтение).',
                })}
                {portfolio.scan_capped
                  ? t('app.marketing.portfolio.capped', { defaultValue: ' Список ограничен.' })
                  : ''}
              </p>
            </div>
            <div
              className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4"
              data-testid="marketing-campaign-portfolio-totals"
            >
              <div>
                <div className="text-xs text-slate-500">Spend</div>
                <div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
                  {portfolio.spend}
                  {portfolio.currency ? ` ${portfolio.currency}` : ''}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Leads</div>
                <div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
                  {portfolio.leads}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">CPL</div>
                <div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
                  {portfolio.cost_per_lead != null ? portfolio.cost_per_lead : '—'}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">CAC proxy</div>
                <div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
                  {portfolio.cost_per_outcome != null ? portfolio.cost_per_outcome : '—'}
                </div>
              </div>
            </div>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs text-slate-500">
                  <tr>
                    <th className="py-2 pr-3 font-medium">Campaign</th>
                    <th className="py-2 pr-3 font-medium">Status</th>
                    <th className="py-2 pr-3 font-medium">Spend</th>
                    <th className="py-2 pr-3 font-medium">Leads</th>
                    <th className="py-2 pr-3 font-medium">CPL</th>
                    <th className="py-2 font-medium">CAC proxy</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.campaigns.map((row) => (
                    <tr
                      key={row.campaign_id}
                      className="border-t border-slate-100"
                      data-testid={`marketing-portfolio-row-${row.campaign_id}`}
                    >
                      <td className="py-2 pr-3 text-slate-900">
                        <Link
                          to={marketingCampaignPath(row.campaign_id)}
                          className="font-medium hover:underline"
                        >
                          {row.name}
                        </Link>
                        {row.is_best_cpl ? (
                          <span className="ml-2 rounded bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-800">
                            best CPL
                          </span>
                        ) : null}
                      </td>
                      <td className="py-2 pr-3 text-slate-700">{statusLabel(row.status)}</td>
                      <td className="py-2 pr-3 tabular-nums text-slate-900">
                        {row.spend}
                        {row.currency ? ` ${row.currency}` : ''}
                      </td>
                      <td className="py-2 pr-3 tabular-nums text-slate-900">{row.leads}</td>
                      <td className="py-2 pr-3 tabular-nums text-slate-700">
                        {row.cost_per_lead != null ? row.cost_per_lead : '—'}
                      </td>
                      <td className="py-2 tabular-nums text-slate-700">
                        {row.cost_per_outcome != null ? row.cost_per_outcome : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}

        {!loading && items.length === 0 && !error ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
            <p className="text-sm font-medium text-slate-800">
              {t('app.marketing.empty_title', { defaultValue: 'Пока нет кампаний' })}
            </p>
            <p className="mt-1 text-sm text-slate-600">
              {t('app.marketing.empty_body', {
                defaultValue: 'Создайте первую: форма → поток → запуск Flight.',
              })}
            </p>
            <Link to={CRM_APP_PATHS.marketingNew} className="btn-primary btn-sm mt-4 inline-flex">
              {t('app.marketing.actions.create', { defaultValue: 'Создать кампанию' })}
            </Link>
          </div>
        ) : null}

        <ul className="divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-200 bg-white">
          {items.map((campaign) => {
            const flight = currentFlight(campaign)
            const form = primaryForm(flight)
            const source = primarySource(flight)
            const sourceLabel = source?.name || source?.provider || (form ? 'Публичная форма' : '—')
            const status = flight?.status || 'planned'
            const busy = actingId === campaign.id
            return (
              <li key={campaign.id} className="px-4 py-3">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                  <Link
                    to={marketingCampaignPath(campaign.id)}
                    className="min-w-0 flex-1 transition hover:opacity-90"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="truncate text-sm font-semibold text-slate-900">{campaign.name}</span>
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs ring-1 ring-inset ${statusTone(campaign.status)}`}
                      >
                        {statusLabel(campaign.status)}
                      </span>
                      {flight ? (
                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-xs ring-1 ring-inset ${statusTone(flight.status)}`}
                        >
                          Flight: {statusLabel(flight.status)}
                        </span>
                      ) : null}
                      <span className="text-xs text-slate-500">
                        Заявок: {counts[campaign.id]?.received ?? '…'}
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                      <span>Форма: {form?.title || '—'}</span>
                      <span>Источник: {sourceLabel}</span>
                      <span>Куда: {destinationSummary(campaign)}</span>
                      <span>
                        Запуск:{' '}
                        {flight?.starts_at ? formatDateTime(flight.starts_at, locale) : 'ещё не запускали'}
                      </span>
                    </div>
                  </Link>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    <Link to={marketingCampaignPath(campaign.id)} className="btn-secondary btn-sm">
                      Открыть
                    </Link>
                    {status === 'planned' ? (
                      <button
                        type="button"
                        className="btn-primary btn-sm"
                        disabled={busy || !flight}
                        onClick={() => void runCommand(campaign, 'launch')}
                      >
                        Запустить
                      </button>
                    ) : null}
                    {status === 'active' ? (
                      <button
                        type="button"
                        className="btn-secondary btn-sm"
                        disabled={busy || !flight}
                        onClick={() => void runCommand(campaign, 'pause')}
                      >
                        Приостановить
                      </button>
                    ) : null}
                    {status === 'paused' ? (
                      <button
                        type="button"
                        className="btn-primary btn-sm"
                        disabled={busy || !flight}
                        onClick={() => void runCommand(campaign, 'resume')}
                      >
                        Возобновить
                      </button>
                    ) : null}
                  </div>
                </div>
              </li>
            )
          })}
        </ul>
      </div>
    </PageShell>
  )
}
