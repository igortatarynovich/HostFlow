import { api } from '../../../api/client'
import type { WorkspaceCapabilityRenderContext } from '../../workspace-capability/renderContext'

export const DOCUMENTS_PUBLIC_CONTRACT_ID = 'documents.public_contract.v1'
export const DOCUMENTS_HUB_ADAPTER_ID = 'documents.hub_adapter_v1'
export const E3_LINKED_ENTITY_TYPE = 'workforce_employee'
export const E3_RELATION_TYPE = 'reused_for_hr'
export const E4_LINKED_ENTITY_TYPE = 'candidate'
export const E4_RELATION_TYPE = 'primary'

const RESOLVE_BY_RESOURCE: Record<string, { linkedEntityType: string; relationType: string }> = {
  [E3_LINKED_ENTITY_TYPE]: {
    linkedEntityType: E3_LINKED_ENTITY_TYPE,
    relationType: E3_RELATION_TYPE,
  },
  [E4_LINKED_ENTITY_TYPE]: {
    linkedEntityType: E4_LINKED_ENTITY_TYPE,
    relationType: E4_RELATION_TYPE,
  },
}

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
  expiry_state?: string | null
  days_left?: number | null
  link: DocumentLinkView
}

export type OutstandingAskView = {
  doc_type: string
  state: string
}

export type DocumentsResolveResult = {
  available: boolean
  contractId: string
  adapterId: string
  items: DocumentHubView[]
  outstandingAsks: OutstandingAskView[]
}

/**
 * Documents owner facade. Transport stays here — hosts must not call
 * `documents.candidate_id` lists, a leftover FK, or local Candidate/HR documents panels
 * for the D2 `documents` surface. Outstanding ask is Hub `outstanding_asks`
 * (required type + entity via Document Link) — not Candidate stage / HR JSON.
 */
export function documentsResolveTarget(
  ctx: WorkspaceCapabilityRenderContext,
): { linkedEntityType: string; relationType: string; entityId: string } | null {
  const resourceType = String(ctx.entity?.resourceType || '').trim()
  const entityId = String(ctx.entity?.resourceId || '').trim()
  const spec = RESOLVE_BY_RESOURCE[resourceType]
  if (!spec || !entityId) return null
  return { ...spec, entityId }
}

export function documentsEntityKey(ctx: WorkspaceCapabilityRenderContext): string {
  return documentsResolveTarget(ctx)?.entityId || ''
}

export async function listLinkedDocuments(
  ctx: WorkspaceCapabilityRenderContext,
): Promise<DocumentsResolveResult> {
  const target = documentsResolveTarget(ctx)
  if (!target) {
    return {
      available: false,
      contractId: DOCUMENTS_PUBLIC_CONTRACT_ID,
      adapterId: DOCUMENTS_HUB_ADAPTER_ID,
      items: [],
      outstandingAsks: [],
    }
  }
  const { data } = await api.get<{
    contract_id?: string
    adapter_id?: string
    items?: DocumentHubView[]
    outstanding_asks?: OutstandingAskView[]
  }>('/platform/documents/resolve', {
    params: {
      linked_entity_type: target.linkedEntityType,
      linked_entity_id: target.entityId,
      relation_type: target.relationType,
    },
  })
  return {
    available: true,
    contractId: String(data?.contract_id || DOCUMENTS_PUBLIC_CONTRACT_ID),
    adapterId: String(data?.adapter_id || DOCUMENTS_HUB_ADAPTER_ID),
    items: Array.isArray(data?.items) ? data.items : [],
    outstandingAsks: Array.isArray(data?.outstanding_asks) ? data.outstanding_asks : [],
  }
}
