import { useMemo } from 'react'
import { Navigate, useSearchParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { inboxContextSearchParams, readInboxListQuery, type InboxListQuery } from '../utils/inboxUrlQuery'

/** Legacy `/app/messages` → unified Inbox (messages scope). Bookmarks and Topbar links keep working. */
export default function CommunicationsMessagesPage() {
  const [searchParams] = useSearchParams()
  const target = useMemo(() => {
    const p = new URLSearchParams(searchParams)
    const tid = p.get('threadId')?.trim()
    p.delete('threadId')
    const base = readInboxListQuery(p)
    const next: InboxListQuery = {
      ...base,
      channel: 'messages',
    }
    const qs = inboxContextSearchParams(next).toString()
    if (tid) {
      return `${CRM_APP_PATHS.inboxThreadsBase}/${encodeURIComponent(tid)}${qs ? `?${qs}` : ''}`
    }
    return `${CRM_APP_PATHS.inbox}${qs ? `?${qs}` : ''}`
  }, [searchParams])

  return <Navigate to={target} replace />
}
