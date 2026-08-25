import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { WorkspaceCapabilityRenderContext } from '../../../workspace-capability/renderContext'
import {
  DOCUMENTS_HUB_ADAPTER_ID,
  DOCUMENTS_PUBLIC_CONTRACT_ID,
  E3_LINKED_ENTITY_TYPE,
  E3_RELATION_TYPE,
  E4_LINKED_ENTITY_TYPE,
  E4_RELATION_TYPE,
  documentsEntityKey,
  listLinkedDocuments,
  persistCanonicalDocumentType,
} from '../documentsOwner'

const get = vi.fn()

vi.mock('../../../../api/client', () => ({
  api: {
    get: (...args: unknown[]) => get(...args),
  },
}))

function ctx(
  patch: Partial<WorkspaceCapabilityRenderContext> = {},
): WorkspaceCapabilityRenderContext {
  return {
    patching: false,
    onClose: () => undefined,
    onRefresh: () => undefined,
    ...patch,
  }
}

describe('documentsOwner', () => {
  beforeEach(() => {
    get.mockReset()
  })

  it('resolves Candidate via Document Link, not candidate_id list', async () => {
    get.mockResolvedValue({
      data: {
        contract_id: DOCUMENTS_PUBLIC_CONTRACT_ID,
        adapter_id: DOCUMENTS_HUB_ADAPTER_ID,
        items: [{ id: 'doc-c', title: 'Passport', doc_type: 'passport', status: 'uploaded', link: {} }],
      },
    })
    const subject = ctx({ entity: { resourceType: E4_LINKED_ENTITY_TYPE, resourceId: 'cand-1' } })
    expect(documentsEntityKey(subject)).toBe('cand-1')
    const result = await listLinkedDocuments(subject)
    expect(result.available).toBe(true)
    expect(result.items).toHaveLength(1)
    expect(result.outstandingAsks).toEqual([])
    expect(result.applicability).toEqual([])
    expect(get).toHaveBeenCalledWith('/platform/documents/resolve', {
      params: {
        linked_entity_type: E4_LINKED_ENTITY_TYPE,
        linked_entity_id: 'cand-1',
        relation_type: E4_RELATION_TYPE,
      },
    })
  })

  it('projects Hub outstanding asks on Candidate resolve, not a request table', async () => {
    get.mockResolvedValue({
      data: {
        contract_id: DOCUMENTS_PUBLIC_CONTRACT_ID,
        adapter_id: DOCUMENTS_HUB_ADAPTER_ID,
        items: [],
        outstanding_asks: [{ doc_type: 'passport', state: 'missing' }],
        canonical_types: ['passport', 'driver_license'],
        applicability: [{ doc_type: 'passport', applicability: 'required' }],
      },
    })
    const subject = ctx({ entity: { resourceType: E4_LINKED_ENTITY_TYPE, resourceId: 'cand-1' } })
    const result = await listLinkedDocuments(subject)
    expect(result.available).toBe(true)
    expect(result.outstandingAsks).toEqual([{ doc_type: 'passport', state: 'missing' }])
    expect(result.canonicalTypes).toEqual(['passport', 'driver_license'])
    expect(result.applicability).toEqual([{ doc_type: 'passport', applicability: 'required' }])
  })

  it('persists alias codes as canonical registry identity', () => {
    expect(persistCanonicalDocumentType('code95')).toBe('driver_qualification_card')
    expect(persistCanonicalDocumentType('tacho_card')).toBe('tachograph_card')
    expect(persistCanonicalDocumentType('residence_permit')).toBe('residence_card')
    expect(persistCanonicalDocumentType('passport')).toBe('passport')
  })

  it('migrates stored alias identity on Candidate resolve', async () => {
    get.mockResolvedValue({
      data: {
        contract_id: DOCUMENTS_PUBLIC_CONTRACT_ID,
        adapter_id: DOCUMENTS_HUB_ADAPTER_ID,
        items: [{ id: 'doc-c', title: 'Code 95', doc_type: 'code95', status: 'uploaded', link: {} }],
        outstanding_asks: [{ doc_type: 'tacho_card', state: 'missing' }],
        canonical_types: ['driver_qualification_card', 'tachograph_card'],
      },
    })
    const result = await listLinkedDocuments(
      ctx({ entity: { resourceType: E4_LINKED_ENTITY_TYPE, resourceId: 'cand-1' } }),
    )
    expect(result.items[0].doc_type).toBe('driver_qualification_card')
    expect(result.outstandingAsks).toEqual([{ doc_type: 'tachograph_card', state: 'missing' }])
    expect(result.applicability).toEqual([])
  })

  it('resolves HR employee via public contract entity-link, not workforce documents', async () => {
    get.mockResolvedValue({
      data: {
        contract_id: DOCUMENTS_PUBLIC_CONTRACT_ID,
        adapter_id: DOCUMENTS_HUB_ADAPTER_ID,
        items: [{ id: 'doc-1', title: 'Passport', doc_type: 'passport', status: 'verified', link: {} }],
      },
    })
    const subject = ctx({
      entity: { resourceType: E3_LINKED_ENTITY_TYPE, resourceId: 'emp-9' },
    })
    expect(documentsEntityKey(subject)).toBe('emp-9')
    const result = await listLinkedDocuments(subject)
    expect(result.available).toBe(true)
    expect(result.items).toHaveLength(1)
    expect(get).toHaveBeenCalledWith('/platform/documents/resolve', {
      params: {
        linked_entity_type: E3_LINKED_ENTITY_TYPE,
        linked_entity_id: 'emp-9',
        relation_type: E3_RELATION_TYPE,
      },
    })
  })

  it('ignores unbound consumers', async () => {
    const subject = ctx({ entity: { resourceType: 'client', resourceId: 'cl-1' } })
    expect(documentsEntityKey(subject)).toBe('')
    await expect(listLinkedDocuments(subject)).resolves.toEqual({
      available: false,
      contractId: DOCUMENTS_PUBLIC_CONTRACT_ID,
      adapterId: DOCUMENTS_HUB_ADAPTER_ID,
      items: [],
      outstandingAsks: [],
      canonicalTypes: [],
      applicability: [],
    })
    expect(get).not.toHaveBeenCalled()
  })

  it('canonicalizes alias applicability codes from R5 merge', async () => {
    get.mockResolvedValue({
      data: {
        contract_id: DOCUMENTS_PUBLIC_CONTRACT_ID,
        adapter_id: DOCUMENTS_HUB_ADAPTER_ID,
        items: [],
        applicability: [{ doc_type: 'code95', applicability: 'required' }],
      },
    })
    const result = await listLinkedDocuments(
      ctx({ entity: { resourceType: E4_LINKED_ENTITY_TYPE, resourceId: 'cand-1' } }),
    )
    expect(result.applicability).toEqual([
      { doc_type: 'driver_qualification_card', applicability: 'required' },
    ])
  })
})
