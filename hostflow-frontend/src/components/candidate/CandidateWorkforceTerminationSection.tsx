import { Link } from 'react-router-dom'
import type { CandidateExtra } from '../../api/types'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { Alert } from '../ui/Alert'

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
    <Alert
      semantic="warning"
      title={t('app.candidate_card.workforce_termination.title', {
        defaultValue: 'HR employment ended',
      })}
    >
      <p>
        {t('app.candidate_card.workforce_termination.lead', {
          defaultValue:
            'Recorded from the HR workspace when the linked employee was terminated or a termination date was set.',
        })}
      </p>
      <dl className="mt-2 grid gap-2 sm:grid-cols-2 text-xs">
        <div>
          <dt className="opacity-70">
            {t('app.candidate_card.workforce_termination.status', { defaultValue: 'Employee status' })}
          </dt>
          <dd className="font-medium">{wt.employee_status || '—'}</dd>
        </div>
        <div>
          <dt className="opacity-70">
            {t('app.candidate_card.workforce_termination.date', { defaultValue: 'Termination date' })}
          </dt>
          <dd className="font-medium">{wt.termination_date || '—'}</dd>
        </div>
        <div>
          <dt className="opacity-70">
            {t('app.candidate_card.workforce_termination.recorded_at', { defaultValue: 'Recorded at' })}
          </dt>
          <dd className="font-medium">{wt.recorded_at || '—'}</dd>
        </div>
        <div>
          <dt className="opacity-70">
            {t('app.candidate_card.workforce_termination.by', { defaultValue: 'Recorded by (user id)' })}
          </dt>
          <dd className="break-all font-medium">{wt.recorded_by_user_id || '—'}</dd>
        </div>
      </dl>
      <div className="mt-2">
        <Link className="text-xs font-medium underline-offset-2 hover:underline" to={CRM_APP_PATHS.hrEmployees}>
          {t('app.candidate_card.workforce_termination.open_hr', { defaultValue: 'Open HR · Employees' })}
        </Link>
      </div>
    </Alert>
  )
}
