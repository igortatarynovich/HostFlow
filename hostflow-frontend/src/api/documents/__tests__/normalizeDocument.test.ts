import { describe, expect, it } from 'vitest'
import { normalizeDocument } from '../normalize'

describe('normalizeDocument', () => {
  it('keeps document_runtime so status chips do not fall back to missing', () => {
    const doc = normalizeDocument({
      id: 'd1',
      tenant_id: 't1',
      candidate_id: 'c1',
      doc_type: 'passport',
      status: 'approved',
      has_files: true,
      files: [{ name: 'Paszport.pdf', url: '/uploads/p.pdf' }],
      document_runtime: {
        evaluation_version: 'document_runtime_v1',
        workflow_status: 'approved',
        expiry_status: 'valid',
        runtime_signal: null,
        satisfies_requirement: true,
      },
    })
    expect(doc.has_files).toBe(true)
    expect(doc.document_runtime?.workflow_status).toBe('approved')
  })

  it('treats a non-empty files array as uploaded even if has_files is omitted', () => {
    const doc = normalizeDocument({
      id: 'd2',
      tenant_id: 't1',
      candidate_id: 'c1',
      doc_type: 'tacho_card',
      status: 'approved',
      files: [{ name: 'Tacho.pdf', url: '/uploads/t.pdf' }],
    })
    expect(doc.has_files).toBe(true)
    expect(doc.document_runtime).toBeNull()
  })
})
