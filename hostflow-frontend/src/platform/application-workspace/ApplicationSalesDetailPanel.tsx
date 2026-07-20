import { useCallback, useEffect, useRef, useState } from 'react'
import type { Application } from '../../api/types/application'
import { getLeadTimeline } from '../../api/client'
import { listCommunicationThreads } from '../../api/communications'
import {
  BusinessTimelinePanel,
  mapTimelineApiItems,
  type BusinessTimelineItem,
} from '../../components/business-timeline/BusinessTimelinePanel'
import { useI18n } from '../../i18n'
import { clientDetailPath } from '../../services/platformHandoff'
import SalesInquiryCommunicationSection from '../../components/sales/SalesInquiryCommunicationSection'
import SalesInquiryPossibleDuplicatesSection from '../../components/sales/SalesInquiryPossibleDuplicatesSection'
import SalesInquiryQuestionnaireSection from '../../components/sales/SalesInquiryQuestionnaireSection'
import { ContextRail } from '../context-rail'
import {
  APPLICATION_STATUS_BADGE,
  APPLICATION_STATUS_TEXT,
  applicationInitial,
} from './applicationDisplay'
import { resolveSalesApplicationDecision } from './resolveSalesApplicationDecision'

const WORKFLOW_STEPS = [
  { key: 'contact', label: 'Связаться' },
  { key: 'need', label: 'Потребность' },
  { key: 'client', label: 'Клиент' },
  { key: 'service', label: 'Услуга' },
  { key: 'order', label: 'Заказ' },
] as const

export type ApplicationSalesDetailPanelProps = {
  application: Application
  converting: boolean
  patching: boolean
  onClose: () => void
  onStage: (stage: 'contacted' | 'qualified' | 'lost') => void | Promise<void>
  onConvert: () => void | Promise<void>
  onQuestionnaireUpdated?: () => void
}

export function ApplicationSalesDetailPanel({
  application,
  converting,
  patching,
  onClose,
  onStage,
  onConvert,
  onQuestionnaireUpdated,
}: ApplicationSalesDetailPanelProps) {
  const { t, locale } = useI18n()
  const companyName = application.title
  const statusKey = application.status === 'rejected' ? 'completed' : application.status
  const activeStep = Number(application.extensions?.workflow_step ?? 1)
  const convertedId = String(application.outcome_entity_id || '').trim()
  const clientHref = convertedId ? clientDetailPath(convertedId) : undefined
  const subtitle = application.subtitle || 'B2B заявка'
  const openCardLabel = t('app.sales_inquiry.open_client_card', { defaultValue: 'Открыть полную карточку' })
  const [timeline, setTimeline] = useState<BusinessTimelineItem[]>([])
  const [primaryThreadId, setPrimaryThreadId] = useState<string | null>(null)
  const onQuestionnaireUpdatedRef = useRef(onQuestionnaireUpdated)
  onQuestionnaireUpdatedRef.current = onQuestionnaireUpdated

  const loadTimeline = useCallback(async () => {
    try {
      const data = await getLeadTimeline(application.id)
      const items = Array.isArray((data as { items?: unknown[] })?.items)
        ? ((data as { items: Array<Record<string, unknown>> }).items)
        : []
      const threadFromApi = String((data as { primary_thread_id?: string })?.primary_thread_id || '').trim()
      setPrimaryThreadId(threadFromApi || null)
      setTimeline(mapTimelineApiItems(items, locale))
      if (!threadFromApi) {
        try {
          const threads = await listCommunicationThreads({
            limit: 20,
            entityType: 'lead',
            entityId: application.id,
          })
          const first = Array.isArray(threads.items) ? threads.items[0] : null
          if (first?.id) setPrimaryThreadId(String(first.id))
        } catch {
          /* optional */
        }
      }
    } catch {
      setTimeline([])
      setPrimaryThreadId(null)
    }
  }, [application.id, locale])

  useEffect(() => {
    void loadTimeline()
  }, [loadTimeline])

  const handleQuestionnaireUpdated = useCallback(() => {
    void loadTimeline()
    onQuestionnaireUpdatedRef.current?.()
  }, [loadTimeline])

  const decision = resolveSalesApplicationDecision({
    application,
    converting,
    patching,
    onStage,
    onConvert,
    t,
  })

  const meta = application.source
    ? `${application.source}${application.created_at ? ` · ${new Date(application.created_at).toLocaleString()}` : ''}`
    : undefined

  return (
    <ContextRail
      railKind="sales"
      header={{
        title: companyName,
        titleHref: clientHref,
        subtitle,
        meta,
        statusLabel: APPLICATION_STATUS_TEXT[statusKey as keyof typeof APPLICATION_STATUS_TEXT] || statusKey,
        statusClassName: `rounded-full px-3 py-0.5 text-xs font-semibold ${APPLICATION_STATUS_BADGE[statusKey as keyof typeof APPLICATION_STATUS_BADGE] || APPLICATION_STATUS_BADGE.new}`,
        entityWorkspaceHref: clientHref,
        entityWorkspaceLabel: openCardLabel,
      }}
      decision={decision}
      onClose={onClose}
      closeLabel={t('common.close', { defaultValue: 'Закрыть' })}
      contextSlots={{
        workflow: (
          <ol className="flex items-center gap-1">
            {WORKFLOW_STEPS.map((step, idx) => {
              const stepNum = idx + 1
              const done = stepNum < activeStep
              const active = stepNum === activeStep
              return (
                <li key={step.key} className="flex min-w-0 flex-1 items-center gap-1">
                  <span
                    className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      done
                        ? 'bg-brand-700 text-white'
                        : active
                          ? 'bg-brand-100 text-brand-800 ring-2 ring-brand-600'
                          : 'bg-slate-100 text-slate-400'
                    }`}
                  >
                    {stepNum}
                  </span>
                  <span
                    className={`hidden truncate text-[11px] font-medium sm:block ${
                      active ? 'text-brand-800' : done ? 'text-slate-700' : 'text-slate-400'
                    }`}
                  >
                    {step.label}
                  </span>
                  {idx < WORKFLOW_STEPS.length - 1 ? (
                    <span className={`mx-0.5 h-px flex-1 ${done ? 'bg-brand-300' : 'bg-slate-200'}`} />
                  ) : null}
                </li>
              )
            })}
          </ol>
        ),
        contacts: (
          <div>
            <div className="flex items-start gap-3">
              <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-800">
                {applicationInitial(application)}
              </span>
              <div className="min-w-0 text-sm text-slate-600">
                <p className="font-medium text-slate-800">{application.contact.name || 'Контакт'}</p>
                {application.contact.phone ? (
                  <p className="mt-0.5 text-xs text-slate-500">{application.contact.phone}</p>
                ) : null}
                {application.contact.email ? (
                  <p className="mt-0.5 truncate text-xs text-slate-500">{application.contact.email}</p>
                ) : null}
              </div>
            </div>
            <SalesInquiryPossibleDuplicatesSection applicationId={application.id} />
          </div>
        ),
        summary: (
          <SalesInquiryQuestionnaireSection
            leadId={application.id}
            onUpdated={handleQuestionnaireUpdated}
          />
        ),
        relations: (
          <SalesInquiryCommunicationSection
            leadId={application.id}
            preferredThreadId={primaryThreadId}
          />
        ),
        history: (
          <BusinessTimelinePanel
            items={timeline}
            primaryThreadId={primaryThreadId}
            testId="sales-inquiry-timeline"
            emptyLabel={t('app.sales_inquiry.timeline_empty', {
              defaultValue: 'Пока нет бизнес-событий по этой заявке.',
            })}
          />
        ),
      }}
      contextTitles={{
        summary: t('app.sales_inquiry.questionnaire_title', { defaultValue: 'Ankieta klienta' }),
        relations: t('app.sales_inquiry.comms.title', { defaultValue: 'Переписка' }),
        history: t('app.sales_inquiry.timeline_title', { defaultValue: 'История' }),
      }}
    />
  )
}
