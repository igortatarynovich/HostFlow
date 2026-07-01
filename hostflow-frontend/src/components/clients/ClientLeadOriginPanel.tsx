import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

type IntakeRecord = Record<string, unknown>

function record(value: unknown): IntakeRecord {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as IntakeRecord) : {}
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

type ClientLeadOriginPanelProps = {
  companyExtra: IntakeRecord | null | undefined
}

export function ClientLeadOriginPanel({ companyExtra }: ClientLeadOriginPanelProps) {
  const { t } = useI18n()
  const extra = record(companyExtra)
  const sourceLeadId = text(extra.source_lead_id)
  if (!sourceLeadId) return null

  const intake = record(extra.intake)
  const company = record(intake.company_profile)
  const contact = record(intake.contact_person)
  const need = record(intake.need)

  const summary =
    text(need.summary) ||
    [text(need.what_needed), text(need.people_count)].filter(Boolean).join(' · ') ||
    text(company.name)

  return (
    <section className="rounded-xl border border-brand-100 bg-brand-50/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
            {t('app.clients.from_lead_badge', { defaultValue: 'Создан из анкеты (лид)' })}
          </p>
          <p className="mt-1 text-sm text-slate-700">
            {t('app.clients.from_lead_hint', {
              defaultValue:
                'Данные перенесены из заполненной анкеты. Проверьте профиль, настройте доступ и продолжайте работу с клиентом.',
            })}
          </p>
          {summary ? <p className="mt-2 text-sm font-medium text-slate-900">{summary}</p> : null}
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            {text(contact.full_name) ? (
              <div>
                <dt className="text-xs text-slate-500">{t('app.clients.from_lead_contact', { defaultValue: 'Контакт' })}</dt>
                <dd className="font-medium text-slate-900">{text(contact.full_name)}</dd>
              </div>
            ) : null}
            {text(contact.phone) || text(contact.email) ? (
              <div>
                <dt className="text-xs text-slate-500">{t('app.clients.from_lead_reach', { defaultValue: 'Связь' })}</dt>
                <dd className="font-medium text-slate-900">
                  {[text(contact.phone), text(contact.email)].filter(Boolean).join(' · ')}
                </dd>
              </div>
            ) : null}
          </dl>
        </div>
        <Link
          to={`${CRM_APP_PATHS.leads}/${sourceLeadId}`}
          className="btn-secondary btn-sm shrink-0"
        >
          {t('app.clients.open_source_lead', { defaultValue: 'Открыть лид' })}
        </Link>
      </div>
    </section>
  )
}
