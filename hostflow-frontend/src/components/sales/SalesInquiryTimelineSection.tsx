import { useCallback, useEffect, useState } from 'react'

import { getLeadTimeline } from '../../api/client'
import { useI18n } from '../../i18n'
import {
  isSalesInquiryTimelineItemVisible,
  salesInquiryTimelineDescription,
  salesInquiryTimelineKindTitle,
  type SalesInquiryTimelineItem,
} from './salesInquiryTimeline'

type Props = {
  leadId: string
  /** Bump to reload after call notes / stage changes. */
  refreshToken?: number
}

function formatAt(iso: string | null | undefined, locale: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Operator timeline: contact, questionnaire, calls, stage changes. */
export default function SalesInquiryTimelineSection({ leadId, refreshToken = 0 }: Props) {
  const { t, locale } = useI18n()
  const [items, setItems] = useState<SalesInquiryTimelineItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!leadId) return
    setLoading(true)
    setError(null)
    try {
      const res = await getLeadTimeline(leadId)
      const raw = Array.isArray(res?.items) ? res.items : []
      setItems(
        raw
          .map((item: Record<string, unknown>) => ({
            at: String(item.at ?? ''),
            kind: String(item.kind || ''),
            source: String(item.source || ''),
            title: item.title != null ? String(item.title) : null,
            description: item.description != null ? String(item.description) : null,
          }))
          .filter(isSalesInquiryTimelineItemVisible),
      )
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.leads.detail.timeline_load_failed', { defaultValue: 'Failed to load history' })
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [leadId, t])

  useEffect(() => {
    void load()
  }, [load, refreshToken])

  if (loading) {
    return (
      <p className="text-sm text-slate-500" data-testid="sales-inquiry-timeline-loading">
        {t('common.loading', { defaultValue: 'Loading…' })}
      </p>
    )
  }

  if (error) {
    return (
      <p className="text-sm text-rose-600" data-testid="sales-inquiry-timeline-error">
        {error}
      </p>
    )
  }

  if (items.length === 0) {
    return (
      <p className="text-sm text-slate-500" data-testid="sales-inquiry-timeline-empty">
        {t('app.leads.detail.timeline_empty', { defaultValue: 'No events yet' })}
      </p>
    )
  }

  return (
    <ul className="space-y-3 border-l-2 border-slate-200 pl-4" data-testid="sales-inquiry-timeline">
      {items.map((item, idx) => {
        const description = salesInquiryTimelineDescription(t, item)
        return (
          <li key={`${item.at}-${item.kind}-${idx}`} className="relative">
            <span
              className="absolute -left-[calc(0.5rem+2px)] top-2 h-2 w-2 rounded-full bg-brand-500"
              aria-hidden
            />
            <div className="text-xs text-slate-500">{formatAt(item.at, locale)}</div>
            <div className="text-sm font-medium text-slate-900">
              {salesInquiryTimelineKindTitle(t, item.kind, item.title)}
            </div>
            {description ? <div className="text-sm text-slate-600">{description}</div> : null}
          </li>
        )
      })}
    </ul>
  )
}
