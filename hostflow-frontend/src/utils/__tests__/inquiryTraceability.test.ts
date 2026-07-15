import { describe, expect, it } from 'vitest'
import type { Lead } from '../../api/types'
import {
  clientOriginInquiryPath,
  clientOriginQuestionnaireFormPath,
  inquiryRequiresReview,
  inquiryReviewMessage,
} from '../inquiryTraceability'

describe('inquiryTraceability', () => {
  it('detects review-required inquiries', () => {
    const lead = { normalized: { intake_review_required: true } } as Lead
    expect(inquiryRequiresReview(lead)).toBe(true)
    expect(inquiryReviewMessage(lead)).toContain('однозначно')
  })

  it('builds client origin paths from company extra', () => {
    const extra = {
      source_lead_id: 'lead-1',
      source_channel_id: 'channel-1',
      source_form_id: 'form-1',
    }
    expect(clientOriginInquiryPath(extra)).toContain('/channel-1/inquiries/lead-1')
    expect(clientOriginQuestionnaireFormPath(extra)).toContain('form-1')
  })
})
