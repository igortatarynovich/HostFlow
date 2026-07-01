import { openDocumentFromBackendUrl } from './documentOpen'

export type OpenHrDocumentOptions = {
  /** Canonical file route from backend (``open_url`` / ``file_url``). */
  openUrl?: string | null
}

/** Open HR document using backend-provided open URL only (no client-side route guessing). */
export async function openHrDocumentInNewTab(options: OpenHrDocumentOptions): Promise<void> {
  const openUrl = String(options.openUrl || '').trim()
  if (!openUrl) throw new Error('Missing open_url from API')
  await openDocumentFromBackendUrl(openUrl)
}
