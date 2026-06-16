import { useEffect, useMemo, useState } from 'react'
import { getSummary } from '../../api/documents/summary'
import type { DocumentPackProjection, ReminderWorkQueueItem } from '../../api/types'
import type { HrReviewPanel, WorkforceEligibilityRuntime } from '../../api/workforce'
import {
  buildEmployeeReadinessSummary,
  type EmployeeReadinessSummary,
  type ReadinessPrimaryCta,
} from '../../utils/buildEmployeeReadinessSummary'
import { EmployeePackProgressStrip } from './EmployeePackProgressStrip'
import { EmployeeReadinessHero } from './EmployeeReadinessHero'

type Props = {
  candidateId?: string | null
  ownerContext?: Record<string, unknown> | null
  eligibility?: WorkforceEligibilityRuntime | null
  hrReview?: HrReviewPanel | null
  refreshToken?: number
  followUpMessage?: string | null
  onSummaryChange?: (summary: EmployeeReadinessSummary) => void
  onPrimaryAction?: (cta: ReadinessPrimaryCta) => void
}

export function EmployeeReadinessHeader({
  candidateId,
  ownerContext,
  eligibility,
  hrReview,
  refreshToken = 0,
  followUpMessage = null,
  onSummaryChange,
  onPrimaryAction,
}: Props) {
  const [loading, setLoading] = useState(Boolean(candidateId))
  const [packs, setPacks] = useState<DocumentPackProjection[]>([])
  const [queue, setQueue] = useState<ReminderWorkQueueItem[]>([])

  useEffect(() => {
    if (!candidateId) {
      setLoading(false)
      setPacks([])
      setQueue([])
      return
    }
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const response = await getSummary(candidateId, {
          context: ownerContext || undefined,
          fillMissing: false,
        })
        if (!cancelled) {
          setPacks(response.summary.packs || [])
          setQueue(response.summary.reminder_work_queue || [])
        }
      } catch {
        if (!cancelled) {
          setPacks([])
          setQueue([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [candidateId, ownerContext, refreshToken])

  const summary = useMemo(
    () =>
      buildEmployeeReadinessSummary({
        packs,
        reminderWorkQueue: queue,
        eligibility,
        hrReview,
      }),
    [packs, queue, eligibility, hrReview],
  )

  useEffect(() => {
    onSummaryChange?.(summary)
  }, [summary, onSummaryChange])

  return (
    <div id="employee-readiness-hero" className="space-y-3">
      <EmployeeReadinessHero
        summary={summary}
        loading={loading}
        followUpMessage={followUpMessage}
        onPrimaryAction={onPrimaryAction}
      />
      <EmployeePackProgressStrip items={summary.packStrip} loading={loading} />
    </div>
  )
}
