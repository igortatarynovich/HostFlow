import { describe, expect, it } from 'vitest'
import { communicationPipelineReasonMessage } from '../communicationPipelineReason'

describe('communicationPipelineReasonMessage', () => {
  const t = (key: string, options?: { defaultValue?: string; values?: Record<string, string | number> }) => {
    if (key === 'app.communications_api.pipeline.missing_result_link') {
      return 'Link this thread first'
    }
    if (key === 'app.communications.email.dispatch_failed_reason') {
      return `Send blocked: ${options?.values?.reason || ''}`
    }
    if (key === 'app.communications.email.dispatch_failed') {
      return 'dispatch failed'
    }
    return options?.defaultValue || ''
  }

  it('maps known pipeline codes', () => {
    expect(communicationPipelineReasonMessage('missing_result_link', t)).toBe('Link this thread first')
  })

  it('falls back with reason code', () => {
    expect(communicationPipelineReasonMessage('weird_code', t)).toBe('Send blocked: weird_code')
  })
})
