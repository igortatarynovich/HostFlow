import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { getWorkforceEmployeeByCandidate, type WorkforceEmployee } from '../../api/workforce'
import { useI18n } from '../../i18n'

type Props = {
  candidateId: string
  enabled?: boolean
  /** When workforce row does not exist yet (delayed path), link to handoff review. */
  fallbackHandoffId?: string | null
}

export default function CandidateOpenInHrLink({
  candidateId,
  enabled = true,
  fallbackHandoffId = null,
}: Props) {
  const { t } = useI18n()
  const [employee, setEmployee] = useState<WorkforceEmployee | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!enabled || !candidateId?.trim()) {
      setEmployee(null)
      return
    }
    let active = true
    setLoading(true)
    getWorkforceEmployeeByCandidate(candidateId)
      .then((row) => {
        if (active) setEmployee(row)
      })
      .catch(() => {
        if (active) setEmployee(null)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [candidateId, enabled])

  if (!enabled || loading) return null

  const handoffId = String(fallbackHandoffId || '').trim()
  if (employee?.id) {
    return (
      <Link
        to={`${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(employee.id)}#hr-verification`}
        className="inline-flex items-center rounded-lg border border-brand-200 bg-brand-50 px-3 py-1.5 text-sm font-medium text-brand-900 hover:bg-brand-100"
      >
        {t('app.candidate_card.open_in_hr', { defaultValue: 'Open in HR dossier →' })}
      </Link>
    )
  }

  if (!handoffId) return null

  return (
    <Link
      to={`${CRM_APP_PATHS.hrHandoffs}/${encodeURIComponent(handoffId)}`}
      className="inline-flex items-center rounded-lg border border-brand-200 bg-brand-50 px-3 py-1.5 text-sm font-medium text-brand-900 hover:bg-brand-100"
    >
      {t('app.candidate_card.open_in_hr_handoff', { defaultValue: 'Open HR handoff review →' })}
    </Link>
  )
}
