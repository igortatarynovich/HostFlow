import { useState } from 'react'
import type { Application, ApplicationStatus } from '../../api/types/application'
import { useI18n } from '../../i18n'
import { clientDetailPath } from '../../services/platformHandoff'
import SalesInquiryPossibleDuplicatesSection from '../../components/sales/SalesInquiryPossibleDuplicatesSection'
import SalesInquiryQuestionnaireSection from '../../components/sales/SalesInquiryQuestionnaireSection'
import SalesInquiryCallNotesSection from '../../components/sales/SalesInquiryCallNotesSection'
import SalesInquiryTimelineSection from '../../components/sales/SalesInquiryTimelineSection'
import { MetaFormAnswersSection } from '../../components/sales/MetaFormAnswersSection'
import { ContextRail } from '../context-rail'
import {
  APPLICATION_STATUS_BADGE,
  applicationInitial,
  applicationStatusLabel,
} from './applicationDisplay'
import { resolveSalesApplicationDecision } from './resolveSalesApplicationDecision'

const WORKFLOW_STEP_KEYS = [
  { key: 'contact', labelKey: 'app.sales_inquiry.workflow.contact', defaultValue: 'Contact' },
  { key: 'need', labelKey: 'app.sales_inquiry.workflow.need', defaultValue: 'Need' },
  { key: 'client', labelKey: 'app.sales_inquiry.workflow.client', defaultValue: 'Client' },
  { key: 'service', labelKey: 'app.sales_inquiry.workflow.service', defaultValue: 'Service' },
  { key: 'order', labelKey: 'app.sales_inquiry.workflow.order', defaultValue: 'Order' },
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
  const { t } = useI18n()
  const [timelineRefresh, setTimelineRefresh] = useState(0)
  const companyName = application.title
  const statusKey: ApplicationStatus = application.status === 'rejected' ? 'completed' : application.status
  const activeStep = Number(application.extensions?.workflow_step ?? 1)
  const convertedId = String(application.outcome_entity_id || '').trim()
  const clientHref = convertedId ? clientDetailPath(convertedId) : undefined
  const subtitle =
    application.subtitle ||
    t('app.sales_inquiry.subtitle_fallback', { defaultValue: 'B2B inquiry' })
  const openCardLabel = t('app.sales_inquiry.open_full_card', { defaultValue: 'Open full card' })
  const contactPhone = application.contact.phone?.trim() || ''
  const contactEmail = application.contact.email?.trim() || ''
  const telHref = contactPhone ? `tel:${contactPhone.replace(/\s/g, '')}` : null
  const busy = patching || converting

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
        statusLabel: applicationStatusLabel(statusKey, t),
        statusClassName: `rounded-full px-3 py-0.5 text-xs font-semibold ${APPLICATION_STATUS_BADGE[statusKey] || APPLICATION_STATUS_BADGE.new}`,
        entityWorkspaceHref: clientHref,
        entityWorkspaceLabel: openCardLabel,
      }}
      decision={decision}
      onClose={onClose}
      closeLabel={t('common.close', { defaultValue: 'Close' })}
      contextSlots={{
        workflow: (
          <ol className="flex items-center gap-1">
            {WORKFLOW_STEP_KEYS.map((step, idx) => {
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
                    {t(step.labelKey, { defaultValue: step.defaultValue })}
                  </span>
                  {idx < WORKFLOW_STEP_KEYS.length - 1 ? (
                    <span className={`mx-0.5 h-px flex-1 ${done ? 'bg-brand-300' : 'bg-slate-200'}`} />
                  ) : null}
                </li>
              )
            })}
          </ol>
        ),
        contacts: (
          <div className="flex items-start gap-3" data-testid="sales-rail-contact">
            <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-800">
              {applicationInitial(application)}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-slate-800">
                {application.contact.name ||
                  t('app.sales_inquiry.contact_fallback', { defaultValue: 'Contact' })}
              </p>
              {telHref ? (
                <a
                  href={telHref}
                  className="mt-1 block break-all text-2xl font-semibold tracking-wide text-slate-900 hover:text-brand-700"
                  data-testid="sales-rail-phone"
                >
                  {contactPhone}
                </a>
              ) : (
                <p className="mt-1 text-sm text-slate-400">
                  {t('app.sales_inquiry.no_phone', { defaultValue: 'No phone number' })}
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
          <div className="space-y-5">
            <MetaFormAnswersSection
              answers={application.extensions?.meta_form_answers}
              additionalAnswers={application.extensions?.additional_answers}
            />
            <SalesInquiryCallNotesSection
              leadId={application.id}
              disabled={busy}
              onSaved={() => {
                setTimelineRefresh((n) => n + 1)
                onQuestionnaireUpdated?.()
              }}
            />
            <SalesInquiryPossibleDuplicatesSection applicationId={application.id} />
            <SalesInquiryQuestionnaireSection
              leadId={application.id}
              onUpdated={() => {
                setTimelineRefresh((n) => n + 1)
                onQuestionnaireUpdated?.()
              }}
            />
          </div>
        ),
        history: (
          <SalesInquiryTimelineSection leadId={application.id} refreshToken={timelineRefresh} />
        ),
      }}
      contextTitles={{
        contacts: t('app.sales_inquiry.contact_title', { defaultValue: 'Contact' }),
        summary: t('app.sales_inquiry.work_title', { defaultValue: 'Work on inquiry' }),
        history: t('app.leads.detail.timeline', { defaultValue: 'History' }),
      }}
    />
  )
}
