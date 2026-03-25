import clsx from 'clsx'
import { Link } from 'react-router-dom'
import type { CommunicationThread } from '../../api/communications'
import type { useCommunicationsThread } from '../../hooks/useCommunicationsThread'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'

export function formatThreadDateTime(value?: string | null): string {
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

type ThreadModel = ReturnType<typeof useCommunicationsThread>

type Props = {
  thread: CommunicationThread
  model: ThreadModel
  /** Full page chrome (calendar + list links, 2-col grid with metadata card). */
  layout: 'page' | 'inboxCenter'
}

export default function CommunicationsThreadWorkArea({ thread, model, layout }: Props) {
  const { t } = useI18n()
  const {
    errorText,
    errorSecondaryTo,
    errorSecondaryLabel,
    threadListPath,
    busyAction,
    sending,
    dispatchingQueued,
    dispatchingMessageId,
    openActionMenu,
    setOpenActionMenu,
    workflowMenuRef,
    deliveryMenuRef,
    draftText,
    setDraftText,
    draftSubject,
    setDraftSubject,
    recipientAddress,
    setRecipientAddress,
    internalNote,
    setInternalNote,
    sendImmediately,
    setSendImmediately,
    templates,
    selectedTemplateId,
    setSelectedTemplateId,
    applySignature,
    setApplySignature,
    threadUnlinked,
    inferredSignature,
    sortedMessages,
    load,
    handleMarkRead,
    handleAutoAssign,
    handleSend,
    handleDispatchQueued,
    handleDispatchOne,
  } = model

  const btn = layout === 'inboxCenter' ? 'btn-secondary btn-sm' : 'btn-secondary'

  const actionBar = (
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" className={clsx(btn, 'disabled:opacity-50')} onClick={() => void load()}>
        {t('app.communications.actions.refresh', { defaultValue: 'Refresh' })}
      </button>
      <div className="relative" ref={workflowMenuRef}>
        <button
          type="button"
          className={btn}
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
          className={btn}
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
  )

  const timelineSection = (
    <section className={clsx('card p-4', layout === 'inboxCenter' && 'min-h-0 flex flex-1 flex-col')}>
      <h2 className="mb-3 shrink-0 text-sm font-semibold text-slate-900">
        {t('app.communications.thread.timeline', { defaultValue: 'Timeline' })}
      </h2>
      <div
        className={clsx(
          'space-y-3 overflow-auto pr-1',
          layout === 'page' && 'max-h-[70vh]',
          layout === 'inboxCenter' && 'min-h-0 flex-1 max-h-[min(50vh,28rem)] xl:max-h-[calc(100vh-14rem)]',
        )}
      >
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
                      : 'border-slate-200 bg-slate-50',
              )}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-xs text-slate-600">
                  <span className="font-medium">{msg.sender_label || msg.sender_address || msg.sender_id || '—'}</span>
                  {' '}→{' '}
                  <span>{msg.recipient_label || msg.recipient_address || msg.recipient_id || '—'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={clsx(
                      'rounded-md px-2 py-0.5 text-[11px]',
                      isInbound ? 'bg-amber-100 text-amber-800' : isOutbound ? 'bg-emerald-100 text-emerald-700' : 'bg-violet-100 text-violet-700',
                    )}
                  >
                    {isNote ? t('app.communications.thread.note', { defaultValue: 'Note' }) : msg.direction}
                  </span>
                  <span className="text-[11px] text-slate-500">{formatThreadDateTime(msg.created_at)}</span>
                </div>
              </div>
              {msg.subject && <div className="mt-1 text-sm font-medium text-slate-900">{msg.subject}</div>}
              {msg.body_text && (
                <div className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-800">{msg.body_text}</div>
              )}
              <div className="mt-1 text-[11px] text-slate-500">
                {t('app.communications.labels.status', { defaultValue: 'Status' })}: {msg.delivery_status}
                {msg.read_at && (
                  <>
                    {' '}
                    · {t('app.communications.actions.mark_thread_read', { defaultValue: 'Read' })}:{' '}
                    {formatThreadDateTime(msg.read_at)}
                  </>
                )}
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
  )

  const composeSection = (
    <div className="card p-4">
      <h2 className="mb-3 text-sm font-semibold text-slate-900">
        {t('app.communications.thread.compose', { defaultValue: 'Compose reply' })}
      </h2>
      {threadUnlinked && (
        <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
          {String(thread.channel || '').toLowerCase() === 'email'
            ? t('app.communications.email.mandatory_link.composer_banner')
            : t('app.communications_messages.mandatory_link.composer_banner')}
        </div>
      )}
      <form className="space-y-3" onSubmit={handleSend}>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={internalNote} onChange={(e) => setInternalNote(e.target.checked)} />
          {t('app.communications.thread.internal_note', { defaultValue: 'Send as internal note' })}
        </label>
        {!internalNote && (
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={sendImmediately} onChange={(e) => setSendImmediately(e.target.checked)} />
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
        {thread.channel === 'email' && !internalNote && templates.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <select className="input" value={selectedTemplateId} onChange={(e) => setSelectedTemplateId(e.target.value)}>
              {templates.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                const tpl = templates.find((x) => x.id === selectedTemplateId)
                if (!tpl) return
                const body = String(tpl.body || '').trim()
                if (!body) return
                setDraftText((prev) => {
                  const base = String(prev || '')
                  if (!base.trim()) return body
                  return `${base.trimEnd()}\n\n${body}`
                })
              }}
            >
              {t('common.actions.insert', { defaultValue: 'Insert' })}
            </button>
          </div>
        )}
        {thread.channel === 'email' && !internalNote && inferredSignature && (
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={applySignature} onChange={(e) => setApplySignature(e.target.checked)} />
            {t('app.communications.email.signature.apply', { defaultValue: 'Add signature' })}
          </label>
        )}
        <textarea
          rows={layout === 'inboxCenter' ? 5 : 8}
          value={draftText}
          onChange={(e) => setDraftText(e.target.value)}
          className="w-full textarea"
          placeholder={t('app.communications.thread.message', { defaultValue: 'Type your message...' })}
        />
        <button
          type="submit"
          disabled={sending || !draftText.trim()}
          className="w-full btn-primary disabled:cursor-not-allowed disabled:opacity-50"
        >
          {sending ? t('common.loading', { defaultValue: 'Loading...' }) : t('app.communications.thread.send', { defaultValue: 'Send' })}
        </button>
      </form>
    </div>
  )

  const metaCard = (
    <div className="card p-4">
      <h3 className="text-sm font-semibold text-slate-900">
        {t('app.communications.thread.meta', { defaultValue: 'Thread metadata' })}
      </h3>
      <div className="mt-3 space-y-1 text-xs text-slate-600">
        <div>
          {t('app.communications.labels.channel', { defaultValue: 'Channel' })}: {thread.channel}
        </div>
        <div>
          {t('app.communications.labels.status', { defaultValue: 'Status' })}: {thread.status}
        </div>
        <div>
          {t('app.communications.queue.assignee', { defaultValue: 'Assignee' })}: {thread.assignee_id || '—'}
        </div>
        <div>
          {t('app.communications.labels.unread', { defaultValue: 'Unread' })}: {thread.unread_count}
        </div>
        <div>
          {t('app.communications.labels.entity', { defaultValue: 'Entity' })}: {thread.entity_type || '—'} / {thread.entity_id || '—'}
        </div>
        <div>Last message: {formatThreadDateTime(thread.last_message_at)}</div>
        <div>Updated: {formatThreadDateTime(thread.updated_at)}</div>
      </div>
    </div>
  )

  if (layout === 'inboxCenter') {
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-3">
        <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-200 pb-2">
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-semibold text-slate-900">
              {thread.subject || thread.last_message_preview || `${String(thread.channel || '').toUpperCase()} thread`}
            </div>
            <div className="mt-0.5 flex flex-wrap gap-x-2 gap-y-0.5 text-[11px] text-slate-500">
              <span>{String(thread.channel || '').toUpperCase()}</span>
              <span>·</span>
              <span>{thread.status || '—'}</span>
              {thread.unread_count ? (
                <>
                  <span>·</span>
                  <span>
                    {thread.unread_count} {t('app.communications.labels.unread', { defaultValue: 'unread' })}
                  </span>
                </>
              ) : null}
            </div>
          </div>
          {actionBar}
        </div>
        {errorText && (
          <ErrorRecoveryBanner
            info={{
              title: errorText,
              hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
            }}
            onRetry={() => void load()}
            retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
            secondaryTo={errorSecondaryTo || threadListPath}
            secondaryLabel={errorSecondaryLabel || t('app.communications.actions.back_to_hub', { defaultValue: 'Back to inbox' })}
            compact
          />
        )}
        <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden">
          {timelineSection}
          {composeSection}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
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
            <span>
              {t('app.communications.labels.thread', { defaultValue: 'Thread' })}: <span className="font-mono">{thread.id}</span>
            </span>
            <span>
              {t('app.communications.labels.channel', { defaultValue: 'Channel' })}: {String(thread.channel || '').toUpperCase()}
            </span>
            <span>
              {t('app.communications.queue.assignee', { defaultValue: 'Assignee' })}: {thread.assignee_id || '—'}
            </span>
            <span>
              {t('app.communications.labels.status', { defaultValue: 'Status' })}: {thread.status}
            </span>
            <span>
              {t('app.communications.labels.unread', { defaultValue: 'Unread' })}: {thread.unread_count ?? 0}
            </span>
          </div>
        </div>
        {actionBar}
      </div>
      {errorText && (
        <ErrorRecoveryBanner
          info={{
            title: errorText,
            hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
          }}
          onRetry={() => void load()}
          retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
          secondaryTo={errorSecondaryTo || threadListPath}
          secondaryLabel={errorSecondaryLabel || t('app.communications.actions.back_to_hub', { defaultValue: 'Back to inbox' })}
          compact
        />
      )}
      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        {timelineSection}
        <section className="space-y-4">
          {composeSection}
          {metaCard}
        </section>
      </div>
    </div>
  )
}
