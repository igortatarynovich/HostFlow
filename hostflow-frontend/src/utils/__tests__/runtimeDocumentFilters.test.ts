import { describe, expect, it } from 'vitest'
import {
  documentMatchesRuntimeFilter,
  isRuntimeDocumentFilter,
  resolveRuntimeDocumentFilter,
  runtimeMatchesFilter,
} from '../runtimeDocumentFilters'

describe('runtimeDocumentFilters', () => {
  it('matches expired by expiry_status', () => {
    expect(runtimeMatchesFilter({ expiry_status: 'expired' }, 'expired')).toBe(true)
    expect(runtimeMatchesFilter({ expiry_status: 'valid' }, 'expired')).toBe(false)
  })

  it('matches expiring_soon by expiry_status', () => {
    expect(runtimeMatchesFilter({ expiry_status: 'expiring_soon' }, 'expiring_soon')).toBe(true)
  })

  it('matches missing by workflow_status', () => {
    expect(runtimeMatchesFilter({ workflow_status: 'missing' }, 'missing')).toBe(true)
  })

  it('matches pending_review by runtime_signal', () => {
    expect(runtimeMatchesFilter({ runtime_signal: 'pending_verification' }, 'pending_review')).toBe(true)
    expect(runtimeMatchesFilter({ workflow_status: 'uploaded' }, 'pending_review')).toBe(false)
  })

  it('matches rejected by workflow_status', () => {
    expect(runtimeMatchesFilter({ workflow_status: 'rejected' }, 'rejected')).toBe(true)
  })

  it('matches satisfied by satisfies_requirement', () => {
    expect(runtimeMatchesFilter({ satisfies_requirement: true }, 'satisfied')).toBe(true)
    expect(runtimeMatchesFilter({ satisfies_requirement: false }, 'satisfied')).toBe(false)
  })

  it('returns false when runtime is absent', () => {
    expect(runtimeMatchesFilter(null, 'missing')).toBe(false)
  })

  it('documentMatchesRuntimeFilter reads document_runtime', () => {
    expect(
      documentMatchesRuntimeFilter(
        { document_runtime: { workflow_status: 'rejected' } },
        'rejected',
      ),
    ).toBe(true)
  })

  it('validates and resolves filter vocabulary', () => {
    expect(isRuntimeDocumentFilter('expired')).toBe(true)
    expect(isRuntimeDocumentFilter('approved')).toBe(false)
    expect(resolveRuntimeDocumentFilter('ready')).toBe('satisfied')
    expect(resolveRuntimeDocumentFilter('in_progress')).toBe('pending_review')
  })
})
