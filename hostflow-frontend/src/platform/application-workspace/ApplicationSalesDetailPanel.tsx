import type { Application } from '../../api/types/application'
import { useI18n } from '../../i18n'
import { clientDetailPath } from '../../services/platformHandoff'
import { ContextRail } from '../context-rail'
import {
  APPLICATION_STATUS_BADGE,
  APPLICATION_STATUS_TEXT,
  applicationInitial,
} from './applicationDisplay'
import { resolveSalesApplicationDecision } from './resolveSalesApplicationDecision'
import {
  SalesInquiryAnswersBlock,
  SalesInquiryAttributionSection,
  SalesInquiryCommunicationBlock,
} from '../../components/leads/SalesInquiryQuestionnaireSection'

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
  onRefresh?: () => void
}

export function ApplicationSalesDetailPanel({
  application,
  converting,
  patching,
  onClose,
  onStage,
  onConvert,
  onRefresh,
}: ApplicationSalesDetailPanelProps) {
  const { t } = useI18n()
  const companyName = application.title
  const statusKey = application.status === 'rejected' ? 'completed' : application.status
  const activeStep = Number(application.extensions?.workflow_step ?? 1)
  const convertedId = String(application.outcome_entity_id || '').trim()
  const clientHref = convertedId ? clientDetailPath(convertedId) : undefined
  const subtitle = application.subtitle || 'B2B заявка'
  const openCardLabel = t('app.sales_inquiry.open_client_card', { defaultValue: 'Открыть полную карточку' })

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
          <div className="space-y-4">
            <div className="space-y-2 text-sm text-slate-700">
              <div className="flex items-start gap-3">
                <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-800">
                  {applicationInitial(application)}
                </span>
                <div>
                  <p className="font-medium text-slate-900">{application.contact.name || 'Контакт'}</p>
                  {application.contact.phone ? <p>{application.contact.phone}</p> : null}
                  {application.contact.email ? <p>{application.contact.email}</p> : null}
                </div>
              </div>
            </div>
            <SalesInquiryCommunicationBlock
              applicationId={application.id}
              contact={application.contact}
              companyName={application.title}
              convertedClientId={convertedId || null}
              onLeadUpdated={onRefresh}
            />
          </div>
        ),
        summary: (
          <SalesInquiryAnswersBlock applicationId={application.id} convertedClientId={convertedId || null} />
        ),
        history: <SalesInquiryAttributionSection applicationId={application.id} />,
      }}
      contextTitles={{
        summary: 'Информация от клиента',
        history: 'История',
        contacts: 'Связаться',
        workflow: 'Этапы',
      }}
    />
  )
}
