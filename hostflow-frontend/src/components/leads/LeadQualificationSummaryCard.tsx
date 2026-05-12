import type { ReactNode } from 'react'

import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import { formatLeadPipelineError } from '../../utils/leadPipelineErrors'
import {
  formatQualificationReasonLabel,
  readLeadQualificationPreview,
} from '../../utils/leadQualificationPreview'

type Props = {
  lead: Lead
  isServicesTenant?: boolean
  formatAt: (iso: string | null | undefined) => string
  className?: string
}

function normRecord(normalized: unknown): Record<string, unknown> {
  if (!normalized || typeof normalized !== 'object' || Array.isArray(normalized)) return {}
  return normalized as Record<string, unknown>
}

function str(v: unknown): string | null {
  if (v == null) return null
  const s = String(v).trim()
  return s || null
}

function formatUtm(utm: unknown): string | null {
  if (!utm || typeof utm !== 'object' || Array.isArray(utm)) return null
  const parts: string[] = []
  for (const [k, val] of Object.entries(utm as Record<string, unknown>)) {
    if (val == null) continue
    const s = String(val).trim()
    if (s) parts.push(`${k}: ${s}`)
  }
  return parts.length ? parts.join(' · ') : null
}

function listStr(v: unknown): string | null {
  if (Array.isArray(v)) {
    const xs = v.map((x) => String(x).trim()).filter(Boolean)
    return xs.length ? xs.join(', ') : null
  }
  return str(v)
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mt-3 first:mt-0">
      <h4 className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{title}</h4>
      <div className="mt-1 grid gap-1 text-xs sm:grid-cols-2">{children}</div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: ReactNode }) {
  if (value == null || value === '' || value === '—') return null
  return (
    <div className="flex flex-col gap-0.5 sm:col-span-2 sm:flex-row sm:gap-2">
      <span className="shrink-0 text-slate-500">{label}</span>
      <span className="min-w-0 break-words text-slate-900">{value}</span>
    </div>
  )
}

function readRuleMatch(
  n: Record<string, unknown>,
): { rule_id?: string | null; note?: string | null } | null {
  const raw = n.lead_qualification_rule_match_v1
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const o = raw as Record<string, unknown>
  return {
    rule_id: o.rule_id != null ? String(o.rule_id) : null,
    note: o.note != null ? String(o.note) : null,
  }
}

/**
 * Slice 3: compact read-only qualification snapshot (meta / CSV agency leads).
 * No new scoring — surfaces existing `normalized` + preview + pipeline errors.
 */
export default function LeadQualificationSummaryCard({
  lead,
  isServicesTenant = false,
  formatAt,
  className = '',
}: Props) {
  const { t } = useI18n()
  const src = String(lead.source || '').toLowerCase()
  const show =
    !isServicesTenant && !lead.candidate_id && (src === 'meta' || src === 'csv_import')
  if (!show) return null

  const n = normRecord(lead.normalized)
  const preview = readLeadQualificationPreview(lead.normalized)
  const err = lead.error?.trim() || ''
  const isFitBlock = err === 'LEAD_FIT_NO_MATCH' || err === 'LEAD_FIT_NEEDS_INFO'
  const fitEffective = n.lead_fit_evaluation_effective_v1
  const fitEffectiveKnown = fitEffective === true || fitEffective === false
  const ruleMatch = readRuleMatch(n)

  const email = str(n.email)
  const phone = str(n.phone)
  const contactComplete = Boolean(email && email.includes('@') && phone && /\d/.test(phone))
  const contactKey = contactComplete
    ? 'app.leads.detail.qualification_summary.contact_complete_yes'
    : email || phone
      ? 'app.leads.detail.qualification_summary.contact_partial'
      : 'app.leads.detail.qualification_summary.contact_missing'

  const poolIntent = n.recruitment_pool_intent_v1 === true

  const hasAny =
    preview ||
    isFitBlock ||
    email ||
    phone ||
    str(n.country) ||
    str(n.geo_country) ||
    str(n.nationality) ||
    listStr(n.languages) ||
    str(n.language) ||
    listStr(n.documents) ||
    n.experience_eu_years != null ||
    n.driving_experience_in_europe != null ||
    (lead.ad_id != null ? String(lead.ad_id) : null) ||
    str(n.form_id) ||
    formatUtm(n.utm) ||
    str(n.created_time) ||
    lead.vacancy_id ||
    lead.suggested_vacancy_id ||
    str(n.resolved_vacancy_id) ||
    lead.funnel_id != null ||
    poolIntent ||
    fitEffectiveKnown ||
    (ruleMatch && (ruleMatch.rule_id || ruleMatch.note))

  if (!hasAny) return null

  const fitStatus = preview?.fit_status || null
  const fitStatusDisplay = fitStatus
    ? (() => {
        const k = `app.leads.qualification.fit_status.${fitStatus}`
        const tr = t(k)
        return tr === k ? fitStatus : tr
      })()
    : null

  return (
    <div
      className={`rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-800 shadow-sm ${className}`.trim()}
    >
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-600">
        {t('app.leads.detail.qualification_summary.title')}
      </div>
      <p className="mt-0.5 text-[11px] text-slate-500">{t('app.leads.detail.qualification_summary.subtitle')}</p>

      <Section title={t('app.leads.detail.qualification_summary.section_source')}>
        <Row label={t('app.leads.table.source')} value={lead.source || null} />
        <Row label={t('app.leads.detail.ad_id')} value={lead.ad_id != null ? String(lead.ad_id) : null} />
        <Row label={t('app.leads.detail.qualification_summary.form_id')} value={str(n.form_id)} />
        <Row
          label={t('app.leads.detail.qualification_summary.created_time')}
          value={str(n.created_time)}
        />
        <Row label={t('app.leads.detail.qualification_summary.utm')} value={formatUtm(n.utm)} />
      </Section>

      <Section title={t('app.leads.detail.qualification_summary.section_contact')}>
        <Row label={t('app.leads.detail.qualification_summary.contact_complete')} value={t(contactKey)} />
        <Row label={t('app.leads.detail.qualification_summary.email')} value={email} />
        <Row label={t('app.leads.detail.qualification_summary.phone')} value={phone} />
      </Section>

      <Section title={t('app.leads.detail.qualification_summary.section_profile')}>
        <Row
          label={t('app.leads.detail.intake_resolution.experience_eu')}
          value={n.experience_eu_years != null ? String(n.experience_eu_years) : null}
        />
        <Row
          label={t('app.leads.detail.qualification_summary.driving_eu')}
          value={str(n.driving_experience_in_europe)}
        />
        <Row
          label={t('app.leads.detail.qualification_summary.documents')}
          value={listStr(n.documents)}
        />
        <Row
          label={t('app.leads.detail.qualification_summary.nationality')}
          value={str(n.nationality) || str(n.nationality_code)}
        />
        <Row label={t('app.leads.detail.intake_resolution.country')} value={str(n.country) || str(n.geo_country)} />
        <Row label={t('app.leads.detail.intake_resolution.in_poland')} value={str(n.in_poland)} />
        <Row
          label={t('app.leads.detail.qualification_summary.poland_stay')}
          value={str(n.poland_stay_basis) || str(n.poland_stay_basis_raw)}
        />
        <Row
          label={t('app.leads.detail.qualification_summary.languages')}
          value={listStr(n.languages) || str(n.language)}
        />
      </Section>

      <Section title={t('app.leads.detail.qualification_summary.section_vacancy')}>
        <Row
          label={t('app.leads.detail.qualification_summary.vacancy_routed')}
          value={lead.vacancy_title || lead.vacancy_id || null}
        />
        <Row
          label={t('app.leads.detail.qualification_summary.suggested_vacancy')}
          value={lead.suggested_vacancy_id || preview?.suggested_vacancy_id || null}
        />
        <Row
          label={t('app.leads.detail.qualification_summary.resolved_vacancy_id')}
          value={str(n.resolved_vacancy_id)}
        />
        <Row
          label={t('app.leads.detail.qualification_summary.funnel')}
          value={lead.funnel_id != null ? String(lead.funnel_id) : null}
        />
        <Row
          label={t('app.leads.detail.qualification_summary.pool_intent')}
          value={
            poolIntent ? t('app.leads.detail.qualification_summary.pool_intent_yes') : t('app.leads.detail.qualification_summary.pool_intent_no')
          }
        />
      </Section>

      <Section title={t('app.leads.detail.qualification_summary.section_fit')}>
        <Row
          label={t('app.leads.detail.qualification_summary.fit_effective')}
          value={
            fitEffectiveKnown
              ? fitEffective
                ? t('app.leads.detail.qualification_summary.fit_effective_on')
                : t('app.leads.detail.qualification_summary.fit_effective_off')
              : null
          }
        />
        {isFitBlock ? (
          <Row label={t('app.leads.detail.qualification_summary.pipeline')} value={formatLeadPipelineError(err, t)} />
        ) : null}
        {preview ? (
          <>
            <Row
              label={t('app.leads.qualification.fit_status_label')}
              value={fitStatusDisplay}
            />
            <Row
              label={t('app.leads.detail.qualification_summary.evaluated_at')}
              value={preview.evaluated_at ? formatAt(preview.evaluated_at) : null}
            />
          </>
        ) : !isFitBlock ? (
          <p className="mt-1 text-xs text-slate-600 sm:col-span-2">
            {t('app.leads.detail.qualification_summary.no_preview')}
          </p>
        ) : null}
        {preview?.fit_reasons && preview.fit_reasons.length > 0 ? (
          <div className="sm:col-span-2">
            <div className="text-slate-500">{t('app.leads.qualification.reasons_title')}</div>
            <ul className="mt-0.5 list-inside list-disc text-slate-800">
              {preview.fit_reasons.map((r) => (
                <li key={r}>{formatQualificationReasonLabel(r, t)}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </Section>

      {ruleMatch && (ruleMatch.rule_id || ruleMatch.note) ? (
        <Section title={t('app.leads.detail.qualification_summary.section_rule')}>
          <Row label={t('app.leads.detail.qualification_summary.rule_id')} value={ruleMatch.rule_id} />
          <Row label={t('app.leads.detail.qualification_summary.rule_note')} value={ruleMatch.note} />
        </Section>
      ) : null}
    </div>
  )
}
