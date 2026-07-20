import { useMemo, useState } from 'react'
import clsx from 'clsx'
import { Link } from 'react-router-dom'
import type { CommunicationThread } from '../../api/communications'
import type { useCommunicationsThread } from '../../hooks/useCommunicationsThread'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import { friendlyErrorBannerSecondary } from '../../utils/friendlyError'
import { NextActionBadge } from '../candidate/NextActionBadge'
import { useThreadNextAction } from './useThreadNextAction'

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

/** Split visible body from quoted reply tails (collapsed by default). */
export function splitMessageBodyQuote(text: string): { main: string; quote: string | null } {
  const raw = String(text || '')
  if (!raw.trim()) return { main: '', quote: null }
  const lines = raw.split(/\r?\n/)
  let cut = -1
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i]
    const trimmed = line.trim()
    if (
      /^>/.test(trimmed) ||
      /^on .+ wrote:$/i.test(trimmed) ||
      /^am .+ schrieb/i.test(trimmed) ||
      /^w dniu .+ napisa/i.test(trimmed) ||
      /^-{2,}\s*original message\s*-{2,}$/i.test(trimmed) ||
      (/^from:\s.+/i.test(trimmed) &&
        i > 0 &&
        lines.slice(Math.max(0, i - 2), i).some((l) => !l.trim()))
    ) {
      cut = i
      break
    }
  }
  if (cut <= 0) return { main: raw, quote: null }
  const main = lines.slice(0, cut).join('\n').trimEnd()
  const quote = lines.slice(cut).join('\n').trim()
  if (!main) return { main: raw, quote: null }
  return { main, quote: quote || null }
}

type ThreadModel = ReturnType<typeof useCommunicationsThread>

type Props = {
  thread: CommunicationThread
  model: ThreadModel
  /** Full page chrome (calendar + list links, 2-col grid with metadata card). */
  layout: 'page' | 'inboxCenter'
}

function MessageBubble({
  msg,
  t,
  dispatchingMessageId,
  onDispatchOne,
}: {
  msg: ThreadModel['sortedMessages'][number]
  t: (key: string, vars?: Record<string, unknown>) => string
  dispatchingMessageId: string | null
  onDispatchOne: (id: string) => void
}) {
  const [showQuote, setShowQuote] = useState(false)
  const isOutbound = msg.direction === 'outbound'
  const isInbound = msg.direction === 'inbound'
  const isNote = msg.is_internal_note || msg.message_type === 'note' || msg.direction === 'system'
  const bodyText = String(msg.body_text || '').trim()
  const { main, quote } = useMemo(() => splitMessageBodyQuote(bodyText), [bodyText])
  const sender = msg.sender_label || msg.sender_address || msg.sender_id || '—'

  return (
    <div
      className={clsx(
        'flex w-full',
        isNote ? 'justify-center' : isOutbound ? 'justify-end' : 'justify-start',
      )}
    >
      <article
        className={clsx(
          'max-w-[min(42rem,92%)] rounded-2xl px-4 py-3 shadow-sm',
          isNote && 'border border-violet-200 bg-violet-50 text-violet-950',
          !isNote && isOutbound && 'bg-brand-600 text-white',
          !isNote && isInbound && 'border border-slate-200 bg-white text-slate-900',
          !isNote && !isOutbound && !isInbound && 'border border-slate-200 bg-slate-50 text-slate-800',
        )}
      >
        <header
          className={clsx(
            'mb-1.5 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 text-[11px]',
            isOutbound && !isNote ? 'text-brand-100' : 'text-slate-500',
          )}
        >
          <span className="truncate font-medium">{sender}</span>
          <span className="shrink-0 tabular-nums">{formatThreadDateTime(msg.created_at || msg.sent_at)}</span>
        </header>
        {msg.subject ? (
          <div className={clsx('mb-1 text-sm font-semibold', isOutbound && !isNote ? 'text-white' : 'text-slate-900')}>
            {msg.subject}
          </div>
        ) : null}
        {main ? (
          <div
            className={clsx(
              'whitespace-pre-wrap break-words text-[15px] leading-relaxed',
              isOutbound && !isNote ? 'text-white' : 'text-slate-800',
            )}
          >
            {main}
          </div>
        ) : null}
        {quote ? (
          <div className="mt-2">
            <button
              type="button"
              className={clsx(
                'text-[11px] font-medium underline-offset-2 hover:underline',
                isOutbound && !isNote ? 'text-brand-100' : 'text-slate-500',
              )}
              onClick={() => setShowQuote((v) => !v)}
            >
              {showQuote
                ? t('app.communications.thread.hide_quote', { defaultValue: 'Hide quoted text' })
                : t('app.communications.thread.show_quote', { defaultValue: 'Show quoted text' })}
            </button>
            {showQuote ? (
              <div
                className={clsx(
                  'mt-1 max-h-40 overflow-auto whitespace-pre-wrap break-words border-l-2 pl-3 text-xs leading-relaxed opacity-80',
                  isOutbound && !isNote ? 'border-brand-300 text-brand-50' : 'border-slate-300 text-slate-600',
                )}
              >
                {quote}
              </div>
            ) : null}
          </div>
        ) : null}
        <footer
          className={clsx(
            'mt-2 flex flex-wrap items-center gap-2 text-[11px]',
            isOutbound && !isNote ? 'text-brand-100/90' : 'text-slate-500',
          )}
        >
          <span>
            {isNote
              ? t('app.communications.thread.note')
              : isInbound
                ? t('app.communications.thread.inbound', { defaultValue: 'Received' })
                : t('app.communications.thread.outbound', { defaultValue: 'Sent' })}
          </span>
          {msg.delivery_status ? (
            <>
              <span aria-hidden>·</span>
              <span>{msg.delivery_status}</span>
            </>
          ) : null}
          {msg.read_at ? (
            <>
              <span aria-hidden>·</span>
              <span>
                {t('app.communications.actions.read_at')}: {formatThreadDateTime(msg.read_at)}
              </span>
            </>
          ) : null}
        </footer>
        {msg.direction === 'outbound' && !msg.is_internal_note && msg.delivery_status === 'queued' ? (
          <div className="mt-2">
            <button
              type="button"
              onClick={() => void onDispatchOne(msg.id)}
              disabled={dispatchingMessageId === msg.id}
              className={clsx(
                'rounded-md px-2 py-1 text-[11px] font-medium disabled:opacity-50',
                isOutbound ? 'bg-white/15 text-white hover:bg-white/25' : 'btn-secondary btn-xs',
              )}
            >
              {dispatchingMessageId === msg.id
                ? t('common.loading')
                : t('app.communications.thread.dispatch_now')}
            </button>
          </div>
        ) : null}
      </article>
    </div>
  )
}

export default function CommunicationsThreadWorkArea({ thread, model, layout }: Props) {
  const { t } = useI18n()
  const [composeAdvancedOpen, setComposeAdvancedOpen] = useState(false)
  const {
    threadError,
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

  const threadLoadErrorBanner = threadError
  const btn = 'btn-secondary btn-sm'

  const threadNextActionFingerprint = `${thread.status ?? ''}|${thread.is_archived ? 1 : 0}|${thread.unread_count ?? 0}|${thread.sla_due_at ?? ''}|${thread.last_inbound_at ?? ''}|${thread.last_outbound_at ?? ''}`
  const {
    data: threadNextAction,
    loading: threadNextActionLoading,
    error: threadNextActionError,
  } = useThreadNextAction(thread.id, threadNextActionFingerprint)

  const participants = useMemo(() => {
    const raw = thread.participants_json
    if (!raw || typeof raw !== 'object') return ''
    const senders = Array.isArray((raw as { senders?: unknown }).senders)
      ? ((raw as { senders: unknown[] }).senders as unknown[]).map((x) => String(x || '').trim()).filter(Boolean)
      : []
    const recipients = Array.isArray((raw as { recipients?: unknown }).recipients)
      ? ((raw as { recipients: unknown[] }).recipients as unknown[])
          .map((x) => String(x || '').trim())
          .filter(Boolean)
      : []
    const parts = [...new Set([...senders, ...recipients])]
    return parts.slice(0, 4).join(', ') + (parts.length > 4 ? '…' : '')
  }, [thread.participants_json])

  const actionBar = (
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" className={clsx(btn, 'disabled:opacity-50')} onClick={() => void load()}>
        {t('app.communications.actions.refresh')}
      </button>
      <div className="relative" ref={workflowMenuRef}>
        <button
          type="button"
          className={btn}
          onClick={() => setOpenActionMenu((prev) => (prev === 'workflow' ? null : 'workflow'))}
        >
          {t('app.communications.thread.workflow_actions')}
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
              {busyAction === 'assign' ? t('common.loading') : t('app.communications.queue.auto_assign')}
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
              {busyAction === 'read' ? t('common.loading') : t('app.communications.actions.mark_thread_read')}
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
          {t('app.communications.thread.delivery_actions')}
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
              {dispatchingQueued ? t('common.loading') : t('app.communications.thread.dispatch_queued')}
            </button>
          </div>
        )}
      </div>
    </div>
  )

  const timelineSection = (
    <section className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-1 py-2">
        {sortedMessages.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-200 px-3 py-10 text-center text-sm text-slate-500">
            {t('app.communications.states.empty')}
          </div>
        )}
        {sortedMessages.map((msg) => (
          <MessageBubble
            key={msg.id}
            msg={msg}
            t={t}
            dispatchingMessageId={dispatchingMessageId}
            onDispatchOne={handleDispatchOne}
          />
        ))}
      </div>
    </section>
  )

  const composeSection = (
    <div className="shrink-0 border-t border-slate-200 bg-white pt-3">
      {threadUnlinked && (
        <div className="mb-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-950">
          {String(thread.channel || '').toLowerCase() === 'email'
            ? t('app.communications.email.mandatory_link.composer_banner')
            : t('app.communications_messages.mandatory_link.composer_banner')}
        </div>
      )}
      <form className="space-y-2" onSubmit={handleSend}>
        {thread.channel === 'email' && !internalNote && (
          <input
            value={draftSubject}
            onChange={(e) => setDraftSubject(e.target.value)}
            className="w-full input"
            placeholder={t('app.communications.thread.subject')}
          />
        )}
        <textarea
          rows={3}
          value={draftText}
          onChange={(e) => setDraftText(e.target.value)}
          className="w-full resize-y textarea min-h-[4.5rem] max-h-40"
          placeholder={t('app.communications.thread.message')}
        />
        <div className="flex flex-wrap items-center gap-2">
          {thread.channel === 'email' && !internalNote && templates.length > 0 && (
            <>
              <select
                className="input max-w-[14rem] text-sm"
                value={selectedTemplateId}
                onChange={(e) => setSelectedTemplateId(e.target.value)}
              >
                {templates.map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="btn-secondary btn-sm"
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
                {t('common.actions.insert')}
              </button>
            </>
          )}
          {thread.channel === 'email' && !internalNote && inferredSignature && (
            <label className="inline-flex items-center gap-1.5 text-xs text-slate-600">
              <input type="checkbox" checked={applySignature} onChange={(e) => setApplySignature(e.target.checked)} />
              {t('app.communications.email.signature.apply')}
            </label>
          )}
          <button
            type="button"
            className="text-xs font-medium text-slate-500 hover:text-slate-800"
            onClick={() => setComposeAdvancedOpen((v) => !v)}
          >
            {composeAdvancedOpen
              ? t('app.communications.thread.compose_fewer', { defaultValue: 'Fewer options' })
              : t('app.communications.thread.compose_more', { defaultValue: 'More options' })}
          </button>
          <div className="ml-auto">
            <button
              type="submit"
              disabled={sending || !draftText.trim()}
              className="btn-primary btn-sm disabled:cursor-not-allowed disabled:opacity-50"
            >
              {sending ? t('common.loading') : t('app.communications.thread.send')}
            </button>
          </div>
        </div>
        {composeAdvancedOpen && (
          <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2">
            <label className="inline-flex items-center gap-1.5 text-xs text-slate-700">
              <input type="checkbox" checked={internalNote} onChange={(e) => setInternalNote(e.target.checked)} />
              {t('app.communications.thread.internal_note')}
            </label>
            {!internalNote && (
              <label className="inline-flex items-center gap-1.5 text-xs text-slate-700">
                <input
                  type="checkbox"
                  checked={sendImmediately}
                  onChange={(e) => setSendImmediately(e.target.checked)}
                />
                {t('app.communications.thread.send_immediately')}
              </label>
            )}
            {!internalNote && (
              <input
                value={recipientAddress}
                onChange={(e) => setRecipientAddress(e.target.value)}
                className="input max-w-xs text-sm"
                placeholder={t('app.communications.thread.recipient')}
              />
            )}
          </div>
        )}
      </form>
    </div>
  )

  const headerBlock = (
    <div className="flex shrink-0 flex-wrap items-start justify-between gap-2 border-b border-slate-200 pb-3">
      <div className="min-w-0 flex-1">
        <div className="truncate text-base font-semibold text-slate-900">
          {thread.subject || thread.last_message_preview || `${String(thread.channel || '').toUpperCase()} thread`}
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-500">
          <span className="font-medium uppercase tracking-wide text-slate-600">
            {String(thread.channel || '').toUpperCase()}
          </span>
          <span aria-hidden>·</span>
          <span>{thread.status || '—'}</span>
          {participants ? (
            <>
              <span aria-hidden>·</span>
              <span className="truncate" title={participants}>
                {participants}
              </span>
            </>
          ) : null}
          {thread.unread_count ? (
            <>
              <span aria-hidden>·</span>
              <span>
                {thread.unread_count} {t('app.communications.labels.unread_lower')}
              </span>
            </>
          ) : null}
          <NextActionBadge
            dto={threadNextAction}
            loading={threadNextActionLoading}
            error={threadNextActionError}
          />
        </div>
      </div>
      {actionBar}
    </div>
  )

  if (layout === 'inboxCenter') {
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        {headerBlock}
        {threadLoadErrorBanner && (
          <ErrorRecoveryBanner
            info={threadLoadErrorBanner}
            onRetry={() => void load()}
            retryLabel={t('common.actions.refresh')}
            {...friendlyErrorBannerSecondary(threadLoadErrorBanner, threadListPath, t('app.communications.actions.back_to_hub'))}
            compact
          />
        )}
        {timelineSection}
        {composeSection}
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link to={CRM_APP_PATHS.calendar} className="text-brand-700 hover:text-brand-900">
              {t('app.communications.actions.back_to_calendar')}
            </Link>
            <Link to={threadListPath} className="text-slate-600 hover:text-slate-900">
              {t('app.communications.actions.back_to_hub')}
            </Link>
          </div>
          <h1 className="mt-1 text-xl font-semibold text-slate-900">
            {thread.subject || thread.last_message_preview || `${String(thread.channel || '').toUpperCase()} thread`}
          </h1>
          <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
            <span>
              {t('app.communications.labels.channel')}: {String(thread.channel || '').toUpperCase()}
            </span>
            <span>
              {t('app.communications.queue.assignee')}: {thread.assignee_id || '—'}
            </span>
            <span>
              {t('app.communications.labels.status')}: {thread.status}
            </span>
            <NextActionBadge
              dto={threadNextAction}
              loading={threadNextActionLoading}
              error={threadNextActionError}
            />
          </div>
        </div>
        {actionBar}
      </div>
      {threadLoadErrorBanner && (
        <ErrorRecoveryBanner
          info={threadLoadErrorBanner}
          onRetry={() => void load()}
          retryLabel={t('common.actions.refresh')}
          {...friendlyErrorBannerSecondary(threadLoadErrorBanner, threadListPath, t('app.communications.actions.back_to_hub'))}
          compact
        />
      )}
      <div className="flex min-h-[70vh] flex-col overflow-hidden rounded-xl border border-slate-200 bg-slate-50/50 p-4">
        {timelineSection}
        {composeSection}
      </div>
    </div>
  )
}
