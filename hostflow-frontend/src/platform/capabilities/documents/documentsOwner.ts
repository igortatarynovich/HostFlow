import { api } from '../../../api/client'
import type { WorkspaceCapabilityRenderContext } from '../../workspace-capability/renderContext'

export const DOCUMENTS_PUBLIC_CONTRACT_ID = 'documents.public_contract.v1'
export const DOCUMENTS_HUB_ADAPTER_ID = 'documents.hub_adapter_v1'
export const E3_LINKED_ENTITY_TYPE = 'workforce_employee'
export const E3_RELATION_TYPE = 'reused_for_hr'

export type DocumentLinkView = {
  id: string
  linked_entity_type: string
  linked_entity_id: string
  relation_type: string
}

export type DocumentHubView = {
  id: string
  title: string
  doc_type: string
  status: string
  expires_at?: string | null
  link: DocumentLinkView
}

export type DocumentsResolveResult = {
  available: boolean
  contractId: string
  adapterId: string
  items: DocumentHubView[]
}

/**
 * Documents owner facade. Transport stays here — hosts and HR pages must not
 * call `/workforce/employees/:id/documents` for the D2 `documents` surface.
 */
export function documentsEntityKey(ctx: WorkspaceCapabilityRenderContext): string {
  if (ctx.entity?.resourceType === E3_LINKED_ENTITY_TYPE) {
    return String(ctx.entity.resourceId || '').trim()
  }
  return ''
}

export async function listLinkedDocuments(
  ctx: WorkspaceCapabilityRenderContext,
): Promise<DocumentsResolveResult> {
  const entityId = documentsEntityKey(ctx)
  if (!entityId) {
    return {
      available: false,
      contractId: DOCUMENTS_PUBLIC_CONTRACT_ID,
      adapterId: DOCUMENTS_HUB_ADAPTER_ID,
      items: [],
    }
  }
  const { data } = await api.get<{
    contract_id?: string
    adapter_id?: string
    items?: DocumentHubView[]
  }>('/platform/documents/resolve', {
    params: {
      linked_entity_type: E3_LINKED_ENTITY_TYPE,
      linked_entity_id: entityId,
      relation_type: E3_RELATION_TYPE,
    },
  })
  return {
    available: true,
    contractId: String(data?.contract_id || DOCUMENTS_PUBLIC_CONTRACT_ID),
    adapterId: String(data?.adapter_id || DOCUMENTS_HUB_ADAPTER_ID),
    items: Array.isArray(data?.items) ? data.items : [],
  }
}
