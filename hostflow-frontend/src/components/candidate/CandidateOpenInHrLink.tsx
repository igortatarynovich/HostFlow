import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { getWorkforceEmployeeByCandidate, type WorkforceEmployee } from '../../api/workforce'
import { useI18n } from '../../i18n'

type Props = {
  candidateId: string
  enabled?: boolean
}

export default function CandidateOpenInHrLink({ candidateId, enabled = true }: Props) {
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

  if (!enabled || loading || !employee?.id) return null

  return (
    <Link
      to={`${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(employee.id)}`}
      className="inline-flex items-center rounded-lg border border-brand-200 bg-brand-50 px-3 py-1.5 text-sm font-medium text-brand-900 hover:bg-brand-100"
    >
      {t('app.candidate_card.open_in_hr', { defaultValue: 'Open in HR dossier →' })}
    </Link>
  )
}
