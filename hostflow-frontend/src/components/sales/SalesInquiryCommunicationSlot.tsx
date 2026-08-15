import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listCommunicationThreads, type CommunicationThread } from '../../api/communications'
import { useI18n } from '../../i18n'
import { buildInboxHubPath, buildInboxThreadPath } from '../../utils/inboxDeepLinks'

type Props = {
  inquiryId: string
}

/** D3 communication slot — public Communication API only; not a second Inbox. */
export function SalesInquiryCommunicationSlot({ inquiryId }: Props) {
  const { t } = useI18n()
  const [threads, setThreads] = useState<CommunicationThread[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const id = inquiryId.trim()
    if (!id) return
    let mounted = true
    const run = async () => {
      setLoading(true)
      try {
        const res = await listCommunicationThreads({
          entityType: 'sales_inquiry',
          entityId: id,
          limit: 20,
          includeArchived: false,
        })
        if (!mounted) return
        setThreads(Array.isArray(res.items) ? res.items : [])
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
  }, [inquiryId])

  const newest = threads[0] ?? null

  return (
    <div className="space-y-2">
      <p className="text-sm text-slate-600">
        {loading
          ? t('app.sales_inquiry.communication.loading', { defaultValue: 'Загрузка переписки…' })
          : newest
            ? t('app.sales_inquiry.communication.linked', {
                defaultValue: 'Переписка по обращению',
              })
            : t('app.sales_inquiry.communication.empty', {
                defaultValue: 'Нет связанной переписки',
              })}
      </p>
      {newest ? (
        <Link
          to={buildInboxThreadPath(newest.id)}
          className="text-sm font-medium text-brand-700 hover:underline"
        >
          {t('app.sales_inquiry.communication.open_thread', { defaultValue: 'Открыть в Inbox' })}
        </Link>
      ) : (
        <Link to={buildInboxHubPath()} className="text-sm font-medium text-brand-700 hover:underline">
          {t('app.sales_inquiry.communication.open_inbox', { defaultValue: 'Открыть Inbox' })}
        </Link>
      )}
    </div>
  )
}
