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
  postFlightOptimizationOperatorAction,
  resumeFlight,
  type Campaign,
  type FlightOptimization,
  type FlightRuntime,
  type LiveIntakeMonitor,
} from '../../api/platformCampaigns'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { ContextHelp } from '../../components/help/ContextHelp'
import { PageShell, PageShellHeader } from '../../components/layout'
import { useI18n } from '../../i18n'
import { formatDateTime } from '../../utils/dateFormat'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import {
  formPublicUrl,
  primaryForm,
  primarySource,
  canConnectAnySource,
  canConnectSourceKind,
  statusLabel,
  statusTone,
} from './marketingPresentation'
import { HostFlowFormSourceCard, MetaLeadFormSourceCard } from './MarketingSourceCards'
import { MarketingAdBindingsPanel } from './MarketingAdBindingsPanel'
import { MarketingConnectMetaAdvertising } from './MarketingConnectMetaAdvertising'

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
  const [loadingMore, setLoadingMore] = useState(false)
  const [metaWizardOpen, setMetaWizardOpen] = useState(false)

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

  async function runOptAction(action: 'acknowledge' | 'dismiss') {
    if (!campaign || !flight || !optimization?.signal_fingerprint) return
    setActing(true)
    setError(null)
    try {
      const next = await postFlightOptimizationOperatorAction(campaign.id, flight.id, {
        action,
        signal_fingerprint: optimization.signal_fingerprint,
      })
      setOptimization(next)
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
    if (!campaign || !flight || !monitor?.applicants_next_cursor || loadingMore) return
    setLoadingMore(true)
    setError(null)
    try {
      const page = await getLiveIntakeMonitor(campaign.id, flight.id, {
        limit: 40,
        applicants_after_created_at: monitor.applicants_next_cursor.created_at,
        applicants_after_id: monitor.applicants_next_cursor.id,
      })
      setMonitor({
        ...page,
        applicants: [...(monitor.applicants || []), ...(page.applicants || [])],
        items: monitor.items || [],
      })
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.detail.errors.load_more', {
            defaultValue: 'Не удалось подгрузить заявки',
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
  const showPublicConnectOnly = Boolean(flight && canConnectSourceKind(flight, 'public_form'))
  const showMetaConnect = Boolean(flight)
  const showPublicPrimaryLimitNote = Boolean(
    flight && !canConnectSourceKind(flight, 'public_form') && formLinks.length > 0,
  )
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
          title={
            <span className="inline-flex items-center gap-1.5">
              {campaign?.name || t('app.marketing.detail.title', { defaultValue: 'Кампания' })}
              <ContextHelp term="campaign" />
            </span>
          }
          subtitle={
            <span className="inline-flex items-center gap-1.5">
              {flight
                ? `Flight · ${statusLabel(flightStatus)}`
                : t('app.marketing.detail.no_flight', { defaultValue: 'Flight не найден' })}
              <ContextHelp term="flight" />
            </span>
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
                    Подключите Meta-рекламу (кампания → формы и объявления) или анкету HostFlow.
                    Connection (OAuth) — в Integrations. Routing наследует Primary Target кампании.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {showMetaConnect ? (
                    <button
                      type="button"
                      className="btn-primary btn-sm"
                      onClick={() => setMetaWizardOpen(true)}
                      data-testid="marketing-connect-meta-advertising-cta"
                    >
                      Подключить Meta-рекламу
                    </button>
                  ) : null}
                  {showPublicConnectOnly ? (
                    <Link
                      to={`${marketingConnectSourcePath(campaign.id)}?kind=public_form`}
                      className="btn-secondary btn-sm"
                      data-testid="marketing-connect-source-cta"
                    >
                      Анкета HostFlow
                    </Link>
                  ) : null}
                </div>
              </div>

              {!hasAnySourceBinding ? (
                <div
                  className="mt-4 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center"
                  data-testid="marketing-sources-empty"
                >
                  <p className="text-sm font-medium text-slate-800">Источников пока нет</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Выберите рекламную кампанию Meta — подключим её Lead Forms и объявления к Flight.
                  </p>
                  {showMetaConnect ? (
                    <button
                      type="button"
                      className="btn-primary btn-sm mt-4 inline-flex"
                      onClick={() => setMetaWizardOpen(true)}
                      data-testid="marketing-sources-empty-cta"
                    >
                      Подключить Meta-рекламу
                    </button>
                  ) : null}
                </div>
              ) : (
                <ul className="mt-4 space-y-3" data-testid="marketing-sources-list">
                  {formLinks.map((f) => (
                    <HostFlowFormSourceCard key={f.id} link={f} locale={locale} />
                  ))}
                  {intakeLinks.map((s) => (
                    <MetaLeadFormSourceCard key={s.id} link={s} locale={locale} />
                  ))}
                </ul>
              )}

              {flight?.ad_bindings?.filter((b) => b.is_active).length ? (
                <div className="mt-4" data-testid="marketing-ad-bindings-summary">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Объявления (Ad → Flight)
                  </h3>
                  <ul className="mt-2 space-y-1">
                    {flight.ad_bindings
                      .filter((b) => b.is_active)
                      .map((b) => (
                        <li key={b.id} className="font-mono text-xs text-slate-700">
                          {b.provider_ad_id}
                        </li>
                      ))}
                  </ul>
                </div>
              ) : null}

              {showPublicPrimaryLimitNote ? (
                <p
                  className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600"
                  data-testid="marketing-sources-primary-limit"
                >
                  Primary-слот анкеты HostFlow для этого Flight занят. Дополнительные Meta Lead Forms
                  можно подключать как secondary через «Подключить Meta-рекламу».
                </p>
              ) : null}

              <details className="mt-4 border-t border-slate-100 pt-3" data-testid="marketing-sources-advanced">
                <summary className="cursor-pointer text-xs font-medium text-slate-600">
                  Дополнительно: одна форма / ручной Ad ID
                </summary>
                <div className="mt-3 space-y-3">
                  {showConnectCta ? (
                    <Link
                      to={marketingConnectSourcePath(campaign.id)}
                      className="btn-secondary btn-sm inline-flex"
                      data-testid="marketing-connect-source-advanced"
                    >
                      Подключить один источник вручную
                    </Link>
                  ) : null}
                  {flight ? (
                    <MarketingAdBindingsPanel
                      campaignId={campaign.id}
                      flight={flight}
                      onChanged={load}
                      t={t}
                    />
                  ) : null}
                </div>
              </details>

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
                {optimization.explanation ? (
                  <p className="mt-2 text-xs text-amber-900/90" data-testid="marketing-optimization-explanation">
                    {optimization.explanation}
                  </p>
                ) : null}
                {optimization.observed ? (
                  <dl
                    className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-amber-900/80 sm:grid-cols-4"
                    data-testid="marketing-optimization-observed"
                  >
                    <div>
                      <dt className="text-amber-800/70">Fail rate</dt>
                      <dd className="font-medium tabular-nums">
                        {optimization.observed.routing_fail_rate == null
                          ? '—'
                          : optimization.observed.routing_fail_rate.toFixed(2)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-amber-800/70">Routing</dt>
                      <dd className="font-medium tabular-nums">
                        {optimization.observed.routing_failed}/{optimization.observed.routing_sample}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-amber-800/70">Delivery err</dt>
                      <dd className="font-medium tabular-nums">{optimization.observed.delivery_errors}</dd>
                    </div>
                    <div>
                      <dt className="text-amber-800/70">Volume</dt>
                      <dd className="font-medium tabular-nums">{optimization.observed.decision_volume}</dd>
                    </div>
                  </dl>
                ) : null}
                {optimization.signals.length ? (
                  <ul className="mt-2 list-disc space-y-0.5 pl-4 text-xs text-amber-900/80">
                    {optimization.signals
                      .filter((s) => s.code !== 'within_thresholds')
                      .map((s) => (
                        <li key={s.code}>{s.message}</li>
                      ))}
                  </ul>
                ) : null}
                {optimization.operator ? (
                  <p className="mt-2 text-xs text-amber-900/80" data-testid="marketing-optimization-operator-state">
                    {optimization.operator.action === 'dismiss'
                      ? 'Отклонено оператором'
                      : 'Подтверждено оператором'}
                    {optimization.operator.occurred_at
                      ? ` · ${formatDateTime(optimization.operator.occurred_at, locale)}`
                      : ''}
                  </p>
                ) : (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      data-testid="marketing-optimization-acknowledge"
                      disabled={acting || !optimization.signal_fingerprint}
                      onClick={() => void runOptAction('acknowledge')}
                    >
                      Принять к сведению
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      data-testid="marketing-optimization-dismiss"
                      disabled={acting || !optimization.signal_fingerprint}
                      onClick={() => void runOptAction('dismiss')}
                    >
                      Отклонить совет
                    </button>
                  </div>
                )}
              </div>
            ) : null}

            <section className="rounded-xl border border-slate-200 bg-white" data-testid="marketing-live-intake-monitor">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <div>
                  <h2 className="text-sm font-semibold text-slate-900">Заявки</h2>
                  <p className="mt-0.5 text-xs text-slate-500">
                    Люди, пришедшие на этот Flight. Технический лог — в таймлайне.
                  </p>
                </div>
                <Link
                  to={`${CRM_APP_PATHS.acquisitionActivity}?campaign_id=${encodeURIComponent(campaign.id)}${
                    flight ? `&flight_id=${encodeURIComponent(flight.id)}` : ''
                  }`}
                  className="text-xs font-medium text-brand-600"
                >
                  Таймлайн →
                </Link>
              </div>
              {!monitor?.applicants?.length ? (
                <p className="px-4 py-6 text-sm text-slate-500">
                  Пока нет заявок на этот Flight. После Connect Source новые Meta-лиды появятся здесь.
                </p>
              ) : (
                <>
                  <ul className="divide-y divide-slate-100">
                    {monitor.applicants.map((row) => {
                      const href = row.candidate_id
                        ? `${CRM_APP_PATHS.candidates}/${encodeURIComponent(row.candidate_id)}`
                        : `${CRM_APP_PATHS.leads}?q=${encodeURIComponent(row.lead_id)}`
                      const contact = [row.phone, row.email].filter(Boolean).join(' · ')
                      return (
                        <li key={row.lead_id} className="px-4 py-3">
                          <Link to={href} className="block hover:bg-slate-50/80 -mx-4 px-4 py-0.5 rounded">
                            <div className="flex flex-wrap items-baseline justify-between gap-2">
                              <span className="text-sm font-medium text-slate-900">
                                {row.full_name || 'Без имени'}
                              </span>
                              <span className="text-xs text-slate-500">
                                {row.created_at ? formatDateTime(row.created_at, locale) : '—'}
                              </span>
                            </div>
                            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-600">
                              <span className="rounded-md bg-slate-100 px-1.5 py-0.5 font-medium text-slate-800">
                                {row.status_label}
                              </span>
                              {contact ? <span>{contact}</span> : null}
                            </div>
                          </Link>
                        </li>
                      )
                    })}
                  </ul>
                  {monitor.applicants_next_cursor ? (
                    <div className="border-t border-slate-100 px-4 py-3">
                      <button
                        type="button"
                        className="btn-secondary btn-sm"
                        disabled={loadingMore}
                        onClick={() => void loadMoreMonitor()}
                        data-testid="marketing-monitor-load-more"
                      >
                        {loadingMore ? t('common.loading') : 'Ещё заявки'}
                      </button>
                    </div>
                  ) : null}
                </>
              )}
            </section>
          </>
        ) : null}
      </div>
      {campaign ? (
        <MarketingConnectMetaAdvertising
          campaignId={campaign.id}
          open={metaWizardOpen}
          onClose={() => setMetaWizardOpen(false)}
          onConnected={async () => {
            await load()
            setMetaWizardOpen(false)
          }}
          t={t}
        />
      ) : null}
    </PageShell>
  )
}
