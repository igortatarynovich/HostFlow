import type { CommunicationThread } from '../api/communications'
import { isCommunicationThreadUnlinked } from './communicationThreadUnlinked'

export const FOLDER_TAG_PREFIX = 'folder:'

export type EmailSystemFolder =
  | 'inbox'
  | 'unread'
  | 'sent'
  | 'assigned'
  | 'unlinked'
  | 'archive'
  | 'trash'
  | 'all'

export type EmailFolderKey = EmailSystemFolder | `custom:${string}`

export function emailInboxTagsOf(th: CommunicationThread): string[] {
  return (Array.isArray(th.tags_json) ? th.tags_json : []).map((x) => String(x || '').trim()).filter(Boolean)
}

export function emailCustomFolderNameOf(th: CommunicationThread): string | null {
  const tag = emailInboxTagsOf(th).find((x) => x.toLowerCase().startsWith(FOLDER_TAG_PREFIX))
  if (!tag) return null
  const raw = tag.slice(FOLDER_TAG_PREFIX.length).trim()
  return raw || null
}

export function emailThreadInFolder(th: CommunicationThread, folder: EmailFolderKey): boolean {
  if (folder === 'all') return true
  if (folder === 'trash') return String(th.status || '').toLowerCase() === 'deleted'
  if (folder === 'archive') return Boolean(th.is_archived) && String(th.status || '').toLowerCase() !== 'deleted'
  if (folder === 'unread') return Number(th.unread_count || 0) > 0 && !th.is_archived
  if (folder === 'sent')
    return (Boolean(th.last_outbound_at) || String(th.direction_hint || '') === 'outbound') && !th.is_archived
  if (folder === 'assigned') return Boolean(String(th.assignee_id || '').trim()) && !th.is_archived
  if (folder === 'unlinked') {
    return (
      isCommunicationThreadUnlinked(th) &&
      !th.is_archived &&
      String(th.status || '').toLowerCase() !== 'deleted'
    )
  }
  if (folder === 'inbox')
    return !th.is_archived && String(th.status || '').toLowerCase() !== 'deleted' && !emailCustomFolderNameOf(th)
  if (folder.startsWith('custom:')) {
    const folderName = folder.slice('custom:'.length)
    return emailCustomFolderNameOf(th) === folderName && !th.is_archived
  }
  return false
}

export function emailThreadTitle(th: CommunicationThread): string {
  return String(th.subject || '').trim() || String(th.last_message_preview || '').trim() || th.id
}

const SYSTEM_FOLDERS: EmailSystemFolder[] = [
  'inbox',
  'unread',
  'archive',
  'sent',
  'assigned',
  'unlinked',
  'trash',
  'all',
]

export function parseEmailFolderKey(raw: string | null | undefined): EmailFolderKey {
  const s = String(raw || '').trim().toLowerCase()
  if (!s) return 'inbox'
  if (s.startsWith('custom:')) {
    const name = s.slice('custom:'.length).trim()
    return name ? (`custom:${name}` as const) : 'inbox'
  }
  if ((SYSTEM_FOLDERS as string[]).includes(s)) return s as EmailSystemFolder
  return 'inbox'
}
