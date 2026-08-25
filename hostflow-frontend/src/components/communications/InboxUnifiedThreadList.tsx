import { useState } from 'react'
import clsx from 'clsx'
import { NavLink } from 'react-router-dom'
import { IconMail, IconMessageCircle } from '@tabler/icons-react'
import type { CommunicationThread } from '../../api/communications'
import { useI18n } from '../../i18n'
import { isCommunicationThreadUnlinked } from '../../utils/communicationThreadUnlinked'
import { threadDecisionTier, threadHoursWaitingForReply, threadNeedsOutboundReply, threadSlaOverdue } from '../../utils/communicationThreadDecision'
import { inboxContextQueryString, type InboxListQuery } from '../../utils/inboxUrlQuery'

/** C1 working queues (+ all). Thread is the work object — filters are Thread queues. */
export type InboxHubFilter =
  | 'all'
  | 'requires_reply'
  | 'new_inbound'
  | 'delivery_errors'
  | 'unresolved'
  | 'assigned_to_me'
  | 'unassigned'
  | 'waiting_for_reply'
  | 'closed'
  /** Legacy client-only (deep-link compat). Prefer platform queues. */
  | 'unlinked'

export type InboxHubSort = 'activity' | 'sla_due'

export function isEmailThread(th: CommunicationThread): boolean {
  return String(th.channel || '').toLowerCase() === 'email'
}

function isUiPinned(th: CommunicationThread): boolean {
  return Boolean((th.thread_meta || {})?.ui_pinned)
}

/** Short channel label for unified list (EMAIL / TELEGRAM / …). */
export function inboxChannelBadgeLabel(th: CommunicationThread): string {
  const c = String(th.channel || '').trim().toLowerCase()
  if (c === 'email') return 'EMAIL'
  if (c === 'telegram') return 'TELEGRAM'
  if (!c) return '—'
  return c.replace(/_/g, ' ').toUpperCase()
}

export function threadTitle(th: CommunicationThread): string {
  return String(th.subject || '').trim() || String(th.last_message_preview || '').trim() || th.id
}

export function threadRecencyMs(th: CommunicationThread): number {
  const raw = th.last_message_at || th.updated_at
  if (!raw) return 0
  const ms = Date.parse(String(raw))
  return Number.isFinite(ms) ? ms : 0
}

function parseMs(iso?: string | null): number {
  if (!iso) return 0
  const t = Date.parse(String(iso))
  return Number.isFinite(t) ? t : 0
}

function formatHubTime(iso?: string | null): string {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'short', timeStyle: 'short' }).format(new Date(iso))
  } catch {
    return String(iso)
  }
}

function formatMinutesDelta(totalMinutes: number, t: ReturnType<typeof useI18n>['t']): string {
  const mins = Math.max(0, Math.floor(totalMinutes))
  const days = Math.floor(mins / (60 * 24))
  const hours = Math.floor((mins % (60 * 24)) / 60)
  const minutes = mins % 60
  if (days > 0) return t('app.communications_inbox_hub.sla_in_days_hours', { defaultValue: '{d}d {h}h', values: { d: days, h: hours } })
  if (hours > 0) return t('app.communications_inbox_hub.sla_in_hours_minutes', { defaultValue: '{h}h {m}m', values: { h: hours, m: minutes } })
  return t('app.communications_inbox_hub.sla_in_minutes', { defaultValue: '{m}m', values: { m: minutes } })
}

function threadTo(
  threadLinkPrefix: string,
  th: CommunicationThread,
  listQuery: InboxListQuery | null | undefined,
  scopeCandidate: string,
): string {
  const path = `${threadLinkPrefix}/${th.id}`
  if (!listQuery) {
    if (scopeCandidate.length > 0) return `${path}?candidateId=${encodeURIComponent(scopeCandidate)}`
    return path
  }
  const q: InboxListQuery = {
    ...listQuery,
    candidateId: scopeCandidate || listQuery.candidateId,
  }
  return `${path}${inboxContextQueryString(q)}`
}

type Props = {
  threads: CommunicationThread[]
  hubFilter: InboxHubFilter
  onHubFilterChange: (f: InboxHubFilter) => void
  hasMessages: boolean
  hasEmail: boolean
  /** Base path for thread links, e.g. `/app/inbox/threads` or use classic `/app/communications/threads` */
  threadLinkPrefix: string
  /** When set, only threads linked to this candidate appear in the list; thread URLs keep `?candidateId=` for sidebar parity. */
  linkedCandidateId?: string | null
  selectedThreadId?: string | null
  /** Hide the section heading — hub focuses on the list + filters only. */
  hideSectionHeading?: boolean
  /** Preserve channel/folder/q in thread links (unified inbox URL state). */
  listQuery?: InboxListQuery | null
  selectedThreadIds?: string[]
  onToggleThreadSelection?: (threadId: string, nextChecked: boolean) => void
  onToggleAllVisibleSelection?: (threadIds: string[], nextChecked: boolean) => void
}

const FILTER_KEYS: InboxHubFilter[] = [
  'all',
  'requires_reply',
  'new_inbound',
  'delivery_errors',
  'unresolved',
  'assigned_to_me',
  'unassigned',
  'waiting_for_reply',
  'closed',
]

/** Maps hub UI filter → platform `queue=` param (undefined = no server queue). */
export function inboxHubFilterToQueue(filter: InboxHubFilter): string | undefined {
  if (filter === 'all' || filter === 'unlinked') return undefined
  return filter
}

export default function InboxUnifiedThreadList({
  threads,
  hubFilter,
  onHubFilterChange,
  hasMessages,
  hasEmail,
  threadLinkPrefix,
  linkedCandidateId,
  selectedThreadId,
  hideSectionHeading,
  listQuery,
  selectedThreadIds,
  onToggleThreadSelection,
  onToggleAllVisibleSelection,
}: Props) {
  const { t } = useI18n()
  const [hubSort, setHubSort] = useState<InboxHubSort>('activity')
  const scopeCandidate = String(linkedCandidateId || '').trim()

  const unifiedThreads = (() => {
    let base = threads.filter((th) => {
      if (isEmailThread(th)) return hasEmail
      return hasMessages
    })
    if (scopeCandidate) {
      base = base.filter((th) => String(th.linked_candidate_id || '').trim() === scopeCandidate)
    }
    // Platform queues are applied server-side via `queue=`; only legacy unlinked stays client-side.
    const filtered =
      hubFilter === 'unlinked' ? base.filter((th) => isCommunicationThreadUnlinked(th)) : base

    const pinThen = (a: CommunicationThread, b: CommunicationThread) => {
      const pa = isUiPinned(a) ? 1 : 0
      const pb = isUiPinned(b) ? 1 : 0
      if (pa !== pb) return pb - pa
      return 0
    }

    if (hubSort === 'sla_due') {
      return [...filtered].sort((a, b) => {
        const p = pinThen(a, b)
        if (p !== 0) return p
        const ao = threadSlaOverdue(a) ? 0 : 1
        const bo = threadSlaOverdue(b) ? 0 : 1
        if (ao !== bo) return ao - bo
        const ad = parseMs(a.sla_due_at) || Number.POSITIVE_INFINITY
        const bd = parseMs(b.sla_due_at) || Number.POSITIVE_INFINITY
        if (ad !== bd) return ad - bd
        return threadRecencyMs(b) - threadRecencyMs(a)
      })
    }
    return [...filtered].sort((a, b) => {
      const p = pinThen(a, b)
      if (p !== 0) return p
      return threadRecencyMs(b) - threadRecencyMs(a)
    })
  })()
  const selectedSet = new Set((selectedThreadIds || []).map((x) => String(x)))
  const selectableIds = unifiedThreads.map((th) => String(th.id))
  const selectableCount = selectableIds.length
  const selectedVisibleCount = selectableIds.filter((id) => selectedSet.has(id)).length
  const allVisibleSelected = selectableCount > 0 && selectedVisibleCount === selectableCount

  return (
    <div>
      {!hideSectionHeading && (
        <h2 className="text-base font-semibold text-slate-900">{t('app.communications_inbox_hub.unified_section_title')}</h2>
      )}

      <div className={clsx('flex flex-wrap items-center justify-between gap-2', !hideSectionHeading && 'mt-3')}>
        <div className="flex flex-wrap gap-1">
          {FILTER_KEYS.map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => onHubFilterChange(key)}
              className={clsx(
                'btn-secondary btn-xs',
                hubFilter === key && 'border-brand-600 bg-brand-50 text-brand-800',
              )}
            >
              {key === 'all' && t('app.communications_inbox_hub.unified_filter_all', { defaultValue: 'All' })}
              {key === 'requires_reply' &&
                t('app.communications_inbox_hub.queue_requires_reply', { defaultValue: 'Requires reply' })}
              {key === 'new_inbound' &&
                t('app.communications_inbox_hub.queue_new_inbound', { defaultValue: 'New inbound' })}
              {key === 'delivery_errors' &&
                t('app.communications_inbox_hub.queue_delivery_errors', { defaultValue: 'Delivery errors' })}
              {key === 'unresolved' &&
                t('app.communications_inbox_hub.queue_unresolved', { defaultValue: 'Unresolved' })}
              {key === 'assigned_to_me' &&
                t('app.communications_inbox_hub.queue_assigned_to_me', { defaultValue: 'Assigned to me' })}
              {key === 'unassigned' &&
                t('app.communications_inbox_hub.queue_unassigned', { defaultValue: 'Unassigned' })}
              {key === 'waiting_for_reply' &&
                t('app.communications_inbox_hub.queue_waiting_for_reply', { defaultValue: 'Waiting for reply' })}
              {key === 'closed' && t('app.communications_inbox_hub.queue_closed', { defaultValue: 'Closed' })}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          {onToggleAllVisibleSelection && selectableCount > 0 && (
            <label className="inline-flex items-center gap-1.5 text-[11px] font-medium text-slate-600">
              <input
                type="checkbox"
                className="h-3.5 w-3.5 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                checked={allVisibleSelected}
                onChange={(e) => onToggleAllVisibleSelection(selectableIds, e.target.checked)}
              />
              {t('app.communications_inbox_hub.bulk.select_visible', {
                defaultValue: 'Select visible ({count})',
                values: { count: selectableCount },
              })}
            </label>
          )}
          <span className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
            {t('app.communications_inbox_hub.sort_label')}
          </span>
          <select
            className="input max-w-[11rem] py-1 text-xs"
            value={hubSort}
            onChange={(e) => setHubSort(e.target.value as InboxHubSort)}
          >
            <option value="activity">{t('app.communications_inbox_hub.sort_last_activity')}</option>
            <option value="sla_due">{t('app.communications_inbox_hub.sort_sla_due')}</option>
          </select>
        </div>
      </div>

      {unifiedThreads.length === 0 ? (
        <p className="mt-6 text-sm text-slate-500">{t('app.communications_inbox_hub.unified_empty')}</p>
      ) : (
        <ul className="mt-4 divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          {unifiedThreads.map((th) => {
            const email = isEmailThread(th)
            const unread = Math.max(0, Number(th.unread_count || 0))
            const unlinked = isCommunicationThreadUnlinked(th)
            const channelBadge = inboxChannelBadgeLabel(th)
            const tier = threadDecisionTier(th)
            const waitH = threadHoursWaitingForReply(th)
            const slaDueMs = parseMs(th.sla_due_at)
            const hasSlaDeadline = slaDueMs > 0
            const slaDeltaMinutes = hasSlaDeadline ? Math.round((slaDueMs - Date.now()) / 60000) : null
            const isSlaOverdue = hasSlaDeadline && (slaDeltaMinutes ?? 0) < 0
            const slaChipLabel =
              hasSlaDeadline && slaDeltaMinutes !== null
                ? isSlaOverdue
                  ? t('app.communications_inbox_hub.sla_overdue_by', {
                      defaultValue: 'SLA overdue {delta}',
                      values: { delta: formatMinutesDelta(Math.abs(slaDeltaMinutes), t) },
                    })
                  : t('app.communications_inbox_hub.sla_due_in', {
                      defaultValue: 'SLA in {delta}',
                      values: { delta: formatMinutesDelta(slaDeltaMinutes, t) },
                    })
                : null
            const waitLine =
              threadNeedsOutboundReply(th) && waitH !== null
                ? waitH < 1
                  ? t('app.communications.email.wait_under_1h', { defaultValue: '<1h no reply' })
                  : t('app.communications.email.wait_hours', { defaultValue: '{n}h no reply', values: { n: waitH } })
                : threadNeedsOutboundReply(th)
                  ? t('app.communications.email.wait_reply_short', { defaultValue: 'Needs reply' })
                  : ''
            const to = threadTo(threadLinkPrefix, th, listQuery, scopeCandidate)
            const active = selectedThreadId === th.id
            return (
              <li key={th.id}>
                <div
                  className={clsx(
                    'flex gap-2 px-3 py-3 transition-colors hover:bg-slate-50',
                    active && 'bg-brand-50/80 ring-1 ring-inset ring-brand-200',
                  )}
                >
                  {onToggleThreadSelection ? (
                    <label className="mt-1 inline-flex shrink-0 items-center" title={t('app.communications_inbox_hub.bulk.select_one', { defaultValue: 'Select thread' })}>
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                        checked={selectedSet.has(String(th.id))}
                        onChange={(e) => onToggleThreadSelection(String(th.id), e.target.checked)}
                      />
                    </label>
                  ) : null}
                <NavLink
                  to={to}
                  className="flex min-w-0 flex-1 gap-3"
                >
                  <div className="mt-0.5 shrink-0 text-slate-400">
                    {email ? <IconMail size={18} stroke={1.75} /> : <IconMessageCircle size={18} stroke={1.75} />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={clsx(
                          'rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                          email ? 'bg-violet-100 text-violet-900' : 'bg-sky-100 text-sky-900',
                        )}
                      >
                        {channelBadge}
                      </span>
                      {isUiPinned(th) && (
                        <span className="text-[10px] font-semibold uppercase text-slate-500">
                          {t('app.communications_inbox_hub.pinned_badge', { defaultValue: 'Pinned' })}
                        </span>
                      )}
                      {unlinked && (
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-900">
                          {t('app.communications_messages.dialogs.link_filter_unlinked')}
                        </span>
                      )}
                      {unread > 0 && (
                        <span className="rounded-md bg-brand-600 px-1.5 py-0.5 text-[11px] font-semibold text-white">{unread}</span>
                      )}
                      {slaChipLabel && (
                        <span
                          className={clsx(
                            'rounded-md px-1.5 py-0.5 text-[10px] font-semibold',
                            isSlaOverdue ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-900',
                          )}
                          title={
                            th.sla_due_at
                              ? t('app.communications_inbox_hub.sla_due_exact', {
                                  defaultValue: 'SLA due: {when}',
                                  values: { when: formatHubTime(th.sla_due_at) },
                                })
                              : undefined
                          }
                        >
                          {slaChipLabel}
                        </span>
                      )}
                      {tier === 'needs_reply' && (
                        <span className="text-sm leading-none" title={t('app.communications.email.tier_needs_reply', { defaultValue: 'Needs reply' })}>
                          🟡
                        </span>
                      )}
                    </div>
                    <div className="mt-1 truncate text-sm font-semibold text-slate-900">{threadTitle(th)}</div>
                    <div className="mt-0.5 truncate text-xs text-slate-500">{th.last_message_preview || '—'}</div>
                    {waitLine && <div className="mt-0.5 text-[11px] text-slate-600">{waitLine}</div>}
                    <div className="mt-1 text-[11px] text-slate-400">
                      {formatHubTime(th.last_message_at || th.updated_at)}
                      {th.channel && th.channel !== 'email' ? ` · ${String(th.channel)}` : ''}
                    </div>
                  </div>
                </NavLink>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
