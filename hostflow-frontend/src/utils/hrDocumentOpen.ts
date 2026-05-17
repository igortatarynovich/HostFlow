import { downloadDocumentFile, getDocumentFileUrl } from '../api/documents/file'
import { downloadWorkforceEmployeeDocumentFile } from '../api/workforce'

export type OpenHrDocumentOptions = {
  /** When set, uses workforce file API (no HR viewer-channel visibility filter). */
  employeeId?: string | null
}

async function openBlobInNewTab(blob: Blob, directLink?: string | null): Promise<void> {
  if (!blob || blob.size === 0) {
    if (directLink) {
      window.open(directLink, '_blank', 'noopener,noreferrer')
      return
    }
    throw new Error('Empty document file')
  }
  const objectUrl = URL.createObjectURL(blob)
  window.open(objectUrl, '_blank', 'noopener,noreferrer')
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)
}

/**
 * Open a dossier document in a new tab with Bearer auth.
 * Prefers workforce scoped download when `employeeId` is known; otherwise uses `/db/documents`
 * with the default recruitment viewer channel (HR channel hides recruitment/transport types).
 */
export async function openHrDocumentInNewTab(
  documentId: string,
  options?: OpenHrDocumentOptions,
): Promise<void> {
  const id = String(documentId || '').trim()
  if (!id) throw new Error('Missing document id')

  const employeeId = String(options?.employeeId || '').trim()
  if (employeeId) {
    const fileData = await downloadWorkforceEmployeeDocumentFile(employeeId, id)
    await openBlobInNewTab(fileData.blob)
    return
  }

  let directLink: string | null = null
  try {
    const res = await getDocumentFileUrl(id)
    if (res?.url) directLink = res.url
  } catch {
    /* fall through to blob download */
  }

  if (directLink && (directLink.startsWith('http://') || directLink.startsWith('https://'))) {
    window.open(directLink, '_blank', 'noopener,noreferrer')
    return
  }

  const fileData = await downloadDocumentFile(id)
  await openBlobInNewTab(fileData.blob, directLink)
}
