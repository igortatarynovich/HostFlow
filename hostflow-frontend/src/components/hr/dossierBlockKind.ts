import type { HrReviewDocumentRow } from '../../api/workforce'

export const DATA_ONLY_BLOCK_KEYS = new Set(['Contacts & address'])
export const OPTIONAL_FILE_BLOCK_KEYS = new Set(['Work experience'])

export type DossierBlockKind = 'document' | 'data_only' | 'optional_file'

export function dossierBlockKind(doc: HrReviewDocumentRow): DossierBlockKind {
  const raw = String(doc.block_kind || '').trim()
  if (raw === 'data_only' || raw === 'optional_file' || raw === 'document') return raw
  if (DATA_ONLY_BLOCK_KEYS.has(doc.document_key)) return 'data_only'
  if (OPTIONAL_FILE_BLOCK_KEYS.has(doc.document_key)) return 'optional_file'
  return 'document'
}

export function dossierFileRequiredForConfirm(doc: HrReviewDocumentRow): boolean {
  if (doc.file_required_for_confirm === false) return false
  return dossierBlockKind(doc) === 'document'
}

export function dossierShowFileActions(doc: HrReviewDocumentRow): boolean {
  return dossierBlockKind(doc) !== 'data_only'
}

export function dossierDefaultUploadDocType(doc: HrReviewDocumentRow): string {
  if (dossierBlockKind(doc) === 'optional_file') return 'swiadectwo_pracy'
  return (doc.document_type || doc.document_key || '').trim()
}
