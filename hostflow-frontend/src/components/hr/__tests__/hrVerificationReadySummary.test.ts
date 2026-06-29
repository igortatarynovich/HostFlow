// @vitest-environment node
import { describe, expect, it } from 'vitest'
import type { HrReviewPanel } from '../../../api/workforce'
import { isVerificationPlanReady, verificationReadyGroups } from '../hrVerificationReadySummary'

function panel(partial: Partial<HrReviewPanel>): HrReviewPanel {
  return {
    status: 'hr_review_in_progress',
    checklist: [],
    blockers: [],
    documents_for_approval: [],
    can_approve: false,
    failed_required_items: [],
    ...partial,
  } as HrReviewPanel
}

describe('hrVerificationReadySummary', () => {
  it('isVerificationPlanReady follows verification_plan.can_approve', () => {
    expect(isVerificationPlanReady(panel({ verification_plan: { can_approve: true } }))).toBe(true)
    expect(isVerificationPlanReady(panel({ verification_plan: { can_approve: false } }))).toBe(false)
  })

  it('verificationReadyGroups splits confirmed, waived, and hr_requested', () => {
    const groups = verificationReadyGroups(
      panel({
        verification_plan: {
          can_approve: false,
          documents: [
            {
              document_key: 'passport',
              label: 'Passport',
              requirement_tier: 'required',
              verification_status: 'verified',
              verified: true,
            },
            {
              document_key: 'medical',
              label: 'Medical',
              requirement_tier: 'required',
              reviewed_fields: { _requirement_waiver: { reason: 'Client exception' } },
            },
            {
              document_key: 'ref_letter',
              label: 'Reference letter',
              requirement_tier: 'hr_requested',
              verification_status: 'pending',
            },
          ],
        },
      }),
    )
    expect(groups.confirmed.map((r) => r.key)).toEqual(['passport'])
    expect(groups.waived[0]?.reason).toBe('Client exception')
    expect(groups.hrRequested[0]?.reason).toBe('pending')
  })
})
