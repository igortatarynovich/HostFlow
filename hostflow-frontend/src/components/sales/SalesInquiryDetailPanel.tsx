import { IconClock, IconMail, IconPhone, IconBrandWhatsapp, IconX } from '@tabler/icons-react'
import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import {
  inquiryCompanyName,
  inquiryContactEmail,
  inquiryContactName,
  inquiryContactPhone,
  inquiryRequestTitle,
  inquiryStatusKey,
  salesInquiryWorkflowStep,
} from '../../utils/clientInquiryLead'
import { leadIntakeResolutionRejected } from '../../utils/intakeResolution'

const STATUS_BADGE: Record<string, string> = {
  new: 'bg-emerald-50 text-emerald-700',
  in_progress: 'bg-amber-50 text-amber-700',
  waiting: 'bg-blue-50 text-blue-700',
  questionnaire_submitted: 'bg-violet-50 text-violet-700',
  completed: 'bg-slate-100 text-slate-600',
}

const WORKFLOW_STEP_KEYS = ['contact', 'need', 'client', 'service', 'order'] as const

type SalesInquiryDetailPanelProps = {
  lead: Lead
  converting: boolean
  patching: boolean
  onStage: (stage: 'contacted' | 'qualified' | 'lost') => void | Promise<void>
  onConvert: () => void | Promise<void>
}

export function SalesInquiryDetailPanel({
  lead,
  converting,
  patching,
  onStage,
  onConvert,
}: SalesInquiryDetailPanelProps) {
  const { t } = useI18n()
  const companyName = inquiryCompanyName(lead)
  const contactName =
    inquiryContactName(lead) ||
    t('app.sales_inquiry.contact_fallback', { defaultValue: 'Contact' })
  const contactPhone = inquiryContactPhone(lead)
  const contactEmail = inquiryContactEmail(lead)
  const statusKey = inquiryStatusKey(lead)
  const activeStep = salesInquiryWorkflowStep(lead)
  const terminal = leadIntakeResolutionRejected(lead)
  const convertedId = String(lead.converted_client_id || '').trim()
  const initial = contactName.charAt(0).toUpperCase() || companyName.charAt(0).toUpperCase() || '?'
  const whatsappHref = contactPhone
    ? `https://wa.me/${contactPhone.replace(/[^\d+]/g, '').replace(/^\+/, '')}`
    : null

  const statusLabel = t(`app.application_workspace.status.${statusKey}`, {
    defaultValue:
      (
        {
          new: 'New',
          in_progress: 'In progress',
          waiting: 'Awaiting reply',
          questionnaire_submitted: 'Reply received',
          completed: 'Completed',
        } as Record<string, string>
      )[statusKey] || statusKey,
  })

  const workflowSteps = WORKFLOW_STEP_KEYS.map((key) => ({
    key,
    label: t(`app.sales_inquiry.workflow.${key}`, {
      defaultValue:
        (
          {
            contact: 'Contact',
            need: 'Need',
            client: 'Client',
            service: 'Service',
            order: 'Order',
          } as Record<string, string>
        )[key] || key,
    }),
  }))

  const stepGuidance = (() => {
    if (convertedId) {
      return {
        title: t('app.sales_inquiry.step.service_title', { defaultValue: 'Add a service' }),
        body: t('app.sales_inquiry.step.service_body', {
          defaultValue: 'Client created. Open the card and add the first service.',
        }),
        primary: null as { label: string; action: () => void } | null,
      }
    }
    if (activeStep >= 3) {
      return {
        title: t('app.sales_inquiry.step.client_title', { defaultValue: 'Create client' }),
        body: t('app.sales_inquiry.step.client_body', {
          defaultValue: 'The company is interested. Save it as a client.',
        }),
        primary: {
          label: converting
            ? t('app.sales_inquiry.creating_client', { defaultValue: 'Creating…' })
            : t('app.sales_inquiry.create_client', { defaultValue: 'Create client' }),
          action: () => void onConvert(),
        },
      }
    }
    if (activeStep >= 2) {
      return {
        title: t('app.sales_inquiry.step.need_title', { defaultValue: 'Clarify the need' }),
        body: t('app.sales_inquiry.step.need_body', {
          defaultValue: 'Confirm which service the company wants to buy.',
        }),
        primary: {
          label: t('app.sales_inquiry.interested', { defaultValue: 'Interested' }),
          action: () => void onStage('qualified'),
        },
      }
    }
    return {
      title: t('app.sales_inquiry.step.contact_title', { defaultValue: 'Contact the client' }),
      body: t('app.sales_inquiry.step.contact_body', {
        defaultValue: 'First contact has not been made yet.',
      }),
      primary: contactPhone
        ? {
            label: t('app.sales_inquiry.called', { defaultValue: 'Called' }),
            action: () => void onStage('contacted'),
          }
        : null,
    }
  })()

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-white">
      <div className="border-b border-slate-100 p-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <h2 className="text-lg font-bold text-slate-900">{companyName}</h2>
            <p className="mt-0.5 text-sm text-slate-500">{inquiryRequestTitle(lead)}</p>
          </div>
          <span className={`rounded-full px-3 py-0.5 text-xs font-semibold ${STATUS_BADGE[statusKey] || STATUS_BADGE.new}`}>
            {statusLabel}
          </span>
        </div>
      </div>

      <div className="border-b border-slate-100 p-4">
        <div className="flex items-start gap-3">
          <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-100 text-base font-bold text-brand-800">
            {initial}
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-slate-900">{contactName}</p>
            {contactPhone ? <p className="text-sm text-slate-600">{contactPhone}</p> : null}
            {contactEmail ? <p className="text-sm text-slate-500">{contactEmail}</p> : null}
          </div>
        </div>
        {!terminal && (contactPhone || contactEmail || whatsappHref) ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {contactPhone ? (
              <a
                href={`tel:${contactPhone.replace(/\s/g, '')}`}
                className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
              >
                <IconPhone size={16} stroke={2} />
                {t('app.sales_inquiry.call', { defaultValue: 'Call' })}
              </a>
            ) : null}
            {whatsappHref ? (
              <a
                href={whatsappHref}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50"
              >
                <IconBrandWhatsapp size={16} stroke={2} />
                WhatsApp
              </a>
            ) : null}
            {contactEmail ? (
              <a
                href={`mailto:${contactEmail}`}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50"
              >
                <IconMail size={16} stroke={2} />
                Email
              </a>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="border-b border-slate-100 px-4 py-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.sales_inquiry.workflow_title', { defaultValue: "What's next?" })}
        </p>
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
                      ? 'bg-brand-600 text-white'
                      : active
                        ? 'bg-brand-100 text-brand-800 ring-2 ring-brand-500'
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
      </div>

      {!terminal && !convertedId ? (
        <div className="flex-1 p-4">
          <section className="rounded-xl border border-brand-200 bg-brand-50/50 p-4">
            <p className="font-semibold text-slate-900">{stepGuidance.title}</p>
            <p className="mt-1 text-sm text-slate-600">{stepGuidance.body}</p>
            {stepGuidance.primary ? (
              <button
                type="button"
                disabled={patching || converting}
                onClick={stepGuidance.primary.action}
                className="mt-4 rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
              >
                {stepGuidance.primary.label}
              </button>
            ) : null}
          </section>
        </div>
      ) : null}

      {!terminal && !convertedId ? (
        <div className="mt-auto flex flex-wrap gap-2 border-t border-slate-100 p-4">
          <button
            type="button"
            disabled={patching || converting}
            onClick={() => void onStage('qualified')}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            <IconClock size={16} stroke={2} />
            {t('app.sales_inquiry.interested_later', { defaultValue: 'Interested, but later' })}
          </button>
          <button
            type="button"
            disabled={patching || converting}
            onClick={() => void onStage('lost')}
            className="inline-flex items-center gap-2 rounded-xl border border-rose-200 bg-white px-4 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-60"
          >
            <IconX size={16} stroke={2} />
            {t('app.sales_inquiry.close', { defaultValue: 'Close request' })}
          </button>
        </div>
      ) : null}
    </div>
  )
}
