import { describe, expect, it } from 'vitest'
import { formatTransferList, groupBlockingReasonsByLayer } from '../transferReadinessDisplay'
import type { TransferBlockingReason } from '../../../api/candidates'

/** Mirrors TransferReadinessReport blocking-reason section rendering contract. */
function renderGroupedBlockingReasonLabels(
  reasons: TransferBlockingReason[] | undefined,
) {
  return groupBlockingReasonsByLayer(reasons)
}

const regressionReasons: TransferBlockingReason[] = [
  {
    code: 'missing_required_document',
    message: "Required document 'work_permit' is missing.",
    source_layer: 'document_packs',
  },
  {
    code: 'pending_document_verification',
    message: "Required document 'driver_license' is not verified yet.",
    source_layer: 'document_packs',
  },
  {
    code: 'missing_data_field',
    message: 'Missing required data: Phone',
    source_layer: 'recruitment_package',
  },
  {
    code: 'unconfirmed_block',
    message: 'Recruiter must confirm reviewed block: Passport / ID',
    source_layer: 'recruiter_confirmation',
    block_key: 'Passport / ID',
  },
  {
    code: 'no_destination',
    message: 'No handoff destination enabled on tenant link',
    source_layer: 'tenant_link',
  },
]

describe('groupBlockingReasonsByLayer', () => {
  it('groups by source_layer for display only', () => {
    const grouped = groupBlockingReasonsByLayer([
      { code: 'a', message: 'Missing passport', source_layer: 'document_packs' },
      { code: 'b', message: 'Confirm block', source_layer: 'recruiter_confirmation' },
      { code: 'c', message: 'Missing permit', source_layer: 'document_packs' },
    ])
    expect(grouped).toHaveLength(2)
    expect(grouped[0].layer).toBe('document_packs')
    expect(grouped[0].items).toHaveLength(2)
    expect(grouped[1].layer).toBe('recruiter_confirmation')
  })

  it('covers regression blocking_reason layers without local rule recomputation', () => {
    const grouped = renderGroupedBlockingReasonLabels(regressionReasons)
    expect(grouped.map((g) => g.layer)).toEqual([
      'document_packs',
      'recruiter_confirmation',
      'recruitment_package',
      'tenant_link',
    ])
    expect(grouped[0].items.map((r) => r.code)).toEqual([
      'missing_required_document',
      'pending_document_verification',
    ])
    expect(grouped[2].items[0].message).toBe('Missing required data: Phone')
    expect(grouped[1].items[0].block_key).toBe('Passport / ID')
  })

  it('preserves API message text for recruiter-facing display', () => {
    const grouped = renderGroupedBlockingReasonLabels(regressionReasons)
    const messages = grouped.flatMap((g) => g.items.map((r) => r.message))
    expect(messages).toContain("Required document 'work_permit' is missing.")
    expect(messages).toContain('Recruiter must confirm reviewed block: Passport / ID')
  })
})

describe('formatTransferList', () => {
  it('formats document and override lists for report sections', () => {
    expect(formatTransferList(['work_permit', 'driver_license'])).toBe('work_permit, driver_license')
    expect(formatTransferList([])).toBe('—')
    expect(formatTransferList(undefined)).toBe('—')
  })
})
