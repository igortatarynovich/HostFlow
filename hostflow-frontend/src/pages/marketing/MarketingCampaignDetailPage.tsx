/**
 * Marketing Flight ops card — runtime controls, KPI strip, Live Intake Monitor.
 */
import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CRM_APP_PATHS, marketingConnectSourcePath } from '../../app/crmAppPaths'
import { getVacancy } from '../../api/vacancies'
import { listAdditionalServices } from '../../api/additionalServices'
import {
  archiveCampaign,
  completeCampaign,
  completeFlight,
  currentFlight,
  getCampaign,
  getFlightOptimization,
  getFlightRuntime,
  getLiveIntakeMonitor,
  launchFlight,
  pauseFlight,
  resumeFlight,
  type Campaign,
  type FlightOptimization,
  type FlightRuntime,
  type LiveIntakeMonitor,
} from '../../api/platformCampaigns'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import { useI18n } from '../../i18n'
import { formatDateTime } from '../../utils/dateFormat'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import { humanizeEventType } from '../acquisition/acquisitionActivityPresentation'
import {
  formPublicUrl,
  primaryForm,
  primarySource,
  canConnectAnySource,
  statusLabel,
  statusTone,
} from './marketingPresentation'

export default function MarketingCampaignDetailPage() {
  const { t, locale } = useI18n()
  const { campaignId = '' } = useParams<{ campaignId: string }>()
  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [runtime, setRuntime] = useState<FlightRuntime | null>(null)
  const [monitor, setMonitor] = useState<LiveIntakeMonitor | null>(null)
  const [optimization, setOptimization] = useState<FlightOptimization | null>(null)
  const [destinationLabel, setDestinationLabel] = useState<string>('—')
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [loadingMore, setLoadingMore] = useState(false)

  const load = useCallback(async () => {
    if (!campaignId) return
    setLoading(true)
    setError(null)
    try {
      const c = await getCampaign(campaignId)
      setCampaign(c)
      const flight = currentFlight(c)
      if (flight) {
        const [rt, mon, opt] = await Promise.all([
          getFlightRuntime(c.id, flight.id),
          getLiveIntakeMonitor(c.id, flight.id, { limit: 40 }),
          getFlightOptimization(c.id, flight.id).catch(() => null),
        ])
        setRuntime(rt)
        setMonitor(mon)
        setOptimization(opt)
      } else {
        setRuntime(null)
        setMonitor(null)
        setOptimization(null)
      }

      const target = c.targets?.[0]
      if (target?.target_type === 'vacancy' && target.target_id) {
        try {
          const v = await getVacancy(target.target_id)
          setDestinationLabel(v?.title || 'Вакансия')
        } catch {
          setDestinationLabel('Вакансия')
        }
      } else if (target?.target_type === 'service' && target.target_id) {
        try {
          const services = await listAdditionalServices(true)
          const s = services.find((row) => row.id === target.target_id)
          setDestinationLabel(s?.name || 'Услуга')
        } catch {
          setDestinationLabel('Услуга')
        }
      } else {
        setDestinationLabel(target ? target.target_type : 'Не задано')
      }
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.detail.errors.load', { defaultValue: 'Не удалось загрузить кампанию' }),
          t,
        ),
      )
      setCampaign(null)
      setRuntime(null)
      setMonitor(null)
      setOptimization(null)
    } finally {
      setLoading(false)
    }
  }, [campaignId, t])

  useEffect(() => {
    void load()
  }, [load])

  const flight = campaign ? currentFlight(campaign) : null
  const form = primaryForm(flight)
  const source = primarySource(flight)

  const flightStatus = runtime?.flight_status || flight?.status || 'planned'
  const campaignStatus = runtime?.campaign_status || campaign?.status || 'draft'
  const canLaunch = flightStatus === 'planned'
  const canPause = flightStatus === 'active'
  const canResume = flightStatus === 'paused'
  const canCompleteFlight = flightStatus === 'active'
  const canCompleteCampaign = ['draft', 'active', 'paused'].includes(campaignStatus)
  const canArchiveCampaign = ['draft', 'active', 'paused', 'completed'].includes(campaignStatus)

  async function runFlightCommand(kind: 'launch' | 'pause' | 'resume' | 'complete') {
    if (!campaign || !flight) return
    setActing(true)
    setError(null)
    try {
      const fn =
        kind === 'launch'
          ? launchFlight
          : kind === 'pause'
            ? pauseFlight
            : kind === 'resume'
              ? resumeFlight
              : completeFlight
      await fn(campaign.id, flight.id)
      await load()
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.detail.errors.command', { defaultValue: 'Не удалось выполнить действие' }),
          t,
        ),
      )
    } finally {
      setActing(false)
    }
  }

  async function runCampaignCommand(kind: 'complete' | 'archive') {
    if (!campaign) return
    setActing(true)
    setError(null)
    try {
      const next =
        kind === 'complete'
          ? await completeCampaign(campaign.id)
          : await archiveCampaign(campaign.id)
      setCampaign(next)
      await load()
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.detail.errors.command', { defaultValue: 'Не удалось выполнить действие' }),
          t,
        ),
      )
    } finally {
      setActing(false)
    }
  }

  async function loadMoreMonitor() {
    if (!campaign || !flight || !monitor?.next_cursor || loadingMore) return
    setLoadingMore(true)
    setError(null)
    try {
      const page = await getLiveIntakeMonitor(campaign.id, flight.id, {
        limit: 40,
        after_occurred_at: monitor.next_cursor.occurred_at,
        after_id: monitor.next_cursor.id,
      })
      setMonitor({
        ...page,
        items: [...(monitor.items || []), ...(page.items || [])],
      })
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.detail.errors.load_more', {
            defaultValue: 'Не удалось подгрузить события монитора',
          }),
          t,
        ),
      )
    } finally {
      setLoadingMore(false)
    }
  }

  const publicUrl = formPublicUrl(form?.public_slug)
  const sourceLabel =
    source?.name || source?.provider || (form ? 'Публичная анкета HostFlow' : '—')
  const formLinks = flight?.forms?.filter((f) => f.is_active) || []
  const intakeLinks = flight?.intake_sources?.filter((s) => s.is_active) || []
  const hasAnySourceBinding = formLinks.length > 0 || intakeLinks.length > 0
  const showConnectCta = Boolean(flight && canConnectAnySource(flight))
  const primaryTarget = campaign?.targets?.find((x) => x.role === 'primary')
  const contextTargets = campaign?.targets?.filter((x) => x.role === 'context') || []
  const counters = monitor?.counters
  const kpiTiles = [
    { label: 'Заявки', value: counters?.submissions ?? 0 },
    { label: 'Направлено', value: counters?.routing_completed ?? 0 },
    { label: 'Ошибки маршрута', value: counters?.routing_failed ?? 0 },
    { label: 'Лиды (KPI)', value: counters?.kpi_leads ?? 0 },
    {
      label: 'CPL',
      value:
        counters?.cost_per_lead != null
          ? `${counters.cost_per_lead}${counters.currency ? ` ${counters.currency}` : ''}`
          : '—',
    },
    {
      label: 'Spend',
      value: counters
        ? `${counters.spend}${counters.currency ? ` ${counters.currency}` : ''}`
        : '0',
    },
  ]

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={campaign?.name || t('app.marketing.detail.title', { defaultValue: 'Кампания' })}
          subtitle={
            flight
              ? `Flight · ${statusLabel(flightStatus)}`
              : t('app.marketing.detail.no_flight', { defaultValue: 'Flight не найден' })
          }
          kind="browse"
          secondaryActions={
            <div className="flex flex-wrap gap-2">
              <Link to={CRM_APP_PATHS.marketing} className="btn-secondary btn-sm">
                К списку
              </Link>
              <button type="button" className="btn-secondary btn-sm" onClick={() => void load()} disabled={loading}>
                {loading ? t('common.loading') : t('common.actions.refresh')}
              </button>
            </div>
          }
          primaryAction={
            flight ? (
              <div className="flex flex-wrap gap-2">
                {canLaunch ? (
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    disabled={acting}
                    onClick={() => void runFlightCommand('launch')}
                    data-testid="marketing-flight-launch"
                  >
                    Запустить
                  </button>
                ) : null}
                {canPause ? (
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    disabled={acting}
                    onClick={() => void runFlightCommand('pause')}
                    data-testid="marketing-flight-pause"
                  >
                    Приостановить
                  </button>
                ) : null}
                {canResume ? (
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    disabled={acting}
                    onClick={() => void runFlightCommand('resume')}
                    data-testid="marketing-flight-resume"
                  >
                    Возобновить
                  </button>
                ) : null}
                {canCompleteFlight ? (
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    disabled={acting}
                    onClick={() => void runFlightCommand('complete')}
                    data-testid="marketing-flight-complete"
                  >
                    Завершить Flight
                  </button>
                ) : null}
                {canCompleteCampaign ? (
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    disabled={acting}
                    onClick={() => void runCampaignCommand('complete')}
                    data-testid="marketing-campaign-complete"
                  >
                    Завершить кампанию
                  </button>
                ) : null}
                {canArchiveCampaign ? (
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    disabled={acting}
                    onClick={() => void runCampaignCommand('archive')}
                    data-testid="marketing-campaign-archive"
                  >
                    В архив
                  </button>
                ) : null}
              </div>
            ) : undefined
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-6">
        {error ? <ErrorRecoveryBanner info={error} onRetry={() => void load()} /> : null}
        {loading && !campaign ? <p className="text-sm text-slate-500">{t('common.loading')}</p> : null}

        {campaign ? (
          <>
            <section className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <div className="text-xs text-slate-500">Кампания</div>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs ring-1 ring-inset ${statusTone(campaignStatus)}`}
                  >
                    {statusLabel(campaignStatus)}
                  </span>
                </div>
                {runtime ? (
                  <div className="mt-1 text-xs text-slate-500">
                    Endpoints: forms {runtime.endpoints.forms_active}/{runtime.endpoints.forms_total}
                    {' · '}
                    sources {runtime.endpoints.intake_sources_active}/
                    {runtime.endpoints.intake_sources_total}
                  </div>
                ) : null}
              </div>
              <div>
                <div className="text-xs text-slate-500">Анкета HostFlow</div>
                <div className="mt-1 text-sm font-medium text-slate-900">{form?.title || '—'}</div>
                {publicUrl ? (
                  <a
                    href={publicUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 block break-all text-xs text-brand-600 underline"
                  >
                    Открыть публичную ссылку
                  </a>
                ) : null}
              </div>
              <div>
                <div className="text-xs text-slate-500">Источник (кратко)</div>
                <div className="mt-1 text-sm font-medium text-slate-900">{sourceLabel}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Куда идут заявки</div>
                <div className="mt-1 text-sm font-medium text-slate-900">{destinationLabel}</div>
                {primaryTarget ? (
                  <div className="mt-1 text-xs text-slate-500">{primaryTarget.route_intent}</div>
                ) : null}
                {flight?.starts_at ? (
                  <div className="mt-1 text-xs text-slate-500">
                    Запуск: {formatDateTime(flight.starts_at, locale)}
                  </div>
                ) : null}
              </div>
            </section>

            <section
              className="rounded-xl border border-slate-200 bg-white p-4"
              data-testid="marketing-campaign-sources"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-sm font-semibold text-slate-900">Источники заявок</h2>
                  <p className="mt-1 text-xs text-slate-500">
                    Подключения к текущему Flight. Routing наследует Primary Target кампании.
                  </p>
                </div>
                {showConnectCta ? (
                  <Link
                    to={marketingConnectSourcePath(campaign.id)}
                    className="btn-primary btn-sm"
                    data-testid="marketing-connect-source-cta"
                  >
                    Подключить источник
                  </Link>
                ) : null}
              </div>

              {!hasAnySourceBinding ? (
                <div
                  className="mt-4 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center"
                  data-testid="marketing-sources-empty"
                >
                  <p className="text-sm font-medium text-slate-800">Источников пока нет</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Подключите Meta Lead Ads или публичную анкету HostFlow — без повторного создания
                    кампании.
                  </p>
                  {showConnectCta ? (
                    <Link
                      to={marketingConnectSourcePath(campaign.id)}
                      className="btn-primary btn-sm mt-4 inline-flex"
                      data-testid="marketing-sources-empty-cta"
                    >
                      Подключить источник
                    </Link>
                  ) : null}
                </div>
              ) : (
                <ul className="mt-4 space-y-2">
                  {formLinks.map((f) => (
                    <li
                      key={f.id}
                      className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                      data-testid={`marketing-source-form-${f.id}`}
                    >
                      <div className="font-medium text-slate-900">
                        Анкета HostFlow · {f.title || f.form_id}
                      </div>
                      <div className="text-xs text-slate-500">
                        role={f.role}
                        {f.public_slug ? ` · ${f.public_slug}` : ''}
                      </div>
                    </li>
                  ))}
                  {intakeLinks.map((s) => (
                    <li
                      key={s.id}
                      className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                      data-testid={`marketing-source-intake-${s.id}`}
                    >
                      <div className="font-medium text-slate-900">
                        Lead Form (Meta) · {s.name || s.code || s.intake_source_profile_id}
                      </div>
                      <div className="text-xs text-slate-500">
                        role={s.role}
                        {s.provider ? ` · ${s.provider}` : ''}
                      </div>
                    </li>
                  ))}
                </ul>
              )}

              {!showConnectCta && hasAnySourceBinding ? (
                <p
                  className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600"
                  data-testid="marketing-sources-primary-limit"
                >
                  Primary-слоты анкеты HostFlow и Meta-источника для этого Flight заняты. Несколько
                  равноправных источников одного типа появятся в следующем обновлении — сейчас UI не
                  предлагает подключение, которое завершится ошибкой.
                </p>
              ) : null}

              {contextTargets.length ? (
                <div className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-600">
                  <div className="font-medium text-slate-700">Контекст кампании</div>
                  <ul className="mt-1 list-inside list-disc">
                    {contextTargets.map((ct) => (
                      <li key={ct.id}>
                        {ct.target_type}: {ct.target_id}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </section>

            <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6" data-testid="marketing-ops-kpi-strip">
              {kpiTiles.map((kpi) => (
                <div key={kpi.label} className="rounded-xl border border-slate-200 bg-white px-3 py-3">
                  <div className="text-xs text-slate-500">{kpi.label}</div>
                  <div className="mt-1 text-xl font-semibold text-slate-900">{kpi.value}</div>
                </div>
              ))}
            </section>

            {optimization?.recommended_action === 'suggest_pause' ? (
              <div
                className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
                data-testid="marketing-optimization-suggest-pause"
                role="status"
              >
                <div className="font-semibold">Рекомендация: рассмотреть паузу Flight</div>
                <p className="mt-1 text-amber-900/90">
                  Сигнал только советует — пауза через кнопку «Пауза» выше. Автопаузы нет.
                </p>
                {optimization.signals.length ? (
                  <ul className="mt-2 list-disc space-y-0.5 pl-4 text-xs text-amber-900/80">
                    {optimization.signals
                      .filter((s) => s.code !== 'within_thresholds')
                      .map((s) => (
                        <li key={s.code}>{s.message}</li>
                      ))}
                  </ul>
                ) : null}
              </div>
            ) : null}

            <section className="rounded-xl border border-slate-200 bg-white" data-testid="marketing-live-intake-monitor">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <h2 className="text-sm font-semibold text-slate-900">Live Intake Monitor</h2>
                <Link
                  to={`${CRM_APP_PATHS.acquisitionActivity}?campaign_id=${encodeURIComponent(campaign.id)}${
                    flight ? `&flight_id=${encodeURIComponent(flight.id)}` : ''
                  }`}
                  className="text-xs font-medium text-brand-600"
                >
                  Полный таймлайн →
                </Link>
              </div>
              {!monitor?.items?.length ? (
                <p className="px-4 py-6 text-sm text-slate-500">
                  Пока нет intake-событий. Отправьте тестовую заявку по публичной ссылке.
                  Meta без Submission (D2) в Timeline не попадёт.
                </p>
              ) : (
                <>
                  <ul className="divide-y divide-slate-100">
                    {monitor.items.map((e) => (
                      <li key={e.id} className="px-4 py-3">
                        <button
                          type="button"
                          className="w-full text-left"
                          onClick={() => setExpandedId((id) => (id === e.id ? null : e.id))}
                        >
                          <div className="flex flex-wrap items-baseline justify-between gap-2">
                            <span className="text-sm font-medium text-slate-900">
                              {humanizeEventType(e.event_type)}
                            </span>
                            <span className="text-xs text-slate-500">
                              {formatDateTime(e.occurred_at, locale)}
                            </span>
                          </div>
                          {e.submission_id ? (
                            <div className="mt-0.5 text-xs text-slate-500">
                              submission {e.submission_id.slice(0, 8)}…
                            </div>
                          ) : null}
                        </button>
                        {expandedId === e.id ? (
                          <pre className="mt-2 overflow-x-auto rounded bg-slate-50 p-2 text-xs text-slate-700">
                            {JSON.stringify(
                              {
                                id: e.id,
                                event_type: e.event_type,
                                submission_id: e.submission_id,
                                payload: e.payload ?? {},
                              },
                              null,
                              2,
                            )}
                          </pre>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                  {monitor.next_cursor ? (
                    <div className="border-t border-slate-100 px-4 py-3">
                      <button
                        type="button"
                        className="btn-secondary btn-sm"
                        disabled={loadingMore}
                        onClick={() => void loadMoreMonitor()}
                        data-testid="marketing-monitor-load-more"
                      >
                        {loadingMore ? t('common.loading') : 'Ещё события'}
                      </button>
                    </div>
                  ) : null}
                </>
              )}
            </section>
          </>
        ) : null}
      </div>
    </PageShell>
  )
}
