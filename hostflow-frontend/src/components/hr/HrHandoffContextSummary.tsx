import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { HrHandoffInboxItem, HrWhyReady } from '../../api/hrWorkspace'
import { formatShortDateIso } from './hrEmployeeUiFormat'
import { Link } from 'react-router-dom'

type Props = {
  row: HrHandoffInboxItem
}

function strVal(v: unknown): string | null {
  return typeof v === 'string' && v.trim() ? v.trim() : null
}

/** Read-only Why Ready + live target — displays backend read model only (no snapshot reconstruction). */
export default function HrHandoffContextSummary({ row }: Props) {
  const { t } = useI18n()
  const why: HrWhyReady | null | undefined = row.why_ready
  const liveTarget = row.live_target_work
  const name = row.candidate_display_name || '—'
  const vacancy =
    strVal(liveTarget?.vacancy_title) ||
    strVal(why?.target_work_as_of?.vacancy_title_as_of) ||
    null
  const employer = strVal(liveTarget?.employer_name)
  const requested = row.handoff.requested_at
  const fits = why?.fits_decision
  const fitsDecision = fits && typeof fits === 'object' ? strVal(fits.decision) : null
  const fitsReason = fits && typeof fits === 'object' ? strVal(fits.reason) : null
  const emittedAt =
    why?.context_refs && typeof why.context_refs === 'object'
      ? strVal(why.context_refs.emitted_at)
      : null
  const verdicts = Array.isArray(why?.requirement_verdicts_as_of) ? why.requirement_verdicts_as_of : []
  const evidenceRefs = Array.isArray(why?.evidence_refs) ? why.evidence_refs : []
  const asOfCitizenship =
    why?.as_of && typeof why.as_of === 'object' && why.as_of.identity && typeof why.as_of.identity === 'object'
      ? strVal(why.as_of.identity.citizenship)
      : null

  return (
    <section id="hr-handoff-summary" className="scroll-mt-24 rounded-xl border border-slate-200 bg-slate-50/80 p-4 text-sm text-slate-700">
      <h2 className="font-semibold text-slate-900">
        {t('app.hr.employee_operational.section_why_ready', { defaultValue: 'Why Ready' })}
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        {t('app.hr.review_case.why_ready_hint', {
          defaultValue:
            'Manifest decisions and as-of audit from Transfer. Current identity and documents come from live Person and Document Hub.',
        })}
      </p>
      <dl className="mt-3 grid gap-2 sm:grid-cols-2">
        <div>
          <dt className="text-xs text-slate-500">{t('app.hr.employee_operational.name', { defaultValue: 'Name' })}</dt>
          <dd className="font-medium text-slate-900">{name}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">{t('app.hr.employee_operational.handoff_when', { defaultValue: 'Handoff date' })}</dt>
          <dd className="font-medium">{formatShortDateIso(requested)}</dd>
        </div>
        {vacancy ? (
          <div>
            <dt className="text-xs text-slate-500">{t('app.hr.employee_operational.vacancy_card_title', { defaultValue: 'Vacancy' })}</dt>
            <dd className="font-medium">{vacancy}</dd>
          </div>
        ) : null}
        {employer ? (
          <div>
            <dt className="text-xs text-slate-500">{t('app.hr.employee_operational.employer', { defaultValue: 'Employer' })}</dt>
            <dd className="font-medium">{employer}</dd>
          </div>
        ) : null}
        {fitsDecision ? (
          <div>
            <dt className="text-xs text-slate-500">{t('app.hr.why_ready.fits', { defaultValue: 'Fits decision' })}</dt>
            <dd className="font-medium">
              {fitsDecision}
              {fitsReason ? <span className="ml-1 text-slate-500">({fitsReason})</span> : null}
            </dd>
          </div>
        ) : null}
        {emittedAt ? (
          <div>
            <dt className="text-xs text-slate-500">{t('app.hr.why_ready.emitted_at', { defaultValue: 'Manifest emitted' })}</dt>
            <dd className="font-medium">{formatShortDateIso(emittedAt)}</dd>
          </div>
        ) : null}
        {asOfCitizenship ? (
          <div>
            <dt className="text-xs text-slate-500">
              {t('app.hr.why_ready.citizenship_as_of', { defaultValue: 'Citizenship at transfer' })}
            </dt>
            <dd className="font-medium">{asOfCitizenship}</dd>
          </div>
        ) : null}
      </dl>

      {verdicts.length > 0 ? (
        <div className="mt-3 border-t border-slate-200 pt-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.hr.why_ready.verdicts', { defaultValue: 'Requirement verdicts (as-of)' })}
          </h3>
          <ul className="mt-2 space-y-1 text-sm">
            {verdicts.slice(0, 12).map((v, i) => {
              const code = strVal(v.requirement_code) || `verdict-${i}`
              const status = strVal(v.status) || '—'
              return (
                <li key={`${code}-${i}`} className="flex justify-between gap-2">
                  <span className="text-slate-700">{code}</span>
                  <span className="font-medium text-slate-900">{status}</span>
                </li>
              )
            })}
          </ul>
        </div>
      ) : null}

      {evidenceRefs.length > 0 ? (
        <div className="mt-3 border-t border-slate-200 pt-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.hr.why_ready.evidence', { defaultValue: 'Evidence refs (as-of)' })}
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            {t('app.hr.why_ready.evidence_hint', {
              defaultValue: `${evidenceRefs.length} document ref(s) at transfer — live files are in Document Hub.`,
              count: evidenceRefs.length,
            })}
          </p>
        </div>
      ) : null}

      {!why ? (
        <p className="mt-3 text-xs text-amber-700">
          {t('app.hr.why_ready.missing', {
            defaultValue: 'No ready_for_employment.v1 Why Ready payload on this handoff.',
          })}
        </p>
      ) : null}

      {row.handoff.candidate_id ? (
        <p className="mt-3 text-xs">
          <Link
            to={`${CRM_APP_PATHS.candidates}/${encodeURIComponent(String(row.handoff.candidate_id))}`}
            className="font-medium text-brand-700 hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            {t('app.hr.employee_operational.open_recruitment_record', {
              defaultValue: 'Open recruitment record (read-only)',
            })}
          </Link>
        </p>
      ) : null}
    </section>
  )
}
