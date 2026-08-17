import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listCommunicationThreads, type CommunicationThread } from '../../api/communications'
import { useI18n } from '../../i18n'
import { buildInboxHubPath, buildInboxThreadPath } from '../../utils/inboxDeepLinks'

type Props = {
  companyId: string
}

/** D7 communication slot — public Communication API only; fold via company. */
export function VacancyCommunicationSlot({ companyId }: Props) {
  const { t } = useI18n()
  const [threads, setThreads] = useState<CommunicationThread[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const id = companyId.trim()
    if (!id) return
    let mounted = true
    const run = async () => {
      setLoading(true)
      try {
        const res = await listCommunicationThreads({
          entityType: 'company',
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
  }, [companyId])

  const newest = threads[0] ?? null

  return (
    <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-sm font-semibold text-slate-900">
        {t('app.entity_workspace.slot.communication', { defaultValue: 'Коммуникация' })}
      </p>
      <p className="text-sm text-slate-600">
        {loading
          ? t('app.vacancies.communication.loading', { defaultValue: 'Загрузка переписки…' })
          : newest
            ? t('app.vacancies.communication.linked', {
                defaultValue: 'Переписка по клиенту вакансии',
              })
            : t('app.vacancies.communication.empty', {
                defaultValue: 'Нет связанной переписки',
              })}
      </p>
      {newest ? (
        <Link
          to={buildInboxThreadPath(newest.id)}
          className="text-sm font-medium text-brand-700 hover:underline"
        >
          {t('app.vacancies.communication.open_thread', { defaultValue: 'Открыть в Inbox' })}
        </Link>
      ) : (
        <Link to={buildInboxHubPath()} className="text-sm font-medium text-brand-700 hover:underline">
          {t('app.vacancies.communication.open_inbox', { defaultValue: 'Открыть Inbox' })}
        </Link>
      )}
    </div>
  )
}
