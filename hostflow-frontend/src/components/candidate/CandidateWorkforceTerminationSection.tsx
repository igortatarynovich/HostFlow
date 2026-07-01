import { Link } from 'react-router-dom'
import type { CandidateExtra } from '../../api/types'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

export type WorkforceTerminationExtra = {
  employee_status?: string | null
  termination_date?: string | null
  recorded_at?: string | null
  recorded_by_user_id?: string | null
}

function readTermination(extra: CandidateExtra | null | undefined): WorkforceTerminationExtra | null {
  const raw = extra && typeof (extra as { workforce_termination?: unknown }).workforce_termination === 'object'
    ? (extra as { workforce_termination?: WorkforceTerminationExtra }).workforce_termination
    : null
  if (!raw || typeof raw !== 'object') return null
  return raw
}

export function CandidateWorkforceTerminationSection({
  extra,
}: {
  extra: CandidateExtra | null | undefined
}) {
  const { t } = useI18n()
  const wt = readTermination(extra)
  if (!wt) return null

  return (
    <section
      className="rounded-lg border border-amber-200 bg-amber-50/80 px-3 py-3 text-sm text-amber-950"
      aria-label={t('app.candidate_card.workforce_termination.title', {
        defaultValue: 'HR employment ended',
      })}
    >
      <h3 className="text-xs font-semibold uppercase tracking-wide text-amber-900/90 mb-2">
        {t('app.candidate_card.workforce_termination.title', {
          defaultValue: 'HR employment ended',
        })}
      </h3>
      <p className="text-xs text-amber-900/80 mb-2">
        {t('app.candidate_card.workforce_termination.lead', {
          defaultValue:
            'Recorded from the HR workspace when the linked employee was terminated or a termination date was set.',
        })}
      </p>
      <dl className="grid gap-1 sm:grid-cols-2 text-xs">
        <div>
          <dt className="text-amber-900/70">
            {t('app.candidate_card.workforce_termination.status', { defaultValue: 'Employee status' })}
          </dt>
          <dd className="font-medium">{wt.employee_status || '—'}</dd>
        </div>
        <div>
          <dt className="text-amber-900/70">
            {t('app.candidate_card.workforce_termination.date', { defaultValue: 'Termination date' })}
          </dt>
          <dd className="font-medium">{wt.termination_date || '—'}</dd>
        </div>
        <div>
          <dt className="text-amber-900/70">
            {t('app.candidate_card.workforce_termination.recorded_at', { defaultValue: 'Recorded at' })}
          </dt>
          <dd className="font-mono text-[11px] break-all">{wt.recorded_at || '—'}</dd>
        </div>
        <div>
          <dt className="text-amber-900/70">
            {t('app.candidate_card.workforce_termination.by', { defaultValue: 'Recorded by (user id)' })}
          </dt>
          <dd className="font-mono text-[11px] break-all">{wt.recorded_by_user_id || '—'}</dd>
        </div>
      </dl>
      <div className="mt-2 pt-2 border-t border-amber-200/80">
        <Link
          className="text-xs font-medium text-amber-950 underline-offset-2 hover:underline"
          to={CRM_APP_PATHS.hrEmployees}
        >
          {t('app.candidate_card.workforce_termination.open_hr', { defaultValue: 'Open HR · Employees' })}
        </Link>
      </div>
    </section>
  )
}
