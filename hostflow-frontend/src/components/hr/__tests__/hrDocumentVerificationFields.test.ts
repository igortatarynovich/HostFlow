// @vitest-environment node
import { describe, expect, it } from 'vitest'
import type { HrReviewDocumentRow } from '../../../api/workforce'
import {
  buildConfirmedReviewedPayload,
  canConfirmHrVerificationDocument,
  countVerifiedDocuments,
  findReviewDocumentForEmployeeDoc,
  firstPendingDocumentIndex,
  isDocumentVerified,
  requiredDocumentQueue,
  sequentialDocumentQueue,
} from '../hrDocumentVerificationFields'

function doc(partial: Partial<HrReviewDocumentRow> & { document_key: string }): HrReviewDocumentRow {
  return {
    label: partial.label ?? partial.document_key,
    status: partial.status ?? 'pending',
    verified: partial.verified ?? false,
    ...partial,
  }
}

describe('hrDocumentVerificationFields', () => {
  it('queues required slots even without upload; optional only when present', () => {
    const docs = [
      doc({ document_key: 'a', document_id: '1' }),
      doc({ document_key: 'b' }),
      doc({ document_key: 'c', required: false }),
      doc({ document_key: 'd', required: false, document_id: '3' }),
    ]
    expect(sequentialDocumentQueue(docs).map((d) => d.document_key)).toEqual(['a', 'b', 'd'])
  })

  it('counts verified documents in queue', () => {
    const docs = [
      doc({ document_key: 'a', document_id: '1', verification_status: 'verified', verified: true }),
      doc({ document_key: 'b', document_id: '2' }),
    ]
    expect(countVerifiedDocuments(docs)).toEqual({ verified: 1, total: 2 })
  })

  it('builds confirmed payload for verify API', () => {
    const payload = buildConfirmedReviewedPayload({
      citizenship: { value: 'UA', comment: '', confirmed: false },
    })
    expect(payload.citizenship).toEqual({ value: 'UA', comment: '', confirmed: true })
  })

  it('excludes optional docs without upload from required progress', () => {
    const docs = [
      doc({ document_key: 'a', document_id: '1', required: true }),
      doc({ document_key: 'b', required: false }),
      doc({ document_key: 'c', required: false, document_id: '3' }),
    ]
    expect(requiredDocumentQueue(docs).map((d) => d.document_key)).toEqual(['a', 'c'])
    expect(countVerifiedDocuments(docs)).toEqual({ verified: 0, total: 1 })
  })

  it('picks first pending index', () => {
    const docs = [
      doc({ document_key: 'a', document_id: '1', verification_status: 'verified', verified: true }),
      doc({ document_key: 'b', document_id: '2' }),
    ]
    expect(firstPendingDocumentIndex(docs)).toBe(1)
    expect(isDocumentVerified(docs[0]!)).toBe(true)
  })

  it('matches employee document row to review card by document_id', () => {
    const panel = {
      review_id: 'r1',
      status: 'in_review',
      checklist: [],
      blockers: [],
      failed_required_items: [],
      can_approve: false,
      documents_for_approval: [
        doc({ document_key: 'Passport / ID', document_id: 'doc-42', document_type: 'passport' }),
      ],
    }
    const match = findReviewDocumentForEmployeeDoc(panel, {
      id: 'doc-42',
      doc_type: 'passport',
      title: 'Passport',
    })
    expect(match?.document_key).toBe('Passport / ID')
  })

  it('sorts sequential queue by step_order then slot_order', () => {
    const docs = [
      doc({ document_key: 'Passport / ID', document_id: '1', step_order: 1, slot_order: 1 }),
      doc({
        document_key: 'Contacts & address',
        fields_to_review: [{ field_code: 'address', label: 'Address' }],
        step_order: 1,
        slot_order: 0,
        block_kind: 'data_only',
      }),
    ]
    expect(sequentialDocumentQueue(docs).map((d) => d.document_key)).toEqual([
      'Contacts & address',
      'Passport / ID',
    ])
  })

  it('allows confirm for data-only blocks without document_id', () => {
    const dataOnly = doc({
      document_key: 'Contacts & address',
      block_kind: 'data_only',
      file_required_for_confirm: false,
      fields_to_review: [{ field_code: 'address', label: 'Address' }],
      actions: { can_verify: true },
    })
    const edits = { address: { value: 'Warsaw', comment: '', confirmed: false } }
    expect(canConfirmHrVerificationDocument(dataOnly, true, edits)).toBe(true)
    expect(canConfirmHrVerificationDocument(dataOnly, true, {})).toBe(false)
  })
})
