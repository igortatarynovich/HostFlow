import { useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import {
  advanceSalesWorkSession,
  cancelSalesWorkSession,
  getSalesWorkSession,
  isActiveWorkSessionForLead,
  leadHref,
  parseSalesInquiryLeadId,
} from '../../services/salesWorkSession'

export function SalesWorkSessionBar() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const location = useLocation()
  const session = useMemo(() => getSalesWorkSession(), [location.pathname])

  const leadId = useMemo(() => {
    const fromSales = parseSalesInquiryLeadId(location.pathname)
    if (fromSales) return fromSales
    const prefix = `${CRM_APP_PATHS.leads}/`
    if (!location.pathname.startsWith(prefix)) return null
    const rest = location.pathname.slice(prefix.length)
    const id = rest.split('/')[0]
    return id || null
  }, [location.pathname])

  if (!session || !leadId || !isActiveWorkSessionForLead(leadId)) {
    return null
  }

  const total = session.queue.length
  const current = session.index + 1
  const kindLabel = t(`app.sales_work_session.kind.${session.kind}`, {
    defaultValue:
      (
        {
          call: 'Company calls',
          convert: 'Client onboarding',
          recruitment_call: 'New applications',
        } as Record<string, string>
      )[session.kind] || session.kind,
  })

  function handleNext() {
    const nextId = advanceSalesWorkSession()
    if (nextId) {
      navigate(leadHref(nextId))
      return
    }
    navigate(session.returnPath)
  }

  function handleStop() {
    cancelSalesWorkSession()
    navigate(session.returnPath)
  }

  return (
    <div
      className="sticky top-0 z-30 border-b border-brand-200 bg-brand-50/95 px-4 py-2 backdrop-blur sm:px-6"
      data-testid="m1-sales-work-session-bar"
    >
      <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-brand-900">
          {t('app.sales_work_session.progress', {
            defaultValue: '{kind}: inquiry {current} of {total}',
            values: {
              kind: kindLabel,
              current,
              total,
            },
          })}
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleNext}
            className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
          >
            {t('app.sales_work_session.next', { defaultValue: 'Done — next' })}
          </button>
          <button
            type="button"
            onClick={handleStop}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {t('app.sales_work_session.back_list', { defaultValue: 'Back to list' })}
          </button>
        </div>
      </div>
    </div>
  )
}
