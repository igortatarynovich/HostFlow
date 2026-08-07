import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import type { LeadCallResultCode } from '../../api/client'
import type { Lead } from '../../api/types'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n, type TranslateFn } from '../../i18n'
import SalesInquiryRodoSection from '../sales/SalesInquiryRodoSection'
import { leadIntakeResolutionRejected, leadRodoSatisfied } from '../../utils/intakeResolution'
import {
  LEAD_CALL_RESULT_CODES,
  leadCallResultHistory,
  type LeadCallResultEntry,
} from '../../utils/leadCallResult'

type ClientLeadDetailViewProps = {
  lead: Lead
  formatDate: (iso: string | null | undefined) => string
  converting: boolean
  patching: boolean
  savingCallResult?: boolean
  onConvert: () => void | Promise<void>
  onStage: (stage: 'contacted' | 'qualified' | 'lost') => void | Promise<void>
  onCallResult?: (payload: { result: LeadCallResultCode; note: string }) => void | Promise<void>
  moreSection?: ReactNode
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

function list(value: unknown): string {
  if (Array.isArray(value)) return value.map(text).filter(Boolean).join(', ')
  return text(value)
}

function yesNo(value: unknown, t: TranslateFn): string {
  if (value === true) return t('common.yes', { defaultValue: 'Yes' })
  if (value === false) return t('common.no', { defaultValue: 'No' })
  return '—'
}

function Field({
  label,
  value,
  t,
}: {
  label: string
  value: unknown
  t: TranslateFn
}) {
  const rendered = Array.isArray(value)
    ? list(value)
    : typeof value === 'boolean'
      ? yesNo(value, t)
      : text(value)
  return (
    <div className="min-w-0 rounded-lg border border-slate-200 bg-white px-3 py-2">
      <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 break-words text-sm font-medium text-slate-900">{rendered || '—'}</dd>
    </div>
  )
}

function Section({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
      <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
      <dl className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{children}</dl>
    </section>
  )
}

function CallResultHistoryItem({
  entry,
  formatDate,
  resultLabel,
  noteLabel,
}: {
  entry: LeadCallResultEntry
  formatDate: (iso: string | null | undefined) => string
  resultLabel: (code: string) => string
  noteLabel: string
}) {
  return (
    <li className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-medium text-slate-800">{resultLabel(entry.result)}</span>
        {entry.at ? <span className="text-xs text-slate-500">{formatDate(entry.at)}</span> : null}
      </div>
      {entry.note?.trim() ? (
        <p className="mt-1.5 whitespace-pre-wrap border-t border-slate-100 pt-1.5 text-slate-700">
          <span className="text-xs font-medium text-slate-500">{noteLabel}: </span>
          {entry.note.trim()}
        </p>
      ) : null}
    </li>
  )
}

export default function ClientLeadDetailView({
  lead,
  formatDate,
  converting,
  patching,
  savingCallResult = false,
  onConvert,
  onStage,
  onCallResult,
  moreSection,
}: ClientLeadDetailViewProps) {
  const { t } = useI18n()
  const [callResult, setCallResult] = useState<LeadCallResultCode>('callback_requested')
  const [callNote, setCallNote] = useState('')
  const [leadState, setLeadState] = useState(lead)
  useEffect(() => {
    setLeadState(lead)
  }, [lead])
  const rodoOk = leadRodoSatisfied(leadState)

  const normalized = record(leadState.normalized)
  const payload = record(leadState.payload)
  const company = record(normalized.company_profile)
  const payloadCompany = record(payload.company)
  const contact = record(normalized.contact_person)
  const payloadContact = record(payload.contact)
  const need = record(normalized.need)
  const payloadNeed = record(payload.need)
  const normalizedTerms = record(need.terms)
  const payloadTerms = record(payload.terms)
  const terms = Object.keys(normalizedTerms).length > 0 ? normalizedTerms : payloadTerms
  const marketing = record(normalized.marketing)
  const meta = record(normalized.meta)
  const consent = record(normalized.consent)
  const sourceProfile = record(meta.source_profile)
  const fieldAnswers = Array.isArray(normalized.field_answers)
    ? (normalized.field_answers as Array<{ name?: unknown; values?: unknown }>)
    : []
  const companyName =
    text(company.name) ||
    text(normalized.company_name) ||
    text(normalized.company_name_hint) ||
    text(payloadCompany.name) ||
    leadState.company_name ||
    'Client Lead'
  const convertedId = text(leadState.converted_client_id)
  const terminal = leadIntakeResolutionRejected(leadState)
  const statusLabel = terminal
    ? t('app.leads.client_detail.status_rejected', { defaultValue: 'Rejected' })
    : convertedId
      ? t('app.leads.client_detail.status_client_created', { defaultValue: 'Client created' })
      : leadState.status === 'processed'
        ? t('app.leads.client_detail.status_new_form', { defaultValue: 'New questionnaire' })
        : leadState.status === 'rejected'
          ? t('app.leads.client_detail.status_rejected', { defaultValue: 'Rejected' })
          : leadState.status

  const history = useMemo(() => leadCallResultHistory(leadState), [leadState])

  const resultLabel = (code: string) =>
    t(`app.leads.detail.call_result.results.${code}`, { defaultValue: code })

  const noteRecommended =
    callResult === 'answered' ||
    callResult === 'callback_requested' ||
    callResult === 'interested' ||
    callResult === 'not_interested'

  const busy = patching || converting || savingCallResult
  const field = (key: string, defaultValue: string) =>
    t(`app.leads.client_detail.fields.${key}`, { defaultValue })
  const section = (key: string, defaultValue: string) =>
    t(`app.leads.client_detail.sections.${key}`, { defaultValue })

  return (
    <div className="space-y-5">
      <header className="card relative overflow-hidden p-5 shadow-md shadow-slate-900/[0.04] sm:p-6">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-brand-400 via-brand-500 to-brand-600/90" aria-hidden />
        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
              {t('app.leads.detail.call_result.kicker', { defaultValue: 'B2B inquiry' })}
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">{companyName}</h1>
            <p className="mt-2 text-sm text-slate-600">
              {text(need.summary) ||
                [text(need.people_count), text(need.what_needed)].filter(Boolean).join(' ') ||
                t('app.leads.client_detail.fallback_summary', {
                  defaultValue: 'Transport company questionnaire',
                })}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span
                className={`inline-flex rounded-lg px-2 py-0.5 text-xs font-medium ${
                  terminal ? 'bg-red-50 text-red-800' : 'bg-slate-100 text-slate-700'
                }`}
              >
                {statusLabel}
              </span>
              {!terminal ? (
                <span className="inline-flex rounded-lg bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-800">
                  {lead.stage || 'questionnaire_submitted'}
                </span>
              ) : null}
              <span className="inline-flex rounded-lg bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                {lead.source}
              </span>
            </div>
            {terminal ? (
              <p className="mt-3 text-sm text-red-700">
                {t('app.leads.client_detail.rejected_banner', {
                  defaultValue: 'Lead rejected and excluded from candidate processing.',
                })}
              </p>
            ) : null}
            <p className="mt-3 font-mono text-[11px] leading-relaxed text-slate-400 break-all">ID · {lead.id}</p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2 border-t border-slate-100 pt-4 lg:border-l lg:border-t-0 lg:pl-5 lg:pt-0">
            {terminal ? null : convertedId ? (
              <Link to={`${CRM_APP_PATHS.agencyClients}/${convertedId}`} className="btn-primary rounded-lg px-3 py-2 text-sm font-semibold">
                {t('app.leads.client_detail.open_client', { defaultValue: 'Open client' })}
              </Link>
            ) : (
              <button
                type="button"
                className="btn-primary rounded-lg px-3 py-2 text-sm font-semibold"
                disabled={busy}
                onClick={() => void onConvert()}
              >
                {converting
                  ? t('app.leads.client_detail.creating', { defaultValue: 'Creating…' })
                  : t('app.leads.client_detail.create_client', { defaultValue: 'Create client' })}
              </button>
            )}
            {!terminal ? (
              <>
                <button
                  type="button"
                  className="btn-secondary rounded-lg px-3 py-2 text-sm"
                  disabled={busy || !rodoOk}
                  onClick={() => void onStage('contacted')}
                  title={
                    !rodoOk
                      ? t('app.leads.messages.process_blocked.LEAD_RODO_REQUIRED', {
                          defaultValue: 'RODO required first',
                        })
                      : undefined
                  }
                >
                  {t('app.leads.client_detail.mark_contacted', { defaultValue: 'Contact established' })}
                </button>
                <button
                  type="button"
                  className="btn-secondary rounded-lg px-3 py-2 text-sm"
                  disabled={busy}
                  onClick={() => void onStage('qualified')}
                >
                  {t('app.leads.client_detail.qualify', { defaultValue: 'Qualify' })}
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-red-200 bg-white px-3 py-2 text-sm text-red-800 hover:bg-red-50 disabled:opacity-60"
                  disabled={busy}
                  onClick={() => void onStage('lost')}
                >
                  {t('app.leads.client_detail.reject', { defaultValue: 'Reject' })}
                </button>
              </>
            ) : null}
          </div>
        </div>
      </header>

      {!terminal && onCallResult ? (
        <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <SalesInquiryRodoSection
            leadId={String(leadState.id)}
            lead={leadState}
            disabled={busy}
            onUpdated={setLeadState}
          />
          <div>
            <h2 className="text-sm font-semibold text-slate-900">
              {t('app.leads.detail.call_result.title', { defaultValue: 'Call result' })}
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              {t('app.leads.detail.call_result.subtitle', {
                defaultValue:
                  'Callback or what else they want / think — capture it after the call.',
              })}
            </p>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-1 block text-xs font-medium text-slate-600">
                {t('app.leads.detail.call_result.fields.result', { defaultValue: 'Result' })}
              </span>
              <select
                className="input w-full"
                value={callResult}
                disabled={busy || !rodoOk}
                onChange={(e) => setCallResult(e.target.value as LeadCallResultCode)}
              >
                {LEAD_CALL_RESULT_CODES.map((code) => (
                  <option key={code} value={code}>
                    {resultLabel(code)}
                  </option>
                ))}
              </select>
            </label>
            <div className="sm:col-span-2">
              <label className="block text-sm">
                <span className="mb-1 block text-xs font-medium text-slate-600">
                  {t('app.leads.detail.call_result.fields.note', {
                    defaultValue: 'Comment',
                  })}
                  {noteRecommended ? (
                    <span className="ml-1 font-normal text-slate-500">
                      (
                      {t('app.leads.detail.call_result.fields.note_recommended', {
                        defaultValue: 'recommended',
                      })}
                      )
                    </span>
                  ) : null}
                </span>
                <textarea
                  className="textarea mt-0 w-full"
                  rows={3}
                  maxLength={2000}
                  disabled={busy || !rodoOk}
                  value={callNote}
                  onChange={(e) => setCallNote(e.target.value)}
                  placeholder={t('app.leads.detail.call_result.fields.note_placeholder', {
                    defaultValue: 'E.g. call back tomorrow at 15:00, asking about rate, thinking…',
                  })}
                />
              </label>
              <p className="mt-1 text-xs text-slate-500">
                {t('app.leads.detail.call_result.fields.note_hint', {
                  defaultValue: 'What they want or think: callback, terms, doubts, next step.',
                })}
              </p>
            </div>
          </div>
          <div className="mt-3 flex justify-end">
            <button
              type="button"
              className="btn-primary rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-60"
              disabled={busy || !rodoOk}
              title={
                !rodoOk
                  ? t('app.leads.messages.process_blocked.LEAD_RODO_REQUIRED', {
                      defaultValue: 'Send RODO or mark covered at source before saving a call result.',
                    })
                  : undefined
              }
              onClick={() => {
                void Promise.resolve(
                  onCallResult({ result: callResult, note: callNote.trim() }),
                ).then(() => setCallNote(''))
              }}
            >
              {savingCallResult
                ? t('common.saving', { defaultValue: 'Saving…' })
                : t('app.leads.detail.call_result.save', { defaultValue: 'Save call result' })}
            </button>
          </div>
          {history.length > 0 ? (
            <div className="mt-4 border-t border-slate-100 pt-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.leads.detail.call_result.history_title', { defaultValue: 'Call history' })}
              </h3>
              <ul className="mt-2 space-y-2">
                {history.map((entry, idx) => (
                  <CallResultHistoryItem
                    key={`${entry.at || 'x'}-${entry.result}-${idx}`}
                    entry={entry}
                    formatDate={formatDate}
                    resultLabel={resultLabel}
                    noteLabel={t('app.leads.detail.call_result.fields.note', {
                      defaultValue: 'Comment',
                    })}
                  />
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}

      <Section title={section('company', 'Company')}>
        <Field
          t={t}
          label={field('name', 'Name')}
          value={company.name || normalized.company_name || normalized.company_name_hint || payloadCompany.name || lead.company_name}
        />
        <Field t={t} label={field('legal_name', 'Legal name')} value={company.legal_name || payloadCompany.legal_name} />
        <Field t={t} label={field('tax_id', 'NIP / VAT')} value={company.tax_id || company.nip || company.vat || payloadCompany.tax_id} />
        <Field t={t} label={field('country', 'Country')} value={company.country || payloadCompany.country} />
        <Field t={t} label={field('city', 'City')} value={company.city || payloadCompany.city} />
        <Field t={t} label={field('website', 'Website')} value={company.website || payloadCompany.website} />
        <Field t={t} label={field('fleet_size', 'Fleet size')} value={company.fleet_size || payloadCompany.fleet_size} />
        <Field t={t} label={field('transport_type', 'Transport type')} value={company.transport_type || payloadCompany.transport_type} />
      </Section>

      <Section title={section('contact', 'Contact person')}>
        <Field t={t} label={field('full_name', 'Full name')} value={contact.full_name || payloadContact.full_name || normalized.full_name} />
        <Field t={t} label={field('role', 'Role')} value={contact.role || payloadContact.role} />
        <Field t={t} label={field('email', 'Email')} value={contact.email || payloadContact.email || normalized.email} />
        <Field t={t} label={field('phone', 'Phone')} value={contact.phone || payloadContact.phone || normalized.phone} />
        <Field t={t} label={field('whatsapp', 'WhatsApp')} value={contact.whatsapp ?? payloadContact.whatsapp} />
      </Section>

      <Section title={section('need', 'Need')}>
        <Field t={t} label={field('what_needed', 'What is needed')} value={need.what_needed || payloadNeed.what_needed} />
        <Field t={t} label={field('summary', 'Summary')} value={need.summary || payloadNeed.summary} />
        <Field t={t} label={field('people_count', 'Headcount')} value={need.people_count || payloadNeed.people_count} />
        <Field t={t} label={field('cooperation_type', 'Cooperation type')} value={need.cooperation_type || payloadNeed.cooperation_type} />
        <Field
          t={t}
          label={field('when_needed', 'When needed')}
          value={need.start_date || need.when_needed || payloadNeed.start_date || payloadNeed.when_needed}
        />
        <Field t={t} label={field('requirements', 'Requirements')} value={need.requirements || payloadNeed.requirements} />
        <Field t={t} label={field('runs_paid_ads', 'Paid campaigns')} value={marketing.runs_paid_ads} />
      </Section>

      {fieldAnswers.length > 0 ? (
        <Section title={section('meta_answers', 'Answers from Meta form')}>
          {fieldAnswers.map((item, idx) => (
            <Field
              key={`${text(item.name) || 'field'}-${idx}`}
              t={t}
              label={text(item.name) || `Field ${idx + 1}`}
              value={item.values}
            />
          ))}
        </Section>
      ) : null}

      <Section title={section('terms', 'Work terms')}>
        <Field t={t} label={field('rate', 'Rate')} value={terms.rate || normalized.rate} />
        <Field t={t} label={field('rate_amount', 'Amount')} value={terms.rate_amount || normalized.rate_amount} />
        <Field t={t} label={field('rate_currency', 'Currency')} value={terms.rate_currency || normalized.rate_currency} />
        <Field t={t} label={field('rate_period', 'Period')} value={terms.rate_period || normalized.rate_period} />
        <Field t={t} label={field('rate_tax_mode', 'Net / gross / B2B')} value={terms.rate_tax_mode || normalized.rate_tax_mode} />
        <Field t={t} label={field('bonus', 'Bonuses')} value={terms.bonus || normalized.bonus} />
        <Field t={t} label={field('schedule', 'Schedule')} value={terms.schedule || normalized.schedule} />
        <Field t={t} label={field('work_systems', 'Work system')} value={terms.work_systems || normalized.work_systems} />
        <Field t={t} label={field('route_directions', 'Route directions')} value={terms.route_directions || normalized.route_directions} />
        <Field t={t} label={field('night_driving', 'Night driving')} value={terms.night_driving || normalized.night_driving} />
        <Field
          t={t}
          label={field('body_types', 'Trailer / transport type')}
          value={terms.body_types || normalized.body_types || terms.cargo_types || normalized.cargo_types}
        />
        <Field t={t} label={field('work_conditions', 'Additional conditions')} value={terms.work_conditions || normalized.work_conditions} />
        <Field t={t} label={field('base', 'Base')} value={terms.base || company.city || payloadCompany.city} />
        <Field t={t} label={field('truck_brands', 'Trucks')} value={terms.truck_brands || normalized.truck_brands} />
        <Field t={t} label={field('body_type', 'Body type')} value={terms.body_type || normalized.body_type} />
        <Field
          t={t}
          label={field('additional', 'Additional')}
          value={terms.additional || normalized.additional_terms || terms.notes || need.notes || payloadNeed.notes}
        />
      </Section>

      <Section title={section('source', 'Source and submission')}>
        <Field t={t} label={field('source_profile', 'Source profile')} value={sourceProfile.name || sourceProfile.public_slug} />
        <Field t={t} label={field('landing_page', 'Landing page')} value={marketing.landing_page || normalized.landing_page} />
        <Field t={t} label={field('language', 'Language')} value={meta.language || payload.language} />
        <Field t={t} label={field('created_at', 'Created')} value={formatDate(lead.created_at)} />
        <Field t={t} label={field('converted_client', 'Converted client')} value={convertedId} />
      </Section>

      <Section title={section('consent', 'Consents / RODO')}>
        <Field t={t} label={field('rodo_consent', 'RODO consent')} value={consent.rodo_consent || normalized.rodo_consent} />
        <Field t={t} label={field('privacy_policy', 'Privacy policy')} value={consent.privacy_policy || normalized.privacy_policy} />
        <Field t={t} label={field('regulamin', 'Terms')} value={consent.regulamin || normalized.regulamin} />
        <Field t={t} label={field('consent_timestamp', 'Consent timestamp')} value={consent.consent_timestamp || normalized.consent_timestamp} />
        <Field t={t} label={field('marketing_contact', 'Marketing contact')} value={consent.marketing_contact_accepted} />
        <Field t={t} label={field('terms_version', 'Terms version')} value={consent.terms_version} />
        <Field t={t} label={field('privacy_version', 'Privacy version')} value={consent.privacy_version} />
      </Section>

      {moreSection ? (
        <details className="card overflow-hidden p-0 shadow-md shadow-slate-900/[0.03]">
          <summary className="cursor-pointer px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-50">
            {t('app.leads.client_detail.more_section', { defaultValue: 'History and system data' })}
          </summary>
          <div className="border-t border-slate-100 p-4">{moreSection}</div>
        </details>
      ) : null}
    </div>
  )
}
