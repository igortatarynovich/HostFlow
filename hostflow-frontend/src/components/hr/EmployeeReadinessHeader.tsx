import { useEffect, useMemo, useState } from 'react'
import { getSummary } from '../../api/documents/summary'
import type { DocumentPackProjection, ReminderWorkQueueItem } from '../../api/types'
import type { HrReviewPanel, WorkforceEligibilityRuntime } from '../../api/workforce'
import {
  buildEmployeeReadinessSummary,
  type EmployeeReadinessSummary,
  type ReadinessPrimaryCta,
  type ReadinessStatus,
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

/**
 * PMI-UI decision ownership: status/CTA prefer backend verdict contracts
 * (`decision_readiness`, eligibility journey next action). Pack strip may still
 * use the legacy presentation merge — do not invent a second domain decision.
 */
function applyBackendVerdict(
  legacy: EmployeeReadinessSummary,
  hrReview?: HrReviewPanel | null,
): EmployeeReadinessSummary {
  const readiness = hrReview?.decision_readiness
  if (!readiness) return legacy

  let status: ReadinessStatus = legacy.status
  let statusLabel = legacy.statusLabel
  if (readiness.can_approve) {
    status = 'ready'
    statusLabel = 'Ready'
  } else if (readiness.approve_blocked_reason) {
    status = 'not_ready'
    statusLabel = String(readiness.approve_blocked_reason).replace(/_/g, ' ')
  }

  const recommended =
    hrReview?.work_eligibility_summary?.recommended_next_action || null

  let primaryCta = legacy.primaryCta
  if (recommended && !readiness.can_approve) {
    primaryCta = {
      kind: 'admin',
      label: recommended,
      scrollTarget: legacy.primaryCta?.scrollTarget || '#employee-readiness-hero',
    }
  }

  return {
    ...legacy,
    status,
    statusLabel,
    primaryCta,
    verificationProgress: {
      verified: readiness.checklist_done,
      total: readiness.checklist_total,
    },
    readyNextStep: readiness.can_approve
      ? legacy.readyNextStep
      : recommended || legacy.readyNextStep,
  }
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

  const summary = useMemo(() => {
    const legacy = buildEmployeeReadinessSummary({
      packs,
      reminderWorkQueue: queue,
      eligibility,
      hrReview,
    })
    return applyBackendVerdict(legacy, hrReview)
  }, [packs, queue, eligibility, hrReview])

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
