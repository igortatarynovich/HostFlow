/**
 * Marketing Flight card — status, bindings, actions, recent leads, activity, funnel.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  listAcquisitionActivity,
  type AcquisitionActivityEvent,
} from '../../api/acquisitionActivity'
import { getVacancy } from '../../api/vacancies'
import { listAdditionalServices } from '../../api/additionalServices'
import {
  currentFlight,
  getCampaign,
  launchFlight,
  pauseFlight,
  resumeFlight,
  type Campaign,
} from '../../api/platformCampaigns'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import { useI18n } from '../../i18n'
import { formatDateTime } from '../../utils/dateFormat'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import {
  formatActivityDetailsJson,
  humanizeEventType,
} from '../acquisition/acquisitionActivityPresentation'
import {
  countFlightFunnel,
  formPublicUrl,
  primaryForm,
  primarySource,
  recentSubmissionEvents,
  statusLabel,
  statusTone,
} from './marketingPresentation'

export default function MarketingCampaignDetailPage() {
  const { t, locale } = useI18n()
  const { campaignId = '' } = useParams<{ campaignId: string }>()
  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [events, setEvents] = useState<AcquisitionActivityEvent[]>([])
  const [destinationLabel, setDestinationLabel] = useState<string>('—')
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!campaignId) return
    setLoading(true)
    setError(null)
    try {
      const c = await getCampaign(campaignId)
      setCampaign(c)
      const activity = await listAcquisitionActivity({
        campaign_id: campaignId,
        limit: 100,
      })
      setEvents(activity.items)

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
  const funnel = useMemo(
    () => countFlightFunnel(events, flight?.id),
    [events, flight?.id],
  )
  const recent = useMemo(
    () => recentSubmissionEvents(events, flight?.id, 8),
    [events, flight?.id],
  )

  const flightStatus = flight?.status || 'planned'
  const canLaunch = flightStatus === 'planned'
  const canPause = flightStatus === 'active'
  const canResume = flightStatus === 'paused'

  async function runCommand(kind: 'launch' | 'pause' | 'resume') {
    if (!campaign || !flight) return
    setActing(true)
    setError(null)
    try {
      const fn = kind === 'launch' ? launchFlight : kind === 'pause' ? pauseFlight : resumeFlight
      const result = await fn(campaign.id, flight.id)
      setCampaign(result.campaign)
      const activity = await listAcquisitionActivity({
        campaign_id: campaign.id,
        limit: 100,
      })
      setEvents(activity.items)
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

  const publicUrl = formPublicUrl(form?.public_slug)
  const sourceLabel =
    source?.name || source?.provider || (form ? 'Публичная форма' : '—')

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={campaign?.name || t('app.marketing.detail.title', { defaultValue: 'Кампания' })}
          subtitle={
            flight
              ? `Flight · ${statusLabel(flight.status)}`
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
                    onClick={() => void runCommand('launch')}
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
                    onClick={() => void runCommand('pause')}
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
                    onClick={() => void runCommand('resume')}
                    data-testid="marketing-flight-resume"
                  >
                    Возобновить
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
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs ring-1 ring-inset ${statusTone(campaign.status)}`}
                  >
                    {statusLabel(campaign.status)}
                  </span>
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Форма</div>
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
                <div className="text-xs text-slate-500">Источник</div>
                <div className="mt-1 text-sm font-medium text-slate-900">{sourceLabel}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Куда идут заявки</div>
                <div className="mt-1 text-sm font-medium text-slate-900">{destinationLabel}</div>
                {flight?.starts_at ? (
                  <div className="mt-1 text-xs text-slate-500">
                    Запуск: {formatDateTime(flight.starts_at, locale)}
                  </div>
                ) : null}
              </div>
            </section>

            <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: 'Получено', value: funnel.received },
                { label: 'Направлено', value: funnel.routed },
                { label: 'Ошибки маршрутизации', value: funnel.routingFailed },
                { label: 'Дубликаты', value: funnel.duplicates },
              ].map((kpi) => (
                <div key={kpi.label} className="rounded-xl border border-slate-200 bg-white px-3 py-3">
                  <div className="text-xs text-slate-500">{kpi.label}</div>
                  <div className="mt-1 text-2xl font-semibold text-slate-900">{kpi.value}</div>
                </div>
              ))}
            </section>

            <section className="rounded-xl border border-slate-200 bg-white">
              <div className="border-b border-slate-100 px-4 py-3">
                <h2 className="text-sm font-semibold text-slate-900">Последние заявки</h2>
              </div>
              {!recent.length ? (
                <p className="px-4 py-6 text-sm text-slate-500">
                  Пока нет заявок. Отправьте тестовую форму по публичной ссылке.
                </p>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {recent.map((e) => (
                    <li key={e.id} className="px-4 py-3 text-sm">
                      <div className="font-medium text-slate-900">Заявка получена</div>
                      <div className="mt-0.5 text-xs text-slate-500">
                        {formatDateTime(e.occurred_at, locale)}
                        {e.submission_id ? ` · ${e.submission_id.slice(0, 8)}…` : ''}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded-xl border border-slate-200 bg-white">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <h2 className="text-sm font-semibold text-slate-900">Activity Timeline</h2>
                <Link
                  to={`${CRM_APP_PATHS.acquisitionActivity}?campaign_id=${encodeURIComponent(campaign.id)}${
                    flight ? `&flight_id=${encodeURIComponent(flight.id)}` : ''
                  }`}
                  className="text-xs font-medium text-brand-600"
                >
                  Полный таймлайн →
                </Link>
              </div>
              {!events.length ? (
                <p className="px-4 py-6 text-sm text-slate-500">Событий пока нет.</p>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {events.slice(0, 25).map((e) => (
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
                      </button>
                      {expandedId === e.id ? (
                        <pre className="mt-2 overflow-x-auto rounded bg-slate-50 p-2 text-xs text-slate-700">
                          {formatActivityDetailsJson(e)}
                        </pre>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        ) : null}
      </div>
    </PageShell>
  )
}
