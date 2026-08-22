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
        items: [{ id: 'doc-c', title: 'CV', doc_type: 'cv', status: 'uploaded', link: {} }],
      },
    })
    const subject = ctx({ entity: { resourceType: E4_LINKED_ENTITY_TYPE, resourceId: 'cand-1' } })
    expect(documentsEntityKey(subject)).toBe('cand-1')
    const result = await listLinkedDocuments(subject)
    expect(result.available).toBe(true)
    expect(result.items).toHaveLength(1)
    expect(get).toHaveBeenCalledWith('/platform/documents/resolve', {
      params: {
        linked_entity_type: E4_LINKED_ENTITY_TYPE,
        linked_entity_id: 'cand-1',
        relation_type: E4_RELATION_TYPE,
      },
    })
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
    })
    expect(get).not.toHaveBeenCalled()
  })
})
