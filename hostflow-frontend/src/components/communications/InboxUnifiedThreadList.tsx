import { useState } from 'react'
import clsx from 'clsx'
import { NavLink } from 'react-router-dom'
import { IconMail, IconMessageCircle } from '@tabler/icons-react'
import type { CommunicationThread } from '../../api/communications'
import { useI18n } from '../../i18n'
import { isCommunicationThreadUnlinked } from '../../utils/communicationThreadUnlinked'
import { opsModeFromThread } from '../../utils/communicationsOpsMode'
import { threadDecisionTier, threadHoursWaitingForReply, threadNeedsOutboundReply, threadSlaOverdue } from '../../utils/communicationThreadDecision'
import { inboxContextQueryString, type InboxListQuery } from '../../utils/inboxUrlQuery'

export type InboxHubFilter = 'all' | 'unread' | 'unlinked' | 'sla' | 'in_work' | 'later'

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
}

const FILTER_KEYS: InboxHubFilter[] = ['all', 'unread', 'unlinked', 'sla', 'in_work', 'later']

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
    const filtered =
      hubFilter === 'unread'
        ? base.filter((th) => Number(th.unread_count || 0) > 0)
        : hubFilter === 'unlinked'
          ? base.filter((th) => isCommunicationThreadUnlinked(th))
          : hubFilter === 'sla'
            ? base.filter((th) => threadSlaOverdue(th))
            : hubFilter === 'in_work'
              ? base.filter((th) => opsModeFromThread(th) === 'in_work')
              : hubFilter === 'later'
                ? base.filter((th) => opsModeFromThread(th) === 'later')
                : base

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
              {key === 'all' && t('app.communications_inbox_hub.unified_filter_all')}
              {key === 'unread' && t('app.communications_inbox_hub.unified_filter_unread')}
              {key === 'unlinked' && t('app.communications_inbox_hub.unified_filter_unlinked')}
              {key === 'sla' && t('app.communications_inbox_hub.unified_filter_sla')}
              {key === 'in_work' && t('app.communications_inbox_hub.unified_filter_in_work')}
              {key === 'later' && t('app.communications_inbox_hub.unified_filter_later')}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
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
                <NavLink
                  to={to}
                  className={clsx(
                    'flex gap-3 px-4 py-3 transition-colors hover:bg-slate-50',
                    active && 'bg-brand-50/80 ring-1 ring-inset ring-brand-200',
                  )}
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
                      {tier === 'sla_overdue' && (
                        <span className="text-sm leading-none" title={t('app.communications.email.tier_sla_overdue', { defaultValue: 'SLA overdue' })}>
                          🔴
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
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
