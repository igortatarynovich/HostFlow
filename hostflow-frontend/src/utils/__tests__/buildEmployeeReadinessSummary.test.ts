// @vitest-environment node
import { describe, expect, it } from 'vitest'
import type { DocumentPackProjection, ReminderWorkQueueItem } from '../api/types'
import type { HrReviewPanel } from '../api/workforce'
import {
  buildEmployeeReadinessSummary,
  buildReadinessFollowUpMessage,
  buildReadinessPrimaryCta,
} from '../buildEmployeeReadinessSummary'

function pack(overrides: Partial<DocumentPackProjection> & Pick<DocumentPackProjection, 'code'>): DocumentPackProjection {
  return {
    label: overrides.label || overrides.code,
    status: 'valid',
    skeleton: false,
    applies: true,
    ref_pack_codes: [],
    required: [],
    present: [],
    missing: [],
    expired: [],
    expiring_soon: [],
    missing_expiry: [],
    gaps: [],
    blockers: [],
    warnings: [],
    expiry: {
      all_documents_valid: true,
      has_expiring_documents: false,
      has_expired_documents: false,
      has_missing_expiry: false,
    },
    ...overrides,
  }
}

function hrReviewWithPassport(pending: boolean): HrReviewPanel {
  return {
    review_id: 'r1',
    status: 'in_review',
    checklist: [],
    blockers: [],
    failed_required_items: [],
    can_approve: false,
    documents_for_approval: [
      {
        document_key: 'Passport / ID',
        label: 'Passport / ID',
        status: pending ? 'pending' : 'verified',
        verified: !pending,
        document_id: 'doc-passport',
        document_type: 'passport',
        required: true,
      },
      {
        document_key: 'Residence Card',
        label: 'Residence Card',
        status: 'missing',
        verified: false,
        required: true,
      },
    ],
  }
}

describe('buildEmployeeReadinessSummary', () => {
  it('prefers verify passport over pack id_card missing', () => {
    const summary = buildEmployeeReadinessSummary({
      packs: [
        pack({
          code: 'legal_stay_pack',
          label: 'Legal Stay Pack',
          status: 'gaps',
          missing: ['id_card', 'residence_card', 'work_permit'],
        }),
      ],
      reminderWorkQueue: [],
      eligibility: null,
      hrReview: hrReviewWithPassport(true),
    })

    expect(summary.primary?.tier).toBe('verify_document')
    expect(summary.primary?.actionTitle).toBe('Verify Passport / ID')
  })

  it('after passport verified shows next obtain action with remaining count', () => {
    const summary = buildEmployeeReadinessSummary({
      packs: [
        pack({
          code: 'legal_stay_pack',
          label: 'Legal Stay Pack',
          status: 'gaps',
          missing: ['id_card', 'residence_card', 'work_permit'],
        }),
      ],
      reminderWorkQueue: [],
      eligibility: null,
      hrReview: hrReviewWithPassport(false),
    })

    expect(summary.primary?.actionTitle).toMatch(/Residence Card|Work Permit/i)
    expect(summary.remainingBlockingCount).toBeGreaterThanOrEqual(2)
    const followUp = buildReadinessFollowUpMessage(summary, 'Passport / ID')
    expect(followUp).toMatch(/Passport \/ ID confirmed/i)
    expect(followUp).toMatch(/Next:/i)
  })

  it('builds verify CTA for uploaded passport', () => {
    const review = hrReviewWithPassport(true)
    const summary = buildEmployeeReadinessSummary({
      packs: [],
      reminderWorkQueue: [],
      eligibility: null,
      hrReview: review,
    })
    expect(summary.primaryCta?.kind).toBe('verify')
    expect(summary.primaryCta?.label).toBe('Verify Passport / ID')
    expect(summary.primaryCta?.focusDocumentKey).toBe('Passport / ID')
  })

  it('builds obtain CTA for missing work permit', () => {
    const cta = buildReadinessPrimaryCta(
      {
        tier: 'missing_required',
        tierOrder: 40,
        actionTitle: 'Obtain Work Permit',
        reason: 'Legal Stay Pack incomplete',
        missingItems: ['Work Permit'],
        responsible: 'HR',
        blocksEmployment: true,
        blockLabel: 'Blocks employment transition',
        dueLabel: '—',
        scrollAnchor: '#dossier-documents',
        severity: 'high',
        documentCode: 'work_permit',
      },
      hrReviewWithPassport(false),
      null,
    )
    expect(cta?.kind).toBe('obtain')
    expect(cta?.scrollTarget).toBe('#hr-employee-linked-documents')
  })

  it('prefers expired work permit over missing expiry admin item', () => {
    const summary = buildEmployeeReadinessSummary({
      packs: [
        pack({
          code: 'legal_stay_pack',
          label: 'Legal Stay Pack',
          status: 'gaps',
          missing: ['work_permit'],
          expired: ['work_permit'],
          blockers: ['work_permit'],
        }),
      ],
      reminderWorkQueue: [
        {
          task_key: 'document:passport:missing_expiry:employee:1',
          title: 'Passport expiry date required',
          severity: 'low',
          owner_type: 'employee',
          owner_id: '1',
          recipient_role: 'hr',
          due_date: '2026-05-29',
          source_pack: 'legal_stay_pack',
          action: 'capture_expiry_date',
          document_code: 'passport',
          reason: 'missing_expiry',
        } satisfies ReminderWorkQueueItem,
      ],
      eligibility: null,
      hrReview: null,
    })

    expect(summary.primary?.tier).toBe('critical_blocker')
    expect(summary.primary?.actionTitle).toMatch(/Work Permit/i)
  })
})
