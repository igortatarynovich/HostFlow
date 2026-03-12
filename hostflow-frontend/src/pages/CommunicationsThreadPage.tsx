import clsx from 'clsx'
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import {
  autoAssignCommunicationThread,
  createCommunicationMessage,
  dispatchCommunicationMessage,
  dispatchQueuedCommunicationMessages,
  getCommunicationThread,
  markCommunicationThreadRead,
  type CommunicationMessage,
  type CommunicationThread,
} from '../api/communications'
import { useI18n } from '../i18n'
import WorkspaceTopNav from '../components/communications/WorkspaceTopNav'

function formatDateTime(value?: string | null): string {
  if (!value) return '—'
  const ts = Date.parse(value)
  if (Number.isNaN(ts)) return String(value)
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(ts))
}

function errorTextFrom(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const msg = detail.map((x) => (typeof x?.msg === 'string' ? x.msg : null)).filter(Boolean).join('; ')
    if (msg) return msg
  }
  if (detail && typeof detail === 'object') {
    if (typeof detail.msg === 'string' && detail.msg.trim()) return detail.msg
    try { return JSON.stringify(detail) } catch {}
  }
  if (typeof err?.message === 'string' && err.message.trim()) return err.message
  return fallback
}

export default function CommunicationsThreadPage() {
  const { t } = useI18n()
  const { threadId = '' } = useParams()
  const [thread, setThread] = useState<CommunicationThread | null>(null)
  const [messages, setMessages] = useState<CommunicationMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [errorText, setErrorText] = useState<string | null>(null)
  const [busyAction, setBusyAction] = useState<'assign' | 'read' | null>(null)
  const [sending, setSending] = useState(false)
  const [dispatchingQueued, setDispatchingQueued] = useState(false)
  const [dispatchingMessageId, setDispatchingMessageId] = useState<string | null>(null)
  const [openActionMenu, setOpenActionMenu] = useState<null | 'workflow' | 'delivery'>(null)
  const workflowMenuRef = useRef<HTMLDivElement | null>(null)
  const deliveryMenuRef = useRef<HTMLDivElement | null>(null)
  const [draftText, setDraftText] = useState('')
  const [draftSubject, setDraftSubject] = useState('')
  const [recipientAddress, setRecipientAddress] = useState('')
  const [internalNote, setInternalNote] = useState(false)
  const [sendImmediately, setSendImmediately] = useState(true)
  const threadListPath = String(thread?.channel || '').toLowerCase() === 'email' ? '/app/email' : '/app/messages'

  const load = useCallback(async () => {
    if (!threadId) return
    setLoading(true)
    setErrorText(null)
    try {
      const data = await getCommunicationThread(threadId, { messagesLimit: 200 })
      setThread(data.thread)
      setMessages(Array.isArray(data.messages) ? data.messages : [])
      if (!draftSubject) setDraftSubject(data.thread.subject || '')
    } catch (err: any) {
      setErrorText(errorTextFrom(err, t('app.communications.errors.load', { defaultValue: 'Failed to load communications data' })))
    } finally {
      setLoading(false)
    }
  }, [draftSubject, t, threadId])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!openActionMenu) return
    const onPointerDown = (event: MouseEvent | TouchEvent) => {
      const target = event.target as Node | null
      const refs = [workflowMenuRef.current, deliveryMenuRef.current]
      if (refs.some((el) => el && target && el.contains(target))) return
      setOpenActionMenu(null)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpenActionMenu(null)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('touchstart', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('touchstart', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [openActionMenu])

  const sortedMessages = useMemo(
    () => [...messages].sort((a, b) => (Date.parse(a.created_at || '') || 0) - (Date.parse(b.created_at || '') || 0)),
    [messages]
  )

  const handleMarkRead = useCallback(async () => {
    if (!threadId) return
    setBusyAction('read')
    try {
      const updated = await markCommunicationThreadRead(threadId, { mark_thread: true })
      setThread(updated)
      setMessages((prev) =>
        prev.map((m) =>
          m.direction === 'inbound' && !m.read_at
            ? { ...m, read_at: new Date().toISOString(), delivery_status: m.delivery_status === 'delivered' ? 'read' : m.delivery_status }
            : m
        )
      )
    } catch (err: any) {
      setErrorText(errorTextFrom(err, t('app.communications.errors.load', { defaultValue: 'Failed to mark thread as read' })))
    } finally {
      setBusyAction(null)
    }
  }, [t, threadId])

  const handleAutoAssign = useCallback(async () => {
    if (!threadId) return
    setBusyAction('assign')
    try {
      const result = await autoAssignCommunicationThread(threadId)
      setThread(result.thread)
      if (!result.assigned) {
        setErrorText(
          t('app.communications.queue.auto_assign_failed', {
            values: { reason: result.reason || 'no_eligible_managers' },
            defaultValue: `Auto-assign failed: ${result.reason || 'no_eligible_managers'}`,
          })
        )
      } else {
        setErrorText(null)
      }
    } catch (err: any) {
      setErrorText(errorTextFrom(err, t('app.communications.errors.load', { defaultValue: 'Failed to auto-assign thread' })))
    } finally {
      setBusyAction(null)
    }
  }, [t, threadId])

  const handleSend = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    if (!threadId || !thread) return
    if (!draftText.trim()) return
    setSending(true)
    try {
      const msg = await createCommunicationMessage(threadId, {
        direction: internalNote ? 'system' : 'outbound',
        message_type: internalNote ? 'note' : (thread.channel === 'email' ? 'email' : 'text'),
        subject: thread.channel === 'email' && !internalNote ? (draftSubject.trim() || undefined) : undefined,
        body_text: draftText.trim(),
        sender_type: internalNote ? 'user' : 'user',
        recipient_address: !internalNote ? (recipientAddress.trim() || undefined) : undefined,
        delivery_status: internalNote ? 'sent' : 'queued',
        is_internal_note: internalNote,
      })
      let finalMsg = msg
      if (!internalNote && sendImmediately) {
        try {
          const dispatched = await dispatchCommunicationMessage(msg.id, { mark_delivered: true })
          finalMsg = dispatched.message
          setThread(dispatched.thread)
        } catch {
          // Keep queued message visible; user can dispatch later manually.
        }
      }
      setMessages((prev) => [...prev, finalMsg])
      setThread((prev) =>
        prev
          ? {
              ...prev,
              last_message_at: finalMsg.created_at,
              last_outbound_at: finalMsg.created_at,
              last_message_preview: finalMsg.body_text || finalMsg.subject || prev.last_message_preview,
              subject: thread.channel === 'email' && draftSubject.trim() ? draftSubject.trim() : prev.subject,
            }
          : prev
      )
      setDraftText('')
      setErrorText(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, t('app.communications.errors.load', { defaultValue: 'Failed to send message' })))
    } finally {
      setSending(false)
    }
  }, [draftSubject, draftText, internalNote, recipientAddress, sendImmediately, t, thread, threadId])

  const handleDispatchQueued = useCallback(async () => {
    if (!thread) return
    setDispatchingQueued(true)
    try {
      const result = await dispatchQueuedCommunicationMessages({ limit: 50, channel: thread.channel, mark_delivered: true })
      const byId = new Map(result.items.map((x) => [x.message.id, x.message]))
      setMessages((prev) => prev.map((m) => byId.get(m.id) || m))
      const threadItem = result.items.find((x) => x.thread.id === thread.id)?.thread
      if (threadItem) setThread(threadItem)
      setErrorText(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, t('app.communications.errors.load', { defaultValue: 'Failed to dispatch queued messages' })))
    } finally {
      setDispatchingQueued(false)
    }
  }, [t, thread])

  const handleDispatchOne = useCallback(async (messageId: string) => {
    setDispatchingMessageId(messageId)
    try {
      const result = await dispatchCommunicationMessage(messageId, { mark_delivered: true })
      setMessages((prev) => prev.map((m) => (m.id === messageId ? result.message : m)))
      setThread(result.thread)
      setErrorText(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, t('app.communications.errors.load', { defaultValue: 'Failed to dispatch message' })))
    } finally {
      setDispatchingMessageId(null)
    }
  }, [t])

  if (loading) {
    return <div className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>
  }

  if (!thread) {
    return (
      <div className="space-y-3">
        <WorkspaceTopNav active={null} />
        <div className="flex flex-wrap gap-2">
          <Link to="/app/calendar" className="text-sm text-brand-700 hover:text-brand-900">
            {t('app.communications.actions.back_to_calendar', { defaultValue: '← Back to calendar' })}
          </Link>
          <Link to="/app/messages" className="text-sm text-slate-600 hover:text-slate-900">
            {t('app.nav.items.messages', { defaultValue: 'Messages' })}
          </Link>
        </div>
        <ErrorRecoveryBanner
          info={{
            title: errorText || t('app.communications.states.empty', { defaultValue: 'No activity yet' }),
            hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
          }}
          onRetry={() => void load()}
          retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
          secondaryTo={threadListPath}
          secondaryLabel={t('app.communications.actions.back_to_hub', { defaultValue: 'Back to inbox' })}
          compact
        />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <WorkspaceTopNav active={null} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link to="/app/calendar" className="text-brand-700 hover:text-brand-900">
              {t('app.communications.actions.back_to_calendar', { defaultValue: '← Back to calendar' })}
            </Link>
            <Link to={threadListPath} className="text-slate-600 hover:text-slate-900">
              {t('app.communications.actions.back_to_hub', { defaultValue: 'Back to inbox' })}
            </Link>
          </div>
          <h1 className="mt-1 text-xl font-semibold text-slate-900">
            {thread.subject || thread.last_message_preview || `${String(thread.channel || '').toUpperCase()} thread`}
          </h1>
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
            <span>{t('app.communications.labels.thread', { defaultValue: 'Thread' })}: <span className="font-mono">{thread.id}</span></span>
            <span>{t('app.communications.labels.channel', { defaultValue: 'Channel' })}: {String(thread.channel || '').toUpperCase()}</span>
            <span>{t('app.communications.queue.assignee', { defaultValue: 'Assignee' })}: {thread.assignee_id || '—'}</span>
            <span>{t('app.communications.labels.status', { defaultValue: 'Status' })}: {thread.status}</span>
            <span>{t('app.communications.labels.unread', { defaultValue: 'Unread' })}: {thread.unread_count ?? 0}</span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="btn-secondary disabled:opacity-50"
            onClick={() => void load()}
          >
            {t('app.communications.actions.refresh', { defaultValue: 'Refresh' })}
          </button>
          <div className="relative" ref={workflowMenuRef}>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setOpenActionMenu((prev) => (prev === 'workflow' ? null : 'workflow'))}
            >
              {t('app.communications.thread.workflow_actions', { defaultValue: 'Workflow' })}
            </button>
            {openActionMenu === 'workflow' && (
              <div className="absolute right-0 z-20 mt-1 w-[min(18rem,calc(100vw-2rem))] rounded border border-slate-200 bg-white p-1 shadow-lg">
                <button
                  type="button"
                  className="dropdown-item disabled:opacity-50"
                  onClick={() => {
                    setOpenActionMenu(null)
                    void handleAutoAssign()
                  }}
                  disabled={busyAction === 'assign'}
                >
                  {busyAction === 'assign'
                    ? t('common.loading', { defaultValue: 'Loading...' })
                    : t('app.communications.queue.auto_assign', { defaultValue: 'Auto assign' })}
                </button>
                <button
                  type="button"
                  className="dropdown-item disabled:opacity-50"
                  onClick={() => {
                    setOpenActionMenu(null)
                    void handleMarkRead()
                  }}
                  disabled={busyAction === 'read' || (thread.unread_count ?? 0) <= 0}
                >
                  {busyAction === 'read'
                    ? t('common.loading', { defaultValue: 'Loading...' })
                    : t('app.communications.actions.mark_thread_read', { defaultValue: 'Mark read' })}
                </button>
              </div>
            )}
          </div>

          <div className="relative" ref={deliveryMenuRef}>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setOpenActionMenu((prev) => (prev === 'delivery' ? null : 'delivery'))}
            >
              {t('app.communications.thread.delivery_actions', { defaultValue: 'Delivery' })}
            </button>
            {openActionMenu === 'delivery' && (
              <div className="absolute right-0 z-20 mt-1 w-[min(18rem,calc(100vw-2rem))] rounded border border-slate-200 bg-white p-1 shadow-lg">
                <button
                  type="button"
                  className="dropdown-item disabled:opacity-50"
                  onClick={() => {
                    setOpenActionMenu(null)
                    void handleDispatchQueued()
                  }}
                  disabled={dispatchingQueued}
                >
                  {dispatchingQueued
                    ? t('common.loading', { defaultValue: 'Loading...' })
                    : t('app.communications.thread.dispatch_queued', { defaultValue: 'Dispatch queued' })}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {errorText && (
        <ErrorRecoveryBanner
          info={{
            title: errorText,
            hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
          }}
          onRetry={() => void load()}
          retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
          secondaryTo={threadListPath}
          secondaryLabel={t('app.communications.actions.back_to_hub', { defaultValue: 'Back to inbox' })}
          compact
        />
      )}

      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <section className="card p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">
            {t('app.communications.thread.timeline', { defaultValue: 'Timeline' })}
          </h2>
          <div className="space-y-3 max-h-[70vh] overflow-auto pr-1">
            {sortedMessages.length === 0 && (
              <div className="rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-sm text-slate-500">
                {t('app.communications.states.empty', { defaultValue: 'No activity yet' })}
              </div>
            )}
            {sortedMessages.map((msg) => {
              const isOutbound = msg.direction === 'outbound'
              const isInbound = msg.direction === 'inbound'
              const isNote = msg.is_internal_note || msg.message_type === 'note' || msg.direction === 'system'
              return (
                <div
                  key={msg.id}
                  className={clsx(
                    'rounded-xl border px-3 py-2',
                    isNote
                      ? 'border-violet-200 bg-violet-50'
                      : isOutbound
                        ? 'border-brand-200 bg-brand-50'
                        : isInbound
                          ? 'border-slate-200 bg-white'
                          : 'border-slate-200 bg-slate-50'
                  )}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-xs text-slate-600">
                      <span className="font-medium">{msg.sender_label || msg.sender_address || msg.sender_id || '—'}</span>
                      {' '}→{' '}
                      <span>{msg.recipient_label || msg.recipient_address || msg.recipient_id || '—'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={clsx(
                        'rounded-md px-2 py-0.5 text-[11px]',
                        isInbound ? 'bg-amber-100 text-amber-800' : isOutbound ? 'bg-emerald-100 text-emerald-700' : 'bg-violet-100 text-violet-700'
                      )}>
                        {isNote ? t('app.communications.thread.note', { defaultValue: 'Note' }) : msg.direction}
                      </span>
                      <span className="text-[11px] text-slate-500">{formatDateTime(msg.created_at)}</span>
                    </div>
                  </div>
                  {msg.subject && (
                    <div className="mt-1 text-sm font-medium text-slate-900">{msg.subject}</div>
                  )}
                  {msg.body_text && (
                    <div className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-800">{msg.body_text}</div>
                  )}
                  <div className="mt-1 text-[11px] text-slate-500">
                    {t('app.communications.labels.status', { defaultValue: 'Status' })}: {msg.delivery_status}
                    {msg.read_at && <> · {t('app.communications.actions.mark_thread_read', { defaultValue: 'Read' })}: {formatDateTime(msg.read_at)}</>}
                  </div>
                  {msg.direction === 'outbound' && !msg.is_internal_note && msg.delivery_status === 'queued' && (
                    <div className="mt-2">
                      <button
                        type="button"
                        onClick={() => void handleDispatchOne(msg.id)}
                        disabled={dispatchingMessageId === msg.id}
                        className="btn-secondary btn-xs disabled:opacity-50"
                      >
                        {dispatchingMessageId === msg.id
                          ? t('common.loading', { defaultValue: 'Loading...' })
                          : t('app.communications.thread.dispatch_now', { defaultValue: 'Dispatch now' })}
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>

        <section className="space-y-4">
          <div className="card p-4">
            <h2 className="mb-3 text-sm font-semibold text-slate-900">
              {t('app.communications.thread.compose', { defaultValue: 'Compose reply' })}
            </h2>
            <form className="space-y-3" onSubmit={handleSend}>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={internalNote}
                  onChange={(e) => setInternalNote(e.target.checked)}
                />
                {t('app.communications.thread.internal_note', { defaultValue: 'Send as internal note' })}
              </label>

              {!internalNote && (
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={sendImmediately}
                    onChange={(e) => setSendImmediately(e.target.checked)}
                  />
                  {t('app.communications.thread.send_immediately', { defaultValue: 'Dispatch immediately (simulate provider send)' })}
                </label>
              )}

              {thread.channel === 'email' && !internalNote && (
                <input
                  value={draftSubject}
                  onChange={(e) => setDraftSubject(e.target.value)}
                  className="w-full input"
                  placeholder={t('app.communications.thread.subject', { defaultValue: 'Subject' })}
                />
              )}

              {!internalNote && (
                <input
                  value={recipientAddress}
                  onChange={(e) => setRecipientAddress(e.target.value)}
                  className="w-full input"
                  placeholder={t('app.communications.thread.recipient', { defaultValue: 'Recipient address (email/phone/chat id)' })}
                />
              )}

              <textarea
                rows={8}
                value={draftText}
                onChange={(e) => setDraftText(e.target.value)}
                className="w-full textarea"
                placeholder={t('app.communications.thread.message', { defaultValue: 'Type your message...' })}
              />

              <button
                type="submit"
                disabled={sending || !draftText.trim()}
                className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {sending
                  ? t('common.loading', { defaultValue: 'Loading...' })
                  : t('app.communications.thread.send', { defaultValue: 'Send' })}
              </button>
            </form>
          </div>

          <div className="card p-4">
            <h3 className="text-sm font-semibold text-slate-900">
              {t('app.communications.thread.meta', { defaultValue: 'Thread metadata' })}
            </h3>
            <div className="mt-3 space-y-1 text-xs text-slate-600">
              <div>{t('app.communications.labels.channel', { defaultValue: 'Channel' })}: {thread.channel}</div>
              <div>{t('app.communications.labels.status', { defaultValue: 'Status' })}: {thread.status}</div>
              <div>{t('app.communications.queue.assignee', { defaultValue: 'Assignee' })}: {thread.assignee_id || '—'}</div>
              <div>{t('app.communications.labels.unread', { defaultValue: 'Unread' })}: {thread.unread_count}</div>
              <div>{t('app.communications.labels.entity', { defaultValue: 'Entity' })}: {thread.entity_type || '—'} / {thread.entity_id || '—'}</div>
              <div>Last message: {formatDateTime(thread.last_message_at)}</div>
              <div>Updated: {formatDateTime(thread.updated_at)}</div>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
