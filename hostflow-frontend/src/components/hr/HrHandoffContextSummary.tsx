import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { HrHandoffInboxItem } from '../../api/hrWorkspace'
import { formatShortDateIso } from './hrEmployeeUiFormat'

type Props = {
  row: HrHandoffInboxItem
}

function pickString(obj: Record<string, unknown> | null | undefined, keys: string[]): string | null {
  if (!obj) return null
  for (const k of keys) {
    const v = obj[k]
    if (typeof v === 'string' && v.trim()) return v.trim()
  }
  return null
}

/** Read-only handoff context for inbox case view (no raw JSON wall). */
export default function HrHandoffContextSummary({ row }: Props) {
  const { t } = useI18n()
  const snap = row.snapshot && typeof row.snapshot === 'object' ? row.snapshot : null
  const name =
    row.candidate_display_name ||
    pickString(snap, ['display_name', 'full_name', 'candidate_name']) ||
    [pickString(snap, ['first_name']), pickString(snap, ['last_name'])].filter(Boolean).join(' ') ||
    '—'
  const vacancy = pickString(snap, ['vacancy_title', 'job_title', 'position_title'])
  const notes = pickString(snap, ['notes', 'recruiter_notes', 'handoff_notes', 'summary'])
  const requested = row.handoff.requested_at

  return (
    <section className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 text-sm text-slate-700">
      <h2 className="font-semibold text-slate-900">
        {t('app.hr.employee_operational.section_source', { defaultValue: 'Recruitment handoff' })}
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        {t('app.hr.review_case.handoff_summary_hint', {
          defaultValue: 'Read-only context from recruitment at transfer. Verify documents in the list above.',
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
          <div className="sm:col-span-2">
            <dt className="text-xs text-slate-500">{t('app.hr.employee_operational.vacancy_card_title', { defaultValue: 'Vacancy' })}</dt>
            <dd className="font-medium">{vacancy}</dd>
          </div>
        ) : null}
      </dl>
      {notes ? (
        <p className="mt-3 whitespace-pre-wrap border-t border-slate-200 pt-3 text-sm text-slate-800">{notes}</p>
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
