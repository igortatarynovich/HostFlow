/**
 * Stage 3E PR-4 — Thin operator UI for Acquisition Activity Timeline.
 * Read-only: displays GET /platform/acquisition-activity. No runtime actions.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  listAcquisitionActivity,
  type AcquisitionActivityCursor,
  type AcquisitionActivityEvent,
} from '../../api/acquisitionActivity'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader, Toolbar } from '../../components/layout'
import { useI18n } from '../../i18n'
import { formatDateTime } from '../../utils/dateFormat'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import {
  formatActivityDetailsJson,
  humanizeEventType,
  mergeActivityPages,
} from './acquisitionActivityPresentation'

function RefChips({ event }: { event: AcquisitionActivityEvent }) {
  const refs: Array<{ label: string; value: string }> = []
  if (event.flight_id) refs.push({ label: 'flight', value: event.flight_id })
  if (event.endpoint_id) refs.push({ label: 'endpoint', value: event.endpoint_id })
  if (event.submission_id) refs.push({ label: 'submission', value: event.submission_id })
  if (event.result_id) refs.push({ label: 'result', value: event.result_id })
  if (event.outcome_id) refs.push({ label: 'outcome', value: event.outcome_id })
  if (!refs.length) return null
  return (
    <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
      {refs.map((r) => (
        <span key={`${r.label}:${r.value}`} className="rounded bg-slate-100 px-1.5 py-0.5 font-mono">
          {r.label}: {r.value}
        </span>
      ))}
    </div>
  )
}

export default function AcquisitionActivityTimelinePage() {
  const { t, locale } = useI18n()
  const [searchParams, setSearchParams] = useSearchParams()
  const appliedCampaignId = (searchParams.get('campaign_id') || '').trim()
  const appliedFlightId = (searchParams.get('flight_id') || '').trim()

  const [draftCampaignId, setDraftCampaignId] = useState(appliedCampaignId)
  const [draftFlightId, setDraftFlightId] = useState(appliedFlightId)
  const [items, setItems] = useState<AcquisitionActivityEvent[]>([])
  const [nextCursor, setNextCursor] = useState<AcquisitionActivityCursor | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  useEffect(() => {
    setDraftCampaignId(appliedCampaignId)
    setDraftFlightId(appliedFlightId)
  }, [appliedCampaignId, appliedFlightId])

  const applyFilters = useCallback(() => {
    const params = new URLSearchParams()
    const campaign = draftCampaignId.trim()
    const flight = draftFlightId.trim()
    if (campaign) params.set('campaign_id', campaign)
    if (flight) params.set('flight_id', flight)
    // Filter change always resets pagination state before the URL-driven reload.
    setItems([])
    setNextCursor(null)
    setExpandedId(null)
    setError(null)
    setSearchParams(params, { replace: true })
  }, [draftCampaignId, draftFlightId, setSearchParams])

  const loadPage = useCallback(
    async (opts?: { append?: boolean; cursor?: AcquisitionActivityCursor | null }) => {
      if (!appliedCampaignId) {
        setItems([])
        setNextCursor(null)
        setError(null)
        setLoading(false)
        return
      }
      setLoading(true)
      setError(null)
      try {
        const res = await listAcquisitionActivity({
          campaign_id: appliedCampaignId,
          flight_id: appliedFlightId || undefined,
          limit: 50,
          ...(opts?.append && opts.cursor
            ? {
                after_occurred_at: opts.cursor.occurred_at,
                after_id: opts.cursor.id,
              }
            : {}),
        })
        setItems((prev) => (opts?.append ? mergeActivityPages(prev, res.items) : res.items))
        setNextCursor(res.next_cursor)
      } catch (err: unknown) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('app.acquisition_activity.errors.load', {
              defaultValue: 'Failed to load activity timeline',
            }),
            t,
          ),
        )
        if (!opts?.append) {
          setItems([])
          setNextCursor(null)
        }
      } finally {
        setLoading(false)
      }
    },
    [appliedCampaignId, appliedFlightId, t],
  )

  useEffect(() => {
    void loadPage()
  }, [loadPage])

  const canLoadMore = useMemo(() => Boolean(nextCursor) && !loading, [nextCursor, loading])

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          kind="browse"
          secondaryActions={
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => void loadPage()}
              disabled={loading || !appliedCampaignId}
            >
              {loading ? t('common.loading') : t('common.actions.refresh')}
            </button>
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pb-4">
        {error ? <ErrorRecoveryBanner info={error} onRetry={() => void loadPage()} /> : null}

        <Toolbar>
          <div className="flex flex-wrap gap-3">
            <label className="flex flex-col gap-1 text-sm">
              {t('app.acquisition_activity.filters.campaign_id', {
                defaultValue: 'Campaign id',
              })}
              <input
                className="input w-80 font-mono text-xs"
                value={draftCampaignId}
                onChange={(e) => setDraftCampaignId(e.target.value)}
                placeholder="UUID"
                data-testid="acquisition-activity-campaign-id"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              {t('app.acquisition_activity.filters.flight_id', {
                defaultValue: 'Flight id (optional)',
              })}
              <input
                className="input w-80 font-mono text-xs"
                value={draftFlightId}
                onChange={(e) => setDraftFlightId(e.target.value)}
                placeholder="UUID"
              />
            </label>
            <div className="flex items-end">
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={loading || !draftCampaignId.trim()}
                onClick={applyFilters}
              >
                {t('common.actions.apply', { defaultValue: 'Apply' })}
              </button>
            </div>
          </div>
        </Toolbar>

        {!appliedCampaignId ? (
          <p className="text-sm text-slate-600" data-testid="acquisition-activity-empty-campaign">
            {t('app.acquisition_activity.empty_campaign', {
              defaultValue: 'Enter a Campaign id to load the timeline.',
            })}
          </p>
        ) : null}

        {appliedCampaignId && loading ? (
          <p className="text-sm text-slate-500" data-testid="acquisition-activity-loading">
            {t('common.loading')}
          </p>
        ) : null}

        {appliedCampaignId && !loading && items.length === 0 && !error ? (
          <p className="text-sm text-slate-600" data-testid="acquisition-activity-empty">
            {t('app.acquisition_activity.empty', {
              defaultValue: 'No activity events for this filter.',
            })}
          </p>
        ) : null}

        <ul className="divide-y divide-slate-200 rounded-md border border-slate-200 bg-white">
          {items.map((event) => {
            const open = expandedId === event.id
            return (
              <li key={event.id} className="px-4 py-3" data-testid={`acquisition-activity-row-${event.id}`}>
                <button
                  type="button"
                  className="flex w-full items-start justify-between gap-3 text-left"
                  onClick={() => setExpandedId(open ? null : event.id)}
                >
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-slate-900">
                      {humanizeEventType(event.event_type)}
                    </div>
                    <div className="mt-0.5 text-xs text-slate-500">
                      {formatDateTime(event.occurred_at, locale)} · {event.actor_type}
                      {event.provider ? ` · ${event.provider}` : ''}
                    </div>
                    <RefChips event={event} />
                  </div>
                  <span className="shrink-0 text-xs text-slate-400">{open ? 'Hide' : 'Details'}</span>
                </button>
                {open ? (
                  <pre
                    className="mt-2 overflow-x-auto rounded bg-slate-50 p-2 text-xs text-slate-700"
                    data-testid={`acquisition-activity-payload-${event.id}`}
                  >
                    {formatActivityDetailsJson(event)}
                  </pre>
                ) : null}
              </li>
            )
          })}
        </ul>

        {canLoadMore ? (
          <div>
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={loading}
              data-testid="acquisition-activity-load-more"
              onClick={() => void loadPage({ append: true, cursor: nextCursor })}
            >
              {t('common.actions.load_more', { defaultValue: 'Load more' })}
            </button>
          </div>
        ) : null}
      </div>
    </PageShell>
  )
}
