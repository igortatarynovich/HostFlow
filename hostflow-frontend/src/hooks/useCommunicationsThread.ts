import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  autoAssignCommunicationThread,
  createCommunicationMessage,
  dispatchCommunicationMessage,
  dispatchQueuedCommunicationMessages,
  getCommunicationThread,
  getCommunicationsSettings,
  executeWorkspaceCommand,
  getThreadContext,
  type CommunicationMessage,
  type CommunicationThread,
  type ThreadContext,
  type WorkspaceCommandResult,
} from '../api/communications'
import { draftFromThreadContext, type ThreadComposerDraft } from '../components/communications/ThreadComposer'
import { recordTtvStepCompleted } from '../api/analytics'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'
import { isCommunicationThreadUnlinked } from '../utils/communicationThreadUnlinked'
import { communicationApiTranslatedDetail } from '../utils/communicationApiTranslatedDetail'
import { communicationPipelineReasonMessage } from '../utils/communicationPipelineReason'
import { formatOutgoingSignaturePlain } from '../utils/outgoingEmailSignature'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { friendlyFormHintError, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'

function commsErr(
  err: any,
  fallbackTitle: string,
  t: (key: string, options?: { defaultValue?: string; values?: Record<string, string | number> }) => string,
  secondary?: { to: string; label: string },
): FriendlyErrorInfo {
  const translated = communicationApiTranslatedDetail(err, t)
  const fe = getFriendlyErrorInfo(err, fallbackTitle, t)
  return {
    ...fe,
    title: translated || fe.title,
    ...(secondary ? { secondaryTo: secondary.to, secondaryLabel: secondary.label } : {}),
  }
}

export type UseCommunicationsThreadOptions = {
  /** Override list path for error recovery links (e.g. `/app/inbox` in Communication Center). */
  backListPathOverride?: string
  /** Bump to refetch thread/messages when the parent list refreshed the same `threadId` (e.g. Messages/Email workspace). */
  reloadSignal?: number
}

export function useCommunicationsThread(threadId: string, opts?: UseCommunicationsThreadOptions) {
  const { t, locale } = useI18n()
  const { me } = useAuth()
  const planLimitModal = usePlanLimitModal()
  const [thread, setThread] = useState<CommunicationThread | null>(null)
  const [threadContext, setThreadContext] = useState<ThreadContext | null>(null)
  const [messages, setMessages] = useState<CommunicationMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [threadError, setThreadError] = useState<FriendlyErrorInfo | null>(null)
  const [busyAction, setBusyAction] = useState<'assign' | 'read' | null>(null)
  const [sending, setSending] = useState(false)
  const [dispatchingQueued, setDispatchingQueued] = useState(false)
  const [dispatchingMessageId, setDispatchingMessageId] = useState<string | null>(null)
  const [openActionMenu, setOpenActionMenu] = useState<null | 'workflow' | 'delivery'>(null)
  const workflowMenuRef = useRef<HTMLDivElement | null>(null)
  const deliveryMenuRef = useRef<HTMLDivElement | null>(null)
  const [composerDraft, setComposerDraft] = useState<ThreadComposerDraft>({
    text: '',
    subject: '',
    recipientAddress: '',
    intent: '',
    channel: '',
    internalNote: false,
    sendImmediately: true,
    applySignature: true,
  })
  const [templates, setTemplates] = useState<Array<{ id: string; label: string; body: string }>>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('')
  const firstEmailTtvSentRef = useRef(false)
  const seededContextForThreadRef = useRef<string | null>(null)

  const patchComposerDraft = useCallback((patch: Partial<ThreadComposerDraft>) => {
    setComposerDraft((prev) => ({ ...prev, ...patch }))
  }, [])

  // Compat aliases for existing work-area / control-panel consumers.
  const draftText = composerDraft.text
  const setDraftText = useCallback(
    (value: string | ((prev: string) => string)) => {
      setComposerDraft((prev) => ({
        ...prev,
        text: typeof value === 'function' ? value(prev.text) : value,
      }))
    },
    [],
  )
  const draftSubject = composerDraft.subject
  const setDraftSubject = useCallback((value: string) => patchComposerDraft({ subject: value }), [patchComposerDraft])
  const recipientAddress = composerDraft.recipientAddress
  const setRecipientAddress = useCallback(
    (value: string) => patchComposerDraft({ recipientAddress: value }),
    [patchComposerDraft],
  )
  const internalNote = composerDraft.internalNote
  const setInternalNote = useCallback(
    (value: boolean) => patchComposerDraft({ internalNote: value }),
    [patchComposerDraft],
  )
  const sendImmediately = composerDraft.sendImmediately
  const setSendImmediately = useCallback(
    (value: boolean) => patchComposerDraft({ sendImmediately: value }),
    [patchComposerDraft],
  )
  const applySignature = composerDraft.applySignature
  const setApplySignature = useCallback(
    (value: boolean) => patchComposerDraft({ applySignature: value }),
    [patchComposerDraft],
  )

  const threadListPath = useMemo(() => {
    if (opts?.backListPathOverride) return opts.backListPathOverride
    const email = String(thread?.channel || '').toLowerCase() === 'email'
    return email ? CRM_APP_PATHS.inboxEmailScoped : CRM_APP_PATHS.inboxMessagesScoped
  }, [opts?.backListPathOverride, thread?.channel])

  const threadUnlinked = useMemo(() => Boolean(thread && isCommunicationThreadUnlinked(thread)), [thread])

  /** Default: personal cabinet signature only — never tenant recruitment/client stubs. */
  const inferredSignature = useMemo(() => {
    if (!thread || String(thread.channel || '').toLowerCase() !== 'email') return ''
    return formatOutgoingSignaturePlain({
      signature: me?.signature ?? null,
      fallbackFirstName: me?.first_name,
      fallbackLastName: me?.last_name,
      fallbackFullName: me?.full_name,
      fallbackPosition: me?.position,
      fallbackPhone: me?.phone,
      fallbackEmail: me?.email,
      locale,
    })
  }, [locale, me, thread])

  const appendSignature = useCallback(
    (text: string) => {
      const sig = inferredSignature
      if (!sig) return text
      const base = String(text || '')
      const normalized = base.trimEnd()
      if (!normalized) return `--\n${sig}`
      return `${normalized}\n\n--\n${sig}`
    },
    [inferredSignature],
  )

  const load = useCallback(async () => {
    if (!threadId) {
      setLoading(false)
      setThread(null)
      setThreadContext(null)
      setMessages([])
      seededContextForThreadRef.current = null
      return
    }
    setLoading(true)
    setThreadError(null)
    try {
      // Critical path: thread + timeline first so the page paints quickly.
      const data = await getCommunicationThread(threadId, { messagesLimit: 50 })
      setThread(data.thread)
      setMessages(Array.isArray(data.messages) ? data.messages : [])
      setLoading(false)

      // Secondary: Workspace read model + templates (non-blocking for timeline).
      void getThreadContext(threadId)
        .then((ctx) => {
          setThreadContext(ctx)
          if (seededContextForThreadRef.current !== threadId) {
            setComposerDraft(draftFromThreadContext(ctx))
            seededContextForThreadRef.current = threadId
          }
        })
        .catch(() => setThreadContext(null))

      void getCommunicationsSettings()
        .then((cfg) => {
          const tplItems = Array.isArray((cfg as any)?.messageTemplates?.items)
            ? (cfg as any).messageTemplates.items
            : []
          const nextTemplates = tplItems
            .filter((x: any) => x && x.enabled && (x.target === 'email' || x.target === 'both'))
            .map((x: any) => ({
              id: String(x.id || ''),
              label: String(x.label || ''),
              body: String(x.body || ''),
            }))
            .filter((x: any) => x.id && x.label)
          setTemplates(nextTemplates)
          setSelectedTemplateId((prev) => prev || (nextTemplates[0]?.id ?? ''))
        })
        .catch(() => undefined)
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.communications.errors.load'))) {
        setThreadError(getFriendlyErrorInfo(err, t('app.communications.errors.load'), t))
      }
      setLoading(false)
    }
  }, [planLimitModal, t, threadId])

  useEffect(() => {
    void load()
  }, [load, opts?.reloadSignal])

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
    [messages],
  )

  const applyCommandResult = useCallback((result: WorkspaceCommandResult) => {
    const ctx = result.context
    setThreadContext(ctx)
    setThread((prev) =>
      prev
        ? {
            ...prev,
            assignee_id: ctx.work_state?.assignee_id ?? prev.assignee_id,
            unread_count: ctx.work_state?.unread_count ?? prev.unread_count,
            is_archived: ctx.work_state?.is_archived ?? prev.is_archived,
            status: ctx.identity?.thread?.status || prev.status,
            subject: ctx.identity?.thread?.subject ?? prev.subject,
            channel: ctx.identity?.thread?.channel || prev.channel,
            priority: ctx.work_state?.priority || prev.priority,
            tags_json: Array.isArray(ctx.work_state?.tags_json)
              ? ctx.work_state.tags_json
              : prev.tags_json,
            thread_meta: ctx.work_state?.thread_meta || prev.thread_meta,
            linked_candidate_id: ctx.work_state?.linked_candidate_id ?? prev.linked_candidate_id,
            linked_company_id: ctx.work_state?.linked_company_id ?? prev.linked_company_id,
            sla_due_at: ctx.work_state?.sla_due_at ?? prev.sla_due_at,
          }
        : prev,
    )
  }, [])

  const handleMarkRead = useCallback(async () => {
    if (!threadId) return
    setBusyAction('read')
    try {
      const result = await executeWorkspaceCommand(threadId, 'MarkThreadRead')
      applyCommandResult(result)
      setMessages((prev) =>
        prev.map((m) =>
          m.direction === 'inbound' && !m.read_at
            ? { ...m, read_at: new Date().toISOString(), delivery_status: m.delivery_status === 'delivered' ? 'read' : m.delivery_status }
            : m,
        ),
      )
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.communications.errors.mark_read'))) {
        setThreadError(getFriendlyErrorInfo(err, t('app.communications.errors.mark_read'), t))
      }
    } finally {
      setBusyAction(null)
    }
  }, [applyCommandResult, planLimitModal, t, threadId])

  const handleAutoAssign = useCallback(async () => {
    if (!threadId) return
    setBusyAction('assign')
    try {
      const result = await autoAssignCommunicationThread(threadId)
      setThread(result.thread)
      if (!result.assigned) {
        setThreadError(
          friendlyFormHintError(
            t('app.communications.queue.auto_assign_failed', {
              values: { reason: result.reason || 'no_eligible_managers' },
            }),
            t,
          ),
        )
      } else {
        setThreadError(null)
      }
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.communications.errors.auto_assign'))) {
        setThreadError(getFriendlyErrorInfo(err, t('app.communications.errors.auto_assign'), t))
      }
    } finally {
      setBusyAction(null)
    }
  }, [planLimitModal, t, threadId])

  const handleSend = useCallback(
    async (e: FormEvent) => {
      e.preventDefault()
      if (!threadId || !thread) return
      if (!composerDraft.text.trim()) return
      const hints = threadContext?.workspace?.ui_hints
      if (threadContext && hints && hints.can_compose === false) return
      const channel = String(
        composerDraft.channel ||
          threadContext?.capabilities?.defaults?.channel ||
          thread.channel ||
          '',
      ).toLowerCase()
      const allowedChannels = threadContext?.capabilities?.allowed_channels || []
      if (threadContext && allowedChannels.length > 0 && !allowedChannels.includes(channel)) return
      const allowedIntents = threadContext?.capabilities?.allowed_intents || []
      if (
        threadContext &&
        !composerDraft.internalNote &&
        allowedIntents.length > 0 &&
        composerDraft.intent &&
        !allowedIntents.includes(composerDraft.intent)
      ) {
        return
      }
      setSending(true)
      try {
        const baseText = composerDraft.text.trim()
        const bodyText =
          !composerDraft.internalNote && channel === 'email' && composerDraft.applySignature
            ? appendSignature(baseText)
            : baseText
        const msg = await createCommunicationMessage(threadId, {
          direction: composerDraft.internalNote ? 'system' : 'outbound',
          message_type: composerDraft.internalNote ? 'note' : channel === 'email' ? 'email' : 'text',
          subject:
            channel === 'email' && !composerDraft.internalNote
              ? composerDraft.subject.trim() || undefined
              : undefined,
          body_text: bodyText,
          sender_type: 'user',
          recipient_address: !composerDraft.internalNote
            ? composerDraft.recipientAddress.trim() || undefined
            : undefined,
          delivery_status: composerDraft.internalNote ? 'sent' : 'queued',
          is_internal_note: composerDraft.internalNote,
          // Selection only — backend re-applies policy (authority).
          intent: composerDraft.internalNote ? undefined : composerDraft.intent || undefined,
        })
        let finalMsg = msg
        if (!composerDraft.internalNote && composerDraft.sendImmediately) {
          try {
            const dispatched = await dispatchCommunicationMessage(msg.id, { mark_delivered: true })
            finalMsg = dispatched.message
            setThread(dispatched.thread)
            if (!dispatched.dispatched) {
              setThreadError(
                friendlyFormHintError(
                  communicationPipelineReasonMessage(
                    dispatched.reason || dispatched.message.error_message,
                    t,
                  ),
                  t,
                ),
              )
            } else {
              setThreadError(null)
              if (!firstEmailTtvSentRef.current && channel === 'email') {
                firstEmailTtvSentRef.current = true
                void recordTtvStepCompleted({
                  event: 'ttv_step',
                  action: 'completed',
                  step_key: 'first_email_sent',
                })
              }
            }
          } catch (err: any) {
            if (
              !planLimitModal?.showPlanLimitIfNeeded(err, t('app.communications.email.dispatch_failed'))
            ) {
              setThreadError(
                commsErr(err, t('app.communications.email.dispatch_failed'), t, {
                  to: CRM_APP_PATHS.settingsEmail,
                  label: t('app.settings.email.title'),
                }),
              )
            }
          }
        } else {
          setThreadError(null)
        }
        setMessages((prev) => [...prev, finalMsg])
        setThread((prev) =>
          prev
            ? {
                ...prev,
                last_message_at: finalMsg.created_at,
                last_outbound_at: finalMsg.created_at,
                last_message_preview: finalMsg.body_text || finalMsg.subject || prev.last_message_preview,
                subject:
                  channel === 'email' && composerDraft.subject.trim()
                    ? composerDraft.subject.trim()
                    : prev.subject,
              }
            : prev,
        )
        patchComposerDraft({ text: '' })
      } catch (err: any) {
        const emailCh = String(thread?.channel || '').toLowerCase() === 'email'
        if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.communications.errors.send'))) {
          setThreadError(
            commsErr(err, t('app.communications.errors.send'), t, {
              to: emailCh ? CRM_APP_PATHS.settingsEmail : threadListPath,
              label: emailCh ? t('app.settings.email.title') : t('app.communications.actions.back_to_hub'),
            }),
          )
        }
      } finally {
        setSending(false)
      }
    },
    [
      appendSignature,
      composerDraft,
      patchComposerDraft,
      planLimitModal,
      t,
      thread,
      threadContext,
      threadId,
      threadListPath,
    ],
  )

  const handleDispatchQueued = useCallback(async () => {
    if (!thread) return
    setDispatchingQueued(true)
    try {
      const result = await dispatchQueuedCommunicationMessages({ limit: 50, channel: thread.channel, mark_delivered: true })
      const byId = new Map(result.items.map((x) => [x.message.id, x.message]))
      setMessages((prev) => prev.map((m) => byId.get(m.id) || m))
      const threadItem = result.items.find((x) => x.thread.id === thread.id)?.thread
      if (threadItem) setThread(threadItem)
      setThreadError(null)
    } catch (err: any) {
      const emailCh = String(thread.channel || '').toLowerCase() === 'email'
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.communications.errors.dispatch_queued'))) {
        setThreadError(
          commsErr(err, t('app.communications.errors.dispatch_queued'), t, {
            to: emailCh ? CRM_APP_PATHS.settingsEmail : threadListPath,
            label: emailCh ? t('app.settings.email.title') : t('app.communications.actions.back_to_hub'),
          }),
        )
      }
    } finally {
      setDispatchingQueued(false)
    }
  }, [planLimitModal, t, thread, threadListPath])

  const handleDispatchOne = useCallback(
    async (messageId: string) => {
      setDispatchingMessageId(messageId)
      try {
        const result = await dispatchCommunicationMessage(messageId, { mark_delivered: true })
        setMessages((prev) => prev.map((m) => (m.id === messageId ? result.message : m)))
        setThread(result.thread)
        if (!result.dispatched) {
          setThreadError(
            friendlyFormHintError(
              communicationPipelineReasonMessage(result.reason || result.message.error_message, t),
              t,
            ),
          )
        } else {
          setThreadError(null)
          if (!firstEmailTtvSentRef.current && String(result.thread.channel || '').toLowerCase() === 'email') {
            firstEmailTtvSentRef.current = true
            void recordTtvStepCompleted({
              event: 'ttv_step',
              action: 'completed',
              step_key: 'first_email_sent',
            })
          }
        }
      } catch (err: any) {
        const emailCh = String(thread?.channel || '').toLowerCase() === 'email'
        if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.communications.errors.dispatch_one'))) {
          setThreadError(
            commsErr(err, t('app.communications.errors.dispatch_one'), t, {
              to: emailCh ? CRM_APP_PATHS.settingsEmail : threadListPath,
              label: emailCh ? t('app.settings.email.title') : t('app.communications.actions.back_to_hub'),
            }),
          )
        }
      } finally {
        setDispatchingMessageId(null)
      }
    },
    [planLimitModal, t, thread, threadListPath],
  )

  return {
    thread,
    threadContext,
    messages,
    loading,
    threadError,
    busyAction,
    sending,
    dispatchingQueued,
    dispatchingMessageId,
    openActionMenu,
    setOpenActionMenu,
    workflowMenuRef,
    deliveryMenuRef,
    composerDraft,
    patchComposerDraft,
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
    threadListPath,
    threadUnlinked,
    inferredSignature,
    sortedMessages,
    load,
    applyCommandResult,
    handleMarkRead,
    handleAutoAssign,
    handleSend,
    handleDispatchQueued,
    handleDispatchOne,
  }
}
