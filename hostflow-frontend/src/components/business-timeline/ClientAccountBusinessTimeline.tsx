import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getClientAccountTimeline } from '../../api/client'
import {
  BusinessTimelinePanel,
  mapTimelineApiItems,
  type BusinessTimelineItem,
} from '../business-timeline/BusinessTimelinePanel'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { servicesWorkspacePath } from '../../modules/services/utils'
import { useI18n } from '../../i18n'

type Props = {
  clientAccountId: string
  companyId: string
  createdAt?: string
  updatedAt?: string
}

function fmtDateTime(value?: string) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

export function ClientAccountBusinessTimeline({
  clientAccountId,
  companyId,
  createdAt,
  updatedAt,
}: Props) {
  const { t, locale } = useI18n()
  const [items, setItems] = useState<BusinessTimelineItem[]>([])
  const [primaryThreadId, setPrimaryThreadId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!clientAccountId) {
      setItems([])
      setPrimaryThreadId(null)
      return
    }
    let mounted = true
    setLoading(true)
    getClientAccountTimeline(clientAccountId)
      .then((data) => {
        if (!mounted) return
        const rows = Array.isArray((data as { items?: unknown[] })?.items)
          ? ((data as { items: Array<Record<string, unknown>> }).items)
          : []
        setItems(mapTimelineApiItems(rows, locale))
        setPrimaryThreadId(String((data as { primary_thread_id?: string })?.primary_thread_id || '') || null)
      })
      .catch(() => {
        if (mounted) {
          setItems([])
          setPrimaryThreadId(null)
        }
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [clientAccountId, locale])

  return (
    <div className="space-y-4 text-sm text-slate-600">
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.companies.detail.workspace.activity.created')}
          </p>
          <p className="mt-1">{fmtDateTime(createdAt)}</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.companies.detail.workspace.activity.updated')}
          </p>
          <p className="mt-1">{fmtDateTime(updatedAt)}</p>
        </div>
      </div>
      {loading ? (
        <p className="text-xs text-slate-500">{t('common.loading', { defaultValue: 'Загрузка…' })}</p>
      ) : clientAccountId ? (
        <BusinessTimelinePanel
          items={items}
          primaryThreadId={primaryThreadId}
          testId="client-account-timeline"
          emptyLabel={t('app.business_timeline.empty', { defaultValue: 'Пока нет бизнес-событий.' })}
        />
      ) : (
        <p className="text-sm text-slate-500">
          {t('app.companies.detail.workspace.activity.no_client_account', {
            defaultValue: 'ClientAccount ещё не связан с этой компанией.',
          })}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Link
          className="btn-secondary btn-sm"
          to={`${CRM_APP_PATHS.invoices}?company_id=${encodeURIComponent(companyId)}`}
        >
          {t('app.companies.detail.workspace.activity.link_invoices')}
        </Link>
        <Link className="btn-secondary btn-sm" to={servicesWorkspacePath('orders', { companyId })}>
          {t('app.companies.detail.workspace.activity.link_services')}
        </Link>
        <Link
          className="btn-secondary btn-sm"
          to={`${CRM_APP_PATHS.vacancies}?company=${encodeURIComponent(companyId)}&page=1`}
        >
          {t('app.companies.detail.workspace.activity.link_vacancies')}
        </Link>
      </div>
    </div>
  )
}
