import http from '../api/http'
import { resolveApiBase } from '../api/client'

/** Map backend ``open_url`` (absolute or /api/v1/...) to axios path under API base. */
export function resolveApiRelativePath(openUrl: string): string {
  const raw = openUrl.trim()
  if (/^https?:\/\//i.test(raw)) return raw
  const base = resolveApiBase().replace(/\/+$/, '')
  if (raw.startsWith(`${base}/`)) return raw.slice(base.length) || '/'
  if (raw.startsWith('/api/v1/')) return raw.slice('/api/v1'.length)
  return raw.startsWith('/') ? raw : `/${raw}`
}

async function openBlobInNewTab(blob: Blob): Promise<void> {
  if (!blob || blob.size === 0) throw new Error('Empty document file')
  const objectUrl = URL.createObjectURL(blob)
  window.open(objectUrl, '_blank', 'noopener,noreferrer')
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)
}

/** Open a document using backend-resolved ``open_url`` (Bearer via http client). */
export async function openDocumentFromBackendUrl(openUrl: string): Promise<void> {
  const path = resolveApiRelativePath(openUrl)
  if (/^https?:\/\//i.test(path)) {
    window.open(path, '_blank', 'noopener,noreferrer')
    return
  }
  const response = await http.get<Blob>(path, { responseType: 'blob' })
  await openBlobInNewTab(response.data)
}
