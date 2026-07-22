import { useMemo, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import type { LeadCallResultCode } from '../../api/client'
import type { Lead } from '../../api/types'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { leadIntakeResolutionRejected } from '../../utils/intakeResolution'
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

function yesNo(value: unknown): string {
  if (value === true) return 'Да'
  if (value === false) return 'Нет'
  return '—'
}

function Field({ label, value }: { label: string; value: unknown }) {
  const rendered = Array.isArray(value) ? list(value) : typeof value === 'boolean' ? yesNo(value) : text(value)
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

  const normalized = record(lead.normalized)
  const payload = record(lead.payload)
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
    lead.company_name ||
    'Client Lead'
  const convertedId = text(lead.converted_client_id)
  const terminal = leadIntakeResolutionRejected(lead)
  const statusLabel = terminal
    ? 'Отклонён'
    : convertedId
      ? 'Клиент создан'
      : lead.status === 'processed'
        ? 'Новая анкета'
        : lead.status === 'rejected'
          ? 'Отклонён'
          : lead.status

  const history = useMemo(() => leadCallResultHistory(lead), [lead])

  const resultLabel = (code: string) =>
    t(`app.leads.detail.call_result.results.${code}`, { defaultValue: code })

  const noteRecommended =
    callResult === 'answered' ||
    callResult === 'callback_requested' ||
    callResult === 'interested' ||
    callResult === 'not_interested'

  const busy = patching || converting || savingCallResult

  return (
    <div className="space-y-5">
      <header className="card relative overflow-hidden p-5 shadow-md shadow-slate-900/[0.04] sm:p-6">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-brand-400 via-brand-500 to-brand-600/90" aria-hidden />
        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
              {t('app.leads.detail.call_result.kicker', { defaultValue: 'Обращение' })}
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">{companyName}</h1>
            <p className="mt-2 text-sm text-slate-600">
              {text(need.summary) || [text(need.people_count), text(need.what_needed)].filter(Boolean).join(' ') || 'Анкета транспортной компании'}
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
              <p className="mt-3 text-sm text-red-700">Лид отклонён и исключён из обработки кандидатов.</p>
            ) : null}
            <p className="mt-3 font-mono text-[11px] leading-relaxed text-slate-400 break-all">ID · {lead.id}</p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2 border-t border-slate-100 pt-4 lg:border-l lg:border-t-0 lg:pl-5 lg:pt-0">
            {terminal ? null : convertedId ? (
              <Link to={`${CRM_APP_PATHS.agencyClients}/${convertedId}`} className="btn-primary rounded-lg px-3 py-2 text-sm font-semibold">
                Открыть клиента
              </Link>
            ) : (
              <button
                type="button"
                className="btn-primary rounded-lg px-3 py-2 text-sm font-semibold"
                disabled={busy}
                onClick={() => void onConvert()}
              >
                {converting ? 'Создаём...' : 'Создать клиента'}
              </button>
            )}
            {!terminal ? (
              <>
                <button type="button" className="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={busy} onClick={() => void onStage('contacted')}>
                  Контакт установлен
                </button>
                <button type="button" className="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={busy} onClick={() => void onStage('qualified')}>
                  Квалифицировать
                </button>
                <button type="button" className="rounded-lg border border-red-200 bg-white px-3 py-2 text-sm text-red-800 hover:bg-red-50 disabled:opacity-60" disabled={busy} onClick={() => void onStage('lost')}>
                  Отклонить
                </button>
              </>
            ) : null}
          </div>
        </div>
      </header>

      {!terminal && onCallResult ? (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">
            {t('app.leads.detail.call_result.title', { defaultValue: 'Результат звонка' })}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.leads.detail.call_result.subtitle', {
              defaultValue: 'Перезвонить или что ещё хотят / думают — зафиксируйте после разговора.',
            })}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-1 block text-xs font-medium text-slate-600">
                {t('app.leads.detail.call_result.fields.result', { defaultValue: 'Результат' })}
              </span>
              <select
                className="input w-full"
                value={callResult}
                disabled={busy}
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
                    defaultValue: 'Комментарий к результату',
                  })}
                  {noteRecommended ? (
                    <span className="ml-1 font-normal text-slate-500">
                      (
                      {t('app.leads.detail.call_result.fields.note_recommended', {
                        defaultValue: 'желательно',
                      })}
                      )
                    </span>
                  ) : null}
                </span>
                <textarea
                  className="textarea mt-0 w-full"
                  rows={3}
                  maxLength={2000}
                  disabled={busy}
                  value={callNote}
                  onChange={(e) => setCallNote(e.target.value)}
                  placeholder={t('app.leads.detail.call_result.fields.note_placeholder', {
                    defaultValue: 'Например: перезвонить завтра в 15:00, спрашивает про ставку, думает…',
                  })}
                />
              </label>
              <p className="mt-1 text-xs text-slate-500">
                {t('app.leads.detail.call_result.fields.note_hint', {
                  defaultValue: 'Что хотят или думают: перезвонить, условия, сомнения, следующий шаг.',
                })}
              </p>
            </div>
          </div>
          <div className="mt-3 flex justify-end">
            <button
              type="button"
              className="btn-primary rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-60"
              disabled={busy}
              onClick={() => {
                void Promise.resolve(
                  onCallResult({ result: callResult, note: callNote.trim() }),
                ).then(() => setCallNote(''))
              }}
            >
              {savingCallResult
                ? t('common.saving', { defaultValue: 'Сохранение…' })
                : t('app.leads.detail.call_result.save', { defaultValue: 'Сохранить результат звонка' })}
            </button>
          </div>
          {history.length > 0 ? (
            <div className="mt-4 border-t border-slate-100 pt-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.leads.detail.call_result.history_title', { defaultValue: 'История звонков' })}
              </h3>
              <ul className="mt-2 space-y-2">
                {history.map((entry, idx) => (
                  <CallResultHistoryItem
                    key={`${entry.at || 'x'}-${entry.result}-${idx}`}
                    entry={entry}
                    formatDate={formatDate}
                    resultLabel={resultLabel}
                    noteLabel={t('app.leads.detail.call_result.fields.note', {
                      defaultValue: 'Комментарий',
                    })}
                  />
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}

      <Section title="Компания">
        <Field
          label="Название"
          value={company.name || normalized.company_name || normalized.company_name_hint || payloadCompany.name || lead.company_name}
        />
        <Field label="Юр. название" value={company.legal_name || payloadCompany.legal_name} />
        <Field label="NIP / VAT" value={company.tax_id || company.nip || company.vat || payloadCompany.tax_id} />
        <Field label="Страна" value={company.country || payloadCompany.country} />
        <Field label="Город" value={company.city || payloadCompany.city} />
        <Field label="Сайт" value={company.website || payloadCompany.website} />
        <Field label="Размер флота" value={company.fleet_size || payloadCompany.fleet_size} />
        <Field label="Тип перевозок" value={company.transport_type || payloadCompany.transport_type} />
      </Section>

      <Section title="Контактное лицо">
        <Field label="Имя" value={contact.full_name || payloadContact.full_name || normalized.full_name} />
        <Field label="Должность" value={contact.role || payloadContact.role} />
        <Field label="Email" value={contact.email || payloadContact.email || normalized.email} />
        <Field label="Телефон" value={contact.phone || payloadContact.phone || normalized.phone} />
        <Field label="WhatsApp" value={contact.whatsapp ?? payloadContact.whatsapp} />
      </Section>

      <Section title="Потребность">
        <Field label="Что нужно" value={need.what_needed || payloadNeed.what_needed} />
        <Field label="Сводка" value={need.summary || payloadNeed.summary} />
        <Field label="Сколько людей" value={need.people_count || payloadNeed.people_count} />
        <Field label="Тип сотрудничества" value={need.cooperation_type || payloadNeed.cooperation_type} />
        <Field label="Когда нужны" value={need.start_date || need.when_needed || payloadNeed.start_date || payloadNeed.when_needed} />
        <Field label="Требования" value={need.requirements || payloadNeed.requirements} />
        <Field label="Платные кампании" value={marketing.runs_paid_ads} />
      </Section>

      {fieldAnswers.length > 0 ? (
        <Section title="Ответы из формы Meta">
          {fieldAnswers.map((item, idx) => (
            <Field
              key={`${text(item.name) || 'field'}-${idx}`}
              label={text(item.name) || `Field ${idx + 1}`}
              value={item.values}
            />
          ))}
        </Section>
      ) : null}

      <Section title="Условия работы">
        <Field label="Ставка" value={terms.rate || normalized.rate} />
        <Field label="Kwota" value={terms.rate_amount || normalized.rate_amount} />
        <Field label="Waluta" value={terms.rate_currency || normalized.rate_currency} />
        <Field label="Okres" value={terms.rate_period || normalized.rate_period} />
        <Field label="Netto / brutto / B2B" value={terms.rate_tax_mode || normalized.rate_tax_mode} />
        <Field label="Premie / bonusy" value={terms.bonus || normalized.bonus} />
        <Field label="График" value={terms.schedule || normalized.schedule} />
        <Field label="System pracy" value={terms.work_systems || normalized.work_systems} />
        <Field label="Kierunki tras" value={terms.route_directions || normalized.route_directions} />
        <Field label="Jazda nocna" value={terms.night_driving || normalized.night_driving} />
        <Field label="Rodzaj naczepy / transportu" value={terms.body_types || normalized.body_types || terms.cargo_types || normalized.cargo_types} />
        <Field label="Warunki dodatkowe" value={terms.work_conditions || normalized.work_conditions} />
        <Field label="База" value={terms.base || company.city || payloadCompany.city} />
        <Field label="Машины" value={terms.truck_brands || normalized.truck_brands} />
        <Field label="Тип кузова" value={terms.body_type || normalized.body_type} />
        <Field label="Дополнительно" value={terms.additional || normalized.additional_terms || terms.notes || need.notes || payloadNeed.notes} />
      </Section>

      <Section title="Источник и отправка">
        <Field label="Профиль источника" value={sourceProfile.name || sourceProfile.public_slug} />
        <Field label="Landing page" value={marketing.landing_page || normalized.landing_page} />
        <Field label="Язык" value={meta.language || payload.language} />
        <Field label="Создано" value={formatDate(lead.created_at)} />
        <Field label="Converted client" value={convertedId} />
      </Section>

      <Section title="Zgody / RODO">
        <Field label="RODO consent" value={consent.rodo_consent || normalized.rodo_consent} />
        <Field label="Privacy policy" value={consent.privacy_policy || normalized.privacy_policy} />
        <Field label="Regulamin" value={consent.regulamin || normalized.regulamin} />
        <Field label="Consent timestamp" value={consent.consent_timestamp || normalized.consent_timestamp} />
        <Field label="Marketing contact" value={consent.marketing_contact_accepted} />
        <Field label="Terms version" value={consent.terms_version} />
        <Field label="Privacy version" value={consent.privacy_version} />
      </Section>

      {moreSection ? (
        <details className="card overflow-hidden p-0 shadow-md shadow-slate-900/[0.03]">
          <summary className="cursor-pointer px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-50">
            История и служебные данные
          </summary>
          <div className="border-t border-slate-100 p-4">{moreSection}</div>
        </details>
      ) : null}
    </div>
  )
}
