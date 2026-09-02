import { useState } from 'react'
import type { Application } from '../../api/types/application'
import { useI18n } from '../../i18n'
import { clientDetailPath } from '../../services/platformHandoff'
import SalesInquiryPossibleDuplicatesSection from '../../components/sales/SalesInquiryPossibleDuplicatesSection'
import SalesInquiryQuestionnaireSection from '../../components/sales/SalesInquiryQuestionnaireSection'
import SalesInquiryCallNotesSection from '../../components/sales/SalesInquiryCallNotesSection'
import SalesInquiryTimelineSection from '../../components/sales/SalesInquiryTimelineSection'
import { SalesInquiryCommunicationSlot } from '../../components/sales/SalesInquiryCommunicationSlot'
import { MetaFormAnswersSection } from '../../components/sales/MetaFormAnswersSection'
import { ContextRail } from '../context-rail'
import { EntityWorkspaceCompositionHost } from '../entity-workspace/compositionHost'
import {
  SALES_INQUIRY_COMPOSITION_CONSUMER_ID,
  SALES_INQUIRY_COMPOSITION_SLOTS,
  assertSalesInquiryCompositionSlots,
} from '../entity-workspace/salesInquiryConsumer'
import {
  APPLICATION_STATUS_BADGE,
  applicationInitial,
  applicationStatusLabel,
} from './applicationDisplay'
import { resolveSalesApplicationDecision, existingClientFromApplication } from './resolveSalesApplicationDecision'

const WORKFLOW_STEP_KEYS = ['contact', 'need', 'client', 'service', 'order'] as const

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
  const { t } = useI18n()
  const [timelineRefresh, setTimelineRefresh] = useState(0)
  const companyName = application.title
  const statusKey = application.status
  const activeStep = Number(application.extensions?.workflow_step ?? 1)
  const convertedId = String(application.outcome_entity_id || '').trim()
  const existingClient = existingClientFromApplication(application)
  const clientHref = convertedId
    ? clientDetailPath(convertedId)
    : existingClient
      ? clientDetailPath(existingClient.company_id)
      : undefined
  const subtitle = application.subtitle || t('app.sales_inquiry.workspace.list_kind')
  const openCardLabel = t('app.sales_inquiry.open_client_card', { defaultValue: 'Открыть полную карточку' })
  const workflowSteps = WORKFLOW_STEP_KEYS.map((key) => ({
    key,
    label: t(`app.sales_inquiry.detail.step_${key}`),
  }))
  const contactPhone = application.contact.phone?.trim() || ''
  const contactEmail = application.contact.email?.trim() || ''
  const telHref = contactPhone ? `tel:${contactPhone.replace(/\s/g, '')}` : null
  const busy = patching || converting
  // Lead-backed sections until questionnaire/notes APIs are SI-native.
  const transportLeadId = String(
    application.transport_lead_id || application.extensions?.transport_lead_id || application.id || '',
  ).trim()

  const decision = resolveSalesApplicationDecision({
    application,
    converting,
    patching,
    onStage,
    onConvert,
    t,
  })
  assertSalesInquiryCompositionSlots(SALES_INQUIRY_COMPOSITION_SLOTS)

  const meta = application.source
    ? `${application.source}${application.created_at ? ` · ${new Date(application.created_at).toLocaleString()}` : ''}`
    : undefined

  return (
    <div
      className="flex h-full min-h-0 flex-col"
      data-entity-workspace-slot="context-rail"
      data-entity-workspace-consumer={SALES_INQUIRY_COMPOSITION_CONSUMER_ID}
    >
    <ContextRail
      railKind="sales"
      header={{
        title: companyName,
        titleHref: clientHref,
        subtitle,
        meta,
        statusLabel: applicationStatusLabel(statusKey, t) || statusKey,
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
            {workflowSteps.map((step, idx) => {
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
                  {idx < workflowSteps.length - 1 ? (
                    <span className={`mx-0.5 h-px flex-1 ${done ? 'bg-brand-300' : 'bg-slate-200'}`} />
                  ) : null}
                </li>
              )
            })}
          </ol>
        ),
        contacts: (
          <div className="flex items-start gap-3" data-testid="sales-rail-contact">
            <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-800">
              {applicationInitial(application)}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-slate-800">
                {application.contact.name || t('app.sales_inquiry.detail.contact_fallback')}
              </p>
              {telHref ? (
                <a
                  href={telHref}
                  className="mt-0.5 block break-all text-sm font-semibold tracking-wide text-slate-900 hover:text-brand-700"
                  data-testid="sales-rail-phone"
                >
                  {contactPhone}
                </a>
              ) : (
                <p className="mt-1 text-sm text-slate-400">
                  {t('app.sales_inquiry.no_phone', { defaultValue: 'Телефон не указан' })}
                </p>
              )}
              {contactEmail ? (
                <a
                  href={`mailto:${contactEmail}`}
                  className="mt-1 block truncate text-sm text-slate-600 hover:text-brand-700"
                >
                  {contactEmail}
                </a>
              ) : null}
            </div>
          </div>
        ),
        summary: (
          <EntityWorkspaceCompositionHost
            consumerId={SALES_INQUIRY_COMPOSITION_CONSUMER_ID}
            enabledSlots={['overview', 'forms', 'communication']}
            renderers={{
              overview: () => (
                <div className="space-y-5">
                  <MetaFormAnswersSection
                    answers={application.extensions?.meta_form_answers}
                    additionalAnswers={application.extensions?.additional_answers}
                    labels={application.extensions?.form_question_labels_v1}
                  />
                  <SalesInquiryCallNotesSection
                    leadId={transportLeadId}
                    disabled={busy}
                    onSaved={() => {
                      setTimelineRefresh((n) => n + 1)
                      onQuestionnaireUpdated?.()
                    }}
                  />
                  <SalesInquiryPossibleDuplicatesSection applicationId={application.id} />
                </div>
              ),
              forms: () => (
                <SalesInquiryQuestionnaireSection
                  leadId={transportLeadId}
                  onUpdated={() => {
                    setTimelineRefresh((n) => n + 1)
                    onQuestionnaireUpdated?.()
                  }}
                />
              ),
              communication: () => <SalesInquiryCommunicationSlot inquiryId={application.id} />,
            }}
          />
        ),
        history: (
          <div data-entity-workspace-slot="timeline">
            <SalesInquiryTimelineSection leadId={transportLeadId} refreshToken={timelineRefresh} />
          </div>
        ),
      }}
      contextTitles={{
        contacts: t('app.sales_inquiry.contact_title', { defaultValue: 'Контакт' }),
        summary: t('app.sales_inquiry.work_title', { defaultValue: 'Работа по обращению' }),
        history: t('app.leads.detail.timeline', { defaultValue: 'История' }),
      }}
    />
    </div>
  )
}
