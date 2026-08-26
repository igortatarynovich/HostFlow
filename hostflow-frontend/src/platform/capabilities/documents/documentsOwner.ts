import { api } from '../../../api/client'
import { DOC_TYPE_LEGACY_ALIASES } from '../../../data/documentTypeAliases'
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

export type ApplicabilityView = {
  doc_type: string
  applicability: 'required' | 'optional' | 'blocked' | string
}

export type DocumentsResolveResult = {
  available: boolean
  contractId: string
  adapterId: string
  items: DocumentHubView[]
  outstandingAsks: OutstandingAskView[]
  canonicalTypes: string[]
  applicability: ApplicabilityView[]
}

/**
 * Documents owner facade. Transport stays here — hosts must not call
 * `documents.candidate_id` lists, a leftover FK, or local Candidate/HR documents panels
 * for the D2 `documents` surface. Outstanding ask is Hub `outstanding_asks`
 * (required type + entity via Document Link) — not Candidate stage / HR JSON.
 * E8-bind: display / select / persist canonical registry codes. R4 aliases
 * resolve only — they are not stored identity. E8-eval: required / optional /
 * blocked applicability from R5 merge. Overlay is an existing CL7 input.
 */
export function persistCanonicalDocumentType(raw: string): string {
  const key = String(raw || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')
  if (!key) return ''
  const mapped = DOC_TYPE_LEGACY_ALIASES[key]
  if (mapped) return mapped
  const canonical = new Set(Object.values(DOC_TYPE_LEGACY_ALIASES))
  return canonical.has(key) ? key : ''
}

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
      canonicalTypes: [],
      applicability: [],
    }
  }
  const { data } = await api.get<{
    contract_id?: string
    adapter_id?: string
    items?: DocumentHubView[]
    outstanding_asks?: OutstandingAskView[]
    canonical_types?: string[]
    applicability?: ApplicabilityView[]
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
    items: Array.isArray(data?.items)
      ? data.items.map((row) => ({
          ...row,
          doc_type: persistCanonicalDocumentType(row.doc_type),
        }))
      : [],
    outstandingAsks: Array.isArray(data?.outstanding_asks)
      ? data.outstanding_asks
          .map((ask) => ({
            ...ask,
            doc_type: persistCanonicalDocumentType(ask.doc_type),
          }))
          .filter((ask) => Boolean(ask.doc_type))
      : [],
    canonicalTypes: Array.isArray(data?.canonical_types) ? data.canonical_types : [],
    applicability: Array.isArray(data?.applicability)
      ? data.applicability
          .map((row) => ({
            ...row,
            doc_type: persistCanonicalDocumentType(row.doc_type),
          }))
          .filter((row) => Boolean(row.doc_type))
      : [],
  }
}
