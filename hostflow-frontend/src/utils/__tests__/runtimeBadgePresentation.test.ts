import { describe, expect, it } from 'vitest'
import {
  extractRuntimeItemsFromSummary,
  indexRuntimeItemsByType,
  isRuntimeExpiringSoon,
  runtimeBadgeForDocumentType,
  runtimeBadgeFromDocument,
  runtimeBadgeFromRuntime,
} from '../runtimeBadgePresentation'

describe('runtimeBadgePresentation', () => {
  it('maps approved + valid to approved badge', () => {
    const badge = runtimeBadgeFromRuntime({
      evaluation_version: 'document_runtime_v1',
      workflow_status: 'approved',
      expiry_status: 'valid',
      runtime_signal: null,
      satisfies_requirement: true,
    })
    expect(badge.badge).toBe('approved')
    expect(badge.showSatisfactionIndicator).toBe(true)
  })

  it('maps pending verification to pending badge', () => {
    const badge = runtimeBadgeFromRuntime({
      workflow_status: 'uploaded',
      expiry_status: 'valid',
      runtime_signal: 'pending_verification',
      satisfies_requirement: false,
    })
    expect(badge.badge).toBe('pending')
  })

  it('precedence: expired over approved workflow', () => {
    const badge = runtimeBadgeFromRuntime({
      workflow_status: 'approved',
      expiry_status: 'expired',
      runtime_signal: 'expired',
      satisfies_requirement: false,
    })
    expect(badge.badge).toBe('expired')
  })

  it('maps expiring_soon signal', () => {
    const badge = runtimeBadgeFromRuntime({
      workflow_status: 'approved',
      expiry_status: 'expiring_soon',
      runtime_signal: 'expiring_soon',
      satisfies_requirement: false,
    })
    expect(badge.badge).toBe('expiring_soon')
  })

  it('maps rejected workflow', () => {
    const badge = runtimeBadgeFromRuntime({
      workflow_status: 'rejected',
      expiry_status: 'valid',
      runtime_signal: 'rejected',
    })
    expect(badge.badge).toBe('rejected')
  })

  it('maps missing instance', () => {
    expect(runtimeBadgeFromRuntime(null).badge).toBe('missing')
    expect(
      runtimeBadgeFromRuntime({
        workflow_status: 'missing',
        runtime_signal: 'missing',
      }).badge,
    ).toBe('missing')
  })

  it('reads document_runtime from document payload', () => {
    const doc = {
      document_runtime: {
        workflow_status: 'approved',
        expiry_status: 'valid',
        satisfies_requirement: true,
      },
    }
    expect(runtimeBadgeFromDocument(doc).badge).toBe('approved')
  })

  it('isRuntimeExpiringSoon is a thin runtime adapter', () => {
    expect(
      isRuntimeExpiringSoon({
        document_runtime: { runtime_signal: 'expiring_soon', expiry_status: 'expiring_soon' },
      }),
    ).toBe(true)
    expect(
      isRuntimeExpiringSoon({
        document_runtime: { workflow_status: 'approved', expiry_status: 'valid' },
      }),
    ).toBe(false)
  })

  it('indexes runtime checklist items by type', () => {
    const index = indexRuntimeItemsByType([
      {
        document_type_code: 'passport',
        document_runtime: { workflow_status: 'approved', expiry_status: 'valid' },
      },
    ])
    expect(runtimeBadgeFromRuntime(index.get('passport')).badge).toBe('approved')
  })

  it('extracts runtime items from summary.checklist.runtimeItems', () => {
    const summary = {
      checklist: {
        runtimeItems: [
          {
            document_type_code: 'driver_license',
            document_runtime: { workflow_status: 'missing', runtime_signal: 'missing' },
          },
        ],
      },
    }
    expect(runtimeBadgeForDocumentType(summary, 'driver_license').badge).toBe('missing')
  })

  it('falls back to summary.document_runtime.items', () => {
    const summary = {
      document_runtime: {
        items: [
          {
            document_type_code: 'visa',
            document_runtime: { workflow_status: 'rejected', runtime_signal: 'rejected' },
          },
        ],
      },
    }
    expect(extractRuntimeItemsFromSummary(summary)).toHaveLength(1)
    expect(runtimeBadgeForDocumentType(summary, 'visa').badge).toBe('rejected')
  })
})
