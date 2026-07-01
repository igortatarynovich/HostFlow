import { useCallback, useEffect, useState } from 'react'
import {
  getWorkforceEmployeeOperationalProfile,
  getWorkforceHrBundle,
  patchWorkforceWorkEligibility,
  patchWorkforceWorkEligibilityPaymentRequirement,
  type WorkforceHrBundle,
  type WorkforceTimelineEvent,
} from '../../api/workforce'
import { useI18n } from '../../i18n'
import WorkEligibilityJourneyWorkspace from './WorkEligibilityJourneyWorkspace'

type Props = {
  employeeId: string
  manage: boolean
  onChanged?: () => void
}

export default function WorkEligibilityJourneyPanel({ employeeId, manage, onChanged }: Props) {
  const { t } = useI18n()
  const [bundle, setBundle] = useState<WorkforceHrBundle | null>(null)
  const [timeline, setTimeline] = useState<WorkforceTimelineEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const [nextBundle, profile] = await Promise.all([
        getWorkforceHrBundle(employeeId),
        getWorkforceEmployeeOperationalProfile(employeeId).catch(() => null),
      ])
      setBundle(nextBundle)
      setTimeline(profile?.timeline ?? [])
    } catch {
      setBundle(null)
      setTimeline([])
    } finally {
      setLoading(false)
    }
  }, [employeeId])

  useEffect(() => {
    void reload()
  }, [reload])

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
  }

  if (!bundle) {
    return (
      <p className="text-sm text-rose-700">
        {t('app.hr.work_eligibility.journey_error', { defaultValue: 'Could not load journey.' })}
      </p>
    )
  }

  return (
    <WorkEligibilityJourneyWorkspace
      employeeId={employeeId}
      profile={bundle.work_eligibility_profile}
      paymentRequirements={bundle.work_eligibility_payment_requirements ?? []}
      docSummary={bundle.hr_document_context_summary ?? { items: [] }}
      timeline={timeline}
      manage={manage}
      saving={saving}
      onSaveEligibility={async (payload) => {
        setSaving('wel_profile')
        try {
          await patchWorkforceWorkEligibility(employeeId, payload)
          await reload()
          onChanged?.()
        } finally {
          setSaving(null)
        }
      }}
      onSavePayment={async (requirementId, payload) => {
        setSaving(`wel_pay_${requirementId}`)
        try {
          await patchWorkforceWorkEligibilityPaymentRequirement(employeeId, requirementId, payload)
          await reload()
          onChanged?.()
        } finally {
          setSaving(null)
        }
      }}
    />
  )
}
