import { useLayoutEffect, useMemo } from 'react'
import { Navigate, useSearchParams } from 'react-router-dom'
import { inboxContextSearchParams, readInboxListQuery, type InboxListQuery } from '../utils/inboxUrlQuery'
import { stashPendingGmailOAuthCode } from '../utils/oauthRedirectBridge'

/**
 * OAuth redirect URI often points at `/app/email` — stash `?code=` then continue to unified Inbox (email scope).
 */
export default function CommunicationsEmailInboxPage() {
  const [searchParams] = useSearchParams()

  useLayoutEffect(() => {
    const code = searchParams.get('code')?.trim()
    if (code) stashPendingGmailOAuthCode(code)
  }, [searchParams])

  const dest = useMemo(() => {
    const p = new URLSearchParams(searchParams)
    p.delete('code')
    p.delete('state')
    p.delete('scope')
    const merged = readInboxListQuery(p)
    const next: InboxListQuery = {
      ...merged,
      channel: 'email',
    }
    const tid = p.get('threadId')?.trim()
    const qs = inboxContextSearchParams(next).toString()
    if (tid) return `/app/inbox/threads/${encodeURIComponent(tid)}${qs ? `?${qs}` : ''}`
    return `/app/inbox${qs ? `?${qs}` : ''}`
  }, [searchParams])

  return <Navigate to={dest} replace />
}
