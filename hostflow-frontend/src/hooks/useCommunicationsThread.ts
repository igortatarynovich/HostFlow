import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  autoAssignCommunicationThread,
  createCommunicationMessage,
  dispatchCommunicationMessage,
  dispatchQueuedCommunicationMessages,
  getCommunicationThread,
  getCommunicationsSettings,
  markCommunicationThreadRead,
  type CommunicationMessage,
  type CommunicationThread,
} from '../api/communications'
import { recordTtvStepCompleted } from '../api/analytics'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'
import { isCommunicationThreadUnlinked } from '../utils/communicationThreadUnlinked'
import { communicationApiTranslatedDetail } from '../utils/communicationApiTranslatedDetail'
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
  const [draftText, setDraftText] = useState('')
  const [draftSubject, setDraftSubject] = useState('')
  const [recipientAddress, setRecipientAddress] = useState('')
  const [internalNote, setInternalNote] = useState(false)
  const [sendImmediately, setSendImmediately] = useState(true)
  const [templates, setTemplates] = useState<Array<{ id: string; label: string; body: string }>>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('')
  const [applySignature, setApplySignature] = useState(true)
  const firstEmailTtvSentRef = useRef(false)

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
      setMessages([])
      return
    }
    setLoading(true)
    setThreadError(null)
    try {
      const [data, cfg] = await Promise.all([
        getCommunicationThread(threadId, { messagesLimit: 200 }),
        getCommunicationsSettings().catch(() => null),
      ])
      setThread(data.thread)
      setMessages(Array.isArray(data.messages) ? data.messages : [])
      if (!draftSubject) setDraftSubject(data.thread.subject || '')
      const tplItems = Array.isArray((cfg as any)?.messageTemplates?.items) ? (cfg as any).messageTemplates.items : []
      const nextTemplates = tplItems
        .filter((x: any) => x && x.enabled && (x.target === 'email' || x.target === 'both'))
        .map((x: any) => ({ id: String(x.id || ''), label: String(x.label || ''), body: String(x.body || '') }))
        .filter((x: any) => x.id && x.label)
      setTemplates(nextTemplates)
      if (!selectedTemplateId && nextTemplates.length) setSelectedTemplateId(nextTemplates[0].id)
    } catch (err: any) {
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.communications.errors.load'))) {
        setThreadError(getFriendlyErrorInfo(err, t('app.communications.errors.load'), t))
      }
    } finally {
      setLoading(false)
    }
  }, [draftSubject, planLimitModal, selectedTemplateId, t, threadId])

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
  }, [planLimitModal, t, threadId])

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
      if (!draftText.trim()) return
      setSending(true)
      try {
        const baseText = draftText.trim()
        const bodyText =
          !internalNote && String(thread.channel || '').toLowerCase() === 'email' && applySignature
            ? appendSignature(baseText)
            : baseText
        const msg = await createCommunicationMessage(threadId, {
          direction: internalNote ? 'system' : 'outbound',
          message_type: internalNote ? 'note' : thread.channel === 'email' ? 'email' : 'text',
          subject: thread.channel === 'email' && !internalNote ? draftSubject.trim() || undefined : undefined,
          body_text: bodyText,
          sender_type: internalNote ? 'user' : 'user',
          recipient_address: !internalNote ? recipientAddress.trim() || undefined : undefined,
          delivery_status: internalNote ? 'sent' : 'queued',
          is_internal_note: internalNote,
        })
        let finalMsg = msg
        if (!internalNote && sendImmediately) {
          try {
            const dispatched = await dispatchCommunicationMessage(msg.id, { mark_delivered: true })
            finalMsg = dispatched.message
            setThread(dispatched.thread)
            setThreadError(null)
            if (!firstEmailTtvSentRef.current && String(thread.channel || '').toLowerCase() === 'email') {
              firstEmailTtvSentRef.current = true
              void recordTtvStepCompleted({
                event: 'ttv_step',
                action: 'completed',
                step_key: 'first_email_sent',
              })
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
                subject: thread.channel === 'email' && draftSubject.trim() ? draftSubject.trim() : prev.subject,
              }
            : prev,
        )
        setDraftText('')
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
      applySignature,
      draftSubject,
      draftText,
      internalNote,
      planLimitModal,
      recipientAddress,
      sendImmediately,
      t,
      thread,
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
        setThreadError(null)
        if (!firstEmailTtvSentRef.current && String(result.thread.channel || '').toLowerCase() === 'email') {
          firstEmailTtvSentRef.current = true
          void recordTtvStepCompleted({
            event: 'ttv_step',
            action: 'completed',
            step_key: 'first_email_sent',
          })
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
    handleMarkRead,
    handleAutoAssign,
    handleSend,
    handleDispatchQueued,
    handleDispatchOne,
  }
}
