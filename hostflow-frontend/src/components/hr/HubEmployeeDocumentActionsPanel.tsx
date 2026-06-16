import { useEffect, useState } from 'react'
import { getWorkforceEmployee } from '../../api/workforce'
import { useI18n } from '../../i18n'
import { EmployeeDocumentActionsPanel } from './EmployeeDocumentActionsPanel'

export function HubEmployeeDocumentActionsPanel({ employeeId }: { employeeId: string }) {
  const { t } = useI18n()
  const [candidateId, setCandidateId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const employee = await getWorkforceEmployee(employeeId)
        if (!cancelled) setCandidateId(employee.candidate_id || null)
      } catch {
        if (!cancelled) setCandidateId(null)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [employeeId])

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
  }

  if (!candidateId) {
    return (
      <p className="text-sm text-slate-500">
        {t('app.hr.document_actions.no_candidate_link', {
          defaultValue: 'This employee has no linked candidate — document actions are unavailable.',
        })}
      </p>
    )
  }

  return (
    <EmployeeDocumentActionsPanel
      candidateId={candidateId}
      ownerContext={{ employee_id: employeeId, candidate_id: candidateId }}
    />
  )
}
