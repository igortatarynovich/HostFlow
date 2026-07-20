import clsx from 'clsx'
import { Link } from 'react-router-dom'
import type { CommunicationThread } from '../../api/communications'
import type { useCommunicationsThread } from '../../hooks/useCommunicationsThread'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary } from '../../utils/friendlyError'
import { primaryThreadEntityLabel } from '../../utils/communicationThreadEntityLinks'
import ThreadComposer from './ThreadComposer'
import ThreadDeliveryDiagnosticsStrip from './ThreadDeliveryDiagnosticsStrip'
import ThreadNextActionPanel from './ThreadNextActionPanel'
import ThreadWorkspaceSlaChip from './ThreadWorkspaceSlaChip'

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
    threadContext,
    composerDraft,
    patchComposerDraft,
    setDraftText,
    templates,
    selectedTemplateId,
    setSelectedTemplateId,
    threadUnlinked,
    sortedMessages,
    load,
    runCommand,
    handleMarkRead,
    handleAutoAssign,
    handleSend,
    handleDispatchQueued,
    handleDispatchOne,
  } = model

  const threadLoadErrorBanner = threadError
  const work = threadContext?.work_state
  const headerStatus = threadContext?.identity?.thread?.status || thread.status
  const headerChannel = threadContext?.identity?.thread?.channel || thread.channel
  const headerUnread = work?.unread_count ?? thread.unread_count
  const headerSubject =
    threadContext?.identity?.thread?.subject ||
    thread.subject ||
    thread.last_message_preview ||
    `${String(headerChannel || '').toUpperCase()} thread`

  const btn = layout === 'inboxCenter' ? 'btn-secondary btn-sm' : 'btn-secondary'

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
              {busyAction === 'assign'
                ? t('common.loading')
                : t('app.communications.queue.auto_assign')}
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
                ? t('common.loading')
                : t('app.communications.actions.mark_thread_read')}
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
              {dispatchingQueued
                ? t('common.loading')
                : t('app.communications.thread.dispatch_queued')}
            </button>
          </div>
        )}
      </div>
    </div>
  )

  const timelineSection = (
    <section className={clsx('card p-4', layout === 'inboxCenter' && 'min-h-0 flex flex-1 flex-col')}>
      <h2 className="mb-3 shrink-0 text-sm font-semibold text-slate-900">
        {t('app.communications.thread.timeline')}
      </h2>
      <div className="mb-2 space-y-2">
        <ThreadDeliveryDiagnosticsStrip
          messages={sortedMessages}
          deliverySummary={threadContext?.workspace?.delivery_summary}
        />
        <ThreadNextActionPanel
          nextAction={work?.next_action}
          runCommand={runCommand}
          compact={layout === 'inboxCenter'}
        />
      </div>
      <div
        className={clsx(
          'space-y-3 overflow-auto pr-1',
          layout === 'page' && 'max-h-[70vh]',
          layout === 'inboxCenter' && 'min-h-0 flex-1 max-h-[min(50vh,28rem)] xl:max-h-[calc(100vh-14rem)]',
        )}
      >
        {sortedMessages.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-sm text-slate-500">
            {t('app.communications.states.empty')}
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
                    {isNote ? t('app.communications.thread.note') : msg.direction}
                  </span>
                  <span className="text-[11px] text-slate-500">{formatThreadDateTime(msg.created_at)}</span>
                </div>
              </div>
              {msg.subject && <div className="mt-1 text-sm font-medium text-slate-900">{msg.subject}</div>}
              {msg.body_text && (
                <div className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-800">{msg.body_text}</div>
              )}
              <div className="mt-1 text-[11px] text-slate-500">
                {t('app.communications.labels.status')}: {msg.delivery_status}
                {msg.read_at && (
                  <>
                    {' '}
                    · {t('app.communications.actions.read_at')}:{' '}
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
                      ? t('common.loading')
                      : t('app.communications.thread.dispatch_now')}
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )

  const templatesSlot =
    String(composerDraft.channel || thread.channel || '').toLowerCase() === 'email' &&
    !composerDraft.internalNote &&
    templates.length > 0 ? (
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
          {t('common.actions.insert')}
        </button>
      </div>
    ) : null

  const composeSection = (
    <div className="card p-4">
      <h2 className="mb-3 text-sm font-semibold text-slate-900">
        {t('app.communications.thread.compose')}
      </h2>
      {threadUnlinked && (
        <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
          {String(thread.channel || '').toLowerCase() === 'email'
            ? t('app.communications.email.mandatory_link.composer_banner')
            : t('app.communications_messages.mandatory_link.composer_banner')}
        </div>
      )}
      {threadContext ? (
        <ThreadComposer
          context={threadContext}
          draft={composerDraft}
          onDraftChange={patchComposerDraft}
          onSubmit={handleSend}
          sending={sending}
          templatesSlot={templatesSlot}
          compact={layout === 'inboxCenter'}
        />
      ) : (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600">
          {t('app.communications.composer.context_loading', {
            defaultValue: 'Loading composer context from Communication Platform…',
          })}
        </div>
      )}
    </div>
  )

  const metaCard = (
    <div className="card p-4">
      <h3 className="text-sm font-semibold text-slate-900">
        {t('app.communications.thread.meta')}
      </h3>
      <div className="mt-3 space-y-1 text-xs text-slate-600">
        <div>
          {t('app.communications.labels.channel')}:{' '}
          {threadContext?.identity?.thread?.channel || thread.channel}
        </div>
        <div>
          {t('app.communications.labels.status')}:{' '}
          {threadContext?.identity?.thread?.status || thread.status}
        </div>
        <div>
          {t('app.communications.queue.assignee')}:{' '}
          {threadContext?.work_state?.assignee_id || thread.assignee_id || '—'}
        </div>
        <div>
          {t('app.communications.labels.unread')}:{' '}
          {threadContext?.work_state?.unread_count ?? thread.unread_count}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ThreadWorkspaceSlaChip workState={work} runCommand={runCommand} interactive />
        </div>
        <div>
          {t('app.communications.labels.entity')}:{' '}
          {threadContext?.identity?.linked_entities?.length
            ? threadContext.identity.linked_entities
                .map((e) => String(e.entity_type || e.entityType || 'entity'))
                .join(', ')
            : primaryThreadEntityLabel(thread)}
        </div>
        {threadContext?.work_state?.active_queues?.length ? (
          <div>
            {t('app.communications.queues.title', { defaultValue: 'Queues' })}:{' '}
            {threadContext.work_state.active_queues.join(', ')}
          </div>
        ) : null}
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
            <div className="truncate text-sm font-semibold text-slate-900">{headerSubject}</div>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-slate-500">
              <span>{String(headerChannel || '').toUpperCase()}</span>
              <span>·</span>
              <span>{headerStatus || '—'}</span>
              {headerUnread ? (
                <>
                  <span>·</span>
                  <span>
                    {headerUnread} {t('app.communications.labels.unread_lower')}
                  </span>
                </>
              ) : null}
              <ThreadWorkspaceSlaChip workState={work} runCommand={runCommand} interactive />
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
            <Link to={CRM_APP_PATHS.calendar} className="text-brand-700 hover:text-brand-900">
              {t('app.communications.actions.back_to_calendar')}
            </Link>
            <Link to={threadListPath} className="text-slate-600 hover:text-slate-900">
              {t('app.communications.actions.back_to_hub')}
            </Link>
          </div>
          <h1 className="mt-1 text-xl font-semibold text-slate-900">{headerSubject}</h1>
          <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
            <span>
              {t('app.communications.labels.thread')}: <span className="font-mono">{thread.id}</span>
            </span>
            <span>
              {t('app.communications.labels.channel')}: {String(headerChannel || '').toUpperCase()}
            </span>
            <span>
              {t('app.communications.queue.assignee')}: {work?.assignee_id || thread.assignee_id || '—'}
            </span>
            <span>
              {t('app.communications.labels.status')}: {headerStatus}
            </span>
            <span>
              {t('app.communications.labels.unread')}: {headerUnread ?? 0}
            </span>
            <ThreadWorkspaceSlaChip workState={work} runCommand={runCommand} interactive />
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
