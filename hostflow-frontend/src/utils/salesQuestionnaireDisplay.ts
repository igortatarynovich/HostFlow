import type { LocaleCode } from '../i18n'
import { fieldOptionsForCode } from './intakePresentationFieldOptions'
import { readSalesQuestionnaireSummary } from './salesQuestionnaire'

type TFn = (key: string, options?: { defaultValue?: string }) => string

const FIELD_LABELS_PL: Record<string, string> = {
  need_type: 'Potrzeba',
  primary_outcome: 'Cel',
  recruitment_roles: 'Stanowiska',
  recruitment_other_role: 'Inne stanowisko',
  recruitment_headcount: 'Liczba pracowników',
  work_location_country: 'Kraj pracy',
  work_location_city: 'Miasto pracy',
  application_channel: 'Kanał zgłoszeń',
  job_posting_ready: 'Ogłoszenie o pracę',
  recruitment_materials: 'Materiały rekrutacyjne',
  promotion_subject: 'Przedmiot promocji',
  industry: 'Branża',
  target_audience_description: 'Grupa docelowa',
  qualified_lead_definition: 'Jakościowy lead',
  client_geo_scope: 'Zasięg geograficzny',
  client_geo_detail: 'Miasto / region',
  conversion_destination: 'Cel konwersji',
  offer_ready: 'Gotowość oferty',
  marketing_materials: 'Materiały reklamowe',
  prior_ads_experience: 'Doświadczenie z reklamami',
  monthly_ad_budget: 'Budżet reklamowy',
  start_timeline: 'Termin startu',
  decision_maker: 'Decydent',
  contact_full_name: 'Imię i nazwisko',
  contact_company_name: 'Firma',
  contact_phone: 'Telefon',
  contact_email: 'E-mail',
  contact_website: 'Strona WWW',
  additional_notes: 'Uwagi',
}

function labelForField(key: string): string {
  return FIELD_LABELS_PL[key] || key.replace(/_/g, ' ')
}

function resolveOptionLabel(
  fieldKey: string,
  raw: unknown,
  t: TFn,
  locale: LocaleCode,
): string {
  const code = `service_sales.targeted_advertising.${fieldKey}`
  const options = fieldOptionsForCode(code, t, locale)
  const values = Array.isArray(raw) ? raw.map(String) : [String(raw)]
  const labels = values
    .map((value) => options.find((option) => option.value === value)?.label || value.replace(/_/g, ' '))
    .filter(Boolean)
  return labels.join(', ')
}

export type SalesQuestionnaireAnswerRow = {
  key: string
  label: string
  value: string
}

export function buildSalesQuestionnaireAnswerRows(
  lead: { normalized?: Record<string, unknown> | null },
  t: TFn,
  locale: LocaleCode,
): SalesQuestionnaireAnswerRow[] {
  const summary = readSalesQuestionnaireSummary(lead)
  const rows: SalesQuestionnaireAnswerRow[] = []

  for (const [key, raw] of Object.entries(summary)) {
    if (key.endsWith('_label')) continue
    if (raw == null || raw === '' || (Array.isArray(raw) && raw.length === 0)) continue
    const rendered =
      typeof raw === 'string' && summary[`${key}_label`]
        ? String(summary[`${key}_label`])
        : resolveOptionLabel(key, raw, t, locale)
    if (!rendered.trim()) continue
    rows.push({ key, label: labelForField(key), value: rendered })
  }

  return rows
}
