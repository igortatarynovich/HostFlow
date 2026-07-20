import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconMessageCircle } from '@tabler/icons-react'
import { listCommunicationThreads, type CommunicationThread } from '../../api/communications'
import { useI18n } from '../../i18n'
import { buildInboxThreadPath } from '../../utils/inboxDeepLinks'

type Props = {
  leadId: string
  /** Optional thread id already known from timeline API. */
  preferredThreadId?: string | null
}

function formatWhen(value?: string | null): string {
  if (!value) return ''
  const ts = Date.parse(value)
  if (!Number.isFinite(ts)) return ''
  return new Date(ts).toLocaleString()
}

/**
 * G13/G15 acceptance: Inquiry shows linked Thread («Переписка») with last preview + open dialog.
 */
export default function SalesInquiryCommunicationSection({ leadId, preferredThreadId }: Props) {
  const { t } = useI18n()
  const [threads, setThreads] = useState<CommunicationThread[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let mounted = true
    const run = async () => {
      setLoading(true)
      try {
        const res = await listCommunicationThreads({
          limit: 20,
          entityType: 'lead',
          entityId: leadId,
          includeArchived: false,
        })
        if (!mounted) return
        const items = Array.isArray(res.items) ? res.items : []
        items.sort(
          (a, b) =>
            Date.parse(String(b.last_message_at || b.updated_at || 0)) -
            Date.parse(String(a.last_message_at || a.updated_at || 0)),
        )
        setThreads(items)
      } catch {
        if (mounted) setThreads([])
      } finally {
        if (mounted) setLoading(false)
      }
    }
    void run()
    return () => {
      mounted = false
    }
  }, [leadId])

  const primary = useMemo(() => {
    const pref = String(preferredThreadId || '').trim()
    if (pref) {
      const hit = threads.find((th) => String(th.id) === pref)
      if (hit) return hit
    }
    return threads[0] || null
  }, [preferredThreadId, threads])

  const preview =
    String(primary?.last_message_preview || '').trim() ||
    String(primary?.subject || '').trim() ||
    null
  const when = formatWhen(primary?.last_message_at || primary?.updated_at)

  return (
    <div className="space-y-2" data-testid="sales-inquiry-comms">
      {loading ? (
        <p className="text-xs text-slate-500">
          {t('app.sales_inquiry.comms.loading', { defaultValue: 'Загрузка переписки…' })}
        </p>
      ) : null}
      {!loading && !primary ? (
        <p className="text-xs text-slate-500">
          {t('app.sales_inquiry.comms.empty', {
            defaultValue: 'Пока нет связанной переписки. Письма из обращения появятся здесь.',
          })}
        </p>
      ) : null}
      {!loading && primary ? (
        <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2.5">
          <div className="flex items-start gap-2">
            <span className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-brand-50 text-brand-700">
              <IconMessageCircle size={16} stroke={1.75} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-slate-900" title={preview || undefined}>
                {preview ||
                  t('app.sales_inquiry.comms.untitled', { defaultValue: 'Диалог без темы' })}
              </p>
              <p className="mt-0.5 text-[11px] text-slate-500">
                {String(primary.channel || '').toUpperCase()}
                {when ? ` · ${when}` : ''}
                {threads.length > 1
                  ? ` · ${t('app.sales_inquiry.comms.more_count', {
                      defaultValue: 'ещё {{count}}',
                      count: threads.length - 1,
                    })}`
                  : ''}
              </p>
            </div>
          </div>
          <div className="mt-2.5">
            <Link
              to={buildInboxThreadPath(primary.id, { channel: 'email' })}
              className="btn-secondary btn-sm inline-flex"
              data-testid="sales-inquiry-open-thread"
            >
              {t('app.sales_inquiry.comms.open_dialog', { defaultValue: 'Открыть диалог' })}
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  )
}
