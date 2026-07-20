import { Link } from 'react-router-dom'
import { buildInboxHubPath, buildInboxThreadPath } from '../../utils/inboxDeepLinks'
import { useI18n } from '../../i18n'

export type BusinessTimelineItem = {
  id: string
  title: string
  description?: string | null
  at: string
  href?: string | null
  kind?: string
}

export type BusinessTimelinePanelProps = {
  items: BusinessTimelineItem[]
  primaryThreadId?: string | null
  emptyLabel?: string
  title?: string
  testId?: string
}

export function BusinessTimelinePanel({
  items,
  primaryThreadId,
  emptyLabel,
  title,
  testId = 'business-timeline',
}: BusinessTimelinePanelProps) {
  const { t } = useI18n()
  const threadHref = primaryThreadId ? buildInboxThreadPath(primaryThreadId) : buildInboxHubPath()

  return (
    <div className="space-y-3" data-testid={testId}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
          {title || t('app.business_timeline.title', { defaultValue: 'История' })}
        </p>
        <Link to={threadHref} className="text-xs font-medium text-brand-700 hover:underline">
          {primaryThreadId
            ? t('app.business_timeline.open_thread', { defaultValue: 'Открыть переписку' })
            : t('app.business_timeline.open_inbox', { defaultValue: 'Открыть Inbox' })}
        </Link>
      </div>
      {items.length > 0 ? (
        <ul className="space-y-2 text-sm">
          {items.map((item) => (
            <li key={item.id} className="border-l-2 border-slate-200 pl-3">
              {item.href ? (
                <Link
                  to={item.href}
                  className="font-medium text-slate-800 hover:text-brand-700 hover:underline"
                >
                  {item.title}
                </Link>
              ) : (
                <p className="font-medium text-slate-800">{item.title}</p>
              )}
              {item.description ? <p className="text-xs text-slate-500">{item.description}</p> : null}
              <p className="text-[10px] text-slate-400">{item.at}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">
          {emptyLabel ||
            t('app.business_timeline.empty', {
              defaultValue: 'Пока нет бизнес-событий.',
            })}
        </p>
      )}
    </div>
  )
}

export function mapTimelineApiItems(
  items: Array<Record<string, unknown>>,
  locale: string,
): BusinessTimelineItem[] {
  const dateLocale = locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : 'en-US'
  return items.slice(0, 60).map((ev, idx) => {
    const atRaw = String(ev.at || '')
    let atLabel = atRaw
    try {
      atLabel = atRaw
        ? new Date(atRaw).toLocaleString(dateLocale, {
            day: 'numeric',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit',
          })
        : ''
    } catch {
      /* keep raw */
    }
    const threadId = String(ev.thread_id || '').trim()
    const href =
      (typeof ev.href === 'string' && ev.href) ||
      (threadId ? buildInboxThreadPath(threadId) : null)
    return {
      id: `${atRaw}-${idx}-${String(ev.kind || ev.title || 'ev')}`,
      title: String(ev.title || ev.kind || 'Событие'),
      description: ev.description != null ? String(ev.description) : null,
      at: atLabel,
      href,
      kind: ev.kind != null ? String(ev.kind) : undefined,
    }
  })
}
