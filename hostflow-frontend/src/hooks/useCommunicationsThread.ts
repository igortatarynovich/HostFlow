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
import { isCommunicationThreadUnlinked } from '../utils/communicationThreadUnlinked'
import { communicationApiTranslatedDetail } from '../utils/communicationApiTranslatedDetail'

export function errorTextFromThread(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const msg = detail.map((x) => (typeof x?.msg === 'string' ? x.msg : null)).filter(Boolean).join('; ')
    if (msg) return msg
  }
  if (detail && typeof detail === 'object') {
    if (typeof detail.msg === 'string' && detail.msg.trim()) return detail.msg
    try {
      return JSON.stringify(detail)
    } catch {
      /* ignore */
    }
  }
  if (typeof err?.message === 'string' && err.message.trim()) return err.message
  return fallback
}

export type UseCommunicationsThreadOptions = {
  /** Override list path for error recovery links (e.g. `/app/inbox` in Communication Center). */
  backListPathOverride?: string
  /** Bump to refetch thread/messages when the parent list refreshed the same `threadId` (e.g. Messages/Email workspace). */
  reloadSignal?: number
}

export function useCommunicationsThread(threadId: string, opts?: UseCommunicationsThreadOptions) {
  const { t } = useI18n()
  const [thread, setThread] = useState<CommunicationThread | null>(null)
  const [messages, setMessages] = useState<CommunicationMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [errorText, setErrorText] = useState<string | null>(null)
  const [errorSecondaryTo, setErrorSecondaryTo] = useState<string | null>(null)
  const [errorSecondaryLabel, setErrorSecondaryLabel] = useState<string | null>(null)
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
  const [signatureCandidates, setSignatureCandidates] = useState<string>('')
  const [signatureClients, setSignatureClients] = useState<string>('')
  const [applySignature, setApplySignature] = useState(true)
  const firstEmailTtvSentRef = useRef(false)

  const threadListPath = useMemo(() => {
    if (opts?.backListPathOverride) return opts.backListPathOverride
    const email = String(thread?.channel || '').toLowerCase() === 'email'
    return email ? '/app/inbox?channel=email' : '/app/inbox?channel=messages'
  }, [opts?.backListPathOverride, thread?.channel])

  const threadUnlinked = useMemo(() => Boolean(thread && isCommunicationThreadUnlinked(thread)), [thread])

  const inferredSignature = useMemo(() => {
    if (!thread || String(thread.channel || '').toLowerCase() !== 'email') return ''
    const hasCompany = Boolean(thread.linked_company_id) || String(thread.entity_type || '').toLowerCase().includes('company')
    const raw = hasCompany ? signatureClients : signatureCandidates
    return String(raw || '').trim()
  }, [signatureCandidates, signatureClients, thread])

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
    setErrorText(null)
    setErrorSecondaryTo(null)
    setErrorSecondaryLabel(null)
    try {
      const [data, cfg] = await Promise.all([
        getCommunicationThread(threadId, { messagesLimit: 200 }),
        getCommunicationsSettings().catch(() => null),
      ])
      setThread(data.thread)
      setMessages(Array.isArray(data.messages) ? data.messages : [])
      if (!draftSubject) setDraftSubject(data.thread.subject || '')
      const emailCfg = (cfg as any)?.email || {}
      setSignatureCandidates(String(emailCfg.signatureCandidates || '').trim())
      setSignatureClients(String(emailCfg.signatureClients || '').trim())
      const tplItems = Array.isArray((cfg as any)?.messageTemplates?.items) ? (cfg as any).messageTemplates.items : []
      const nextTemplates = tplItems
        .filter((x: any) => x && x.enabled && (x.target === 'email' || x.target === 'both'))
        .map((x: any) => ({ id: String(x.id || ''), label: String(x.label || ''), body: String(x.body || '') }))
        .filter((x: any) => x.id && x.label)
      setTemplates(nextTemplates)
      if (!selectedTemplateId && nextTemplates.length) setSelectedTemplateId(nextTemplates[0].id)
    } catch (err: any) {
      setErrorText(errorTextFromThread(err, t('app.communications.errors.load', { defaultValue: 'Failed to load communications data' })))
    } finally {
      setLoading(false)
    }
  }, [draftSubject, selectedTemplateId, t, threadId])

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
      setErrorText(errorTextFromThread(err, t('app.communications.errors.load', { defaultValue: 'Failed to mark thread as read' })))
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
          }),
        )
      } else {
        setErrorText(null)
      }
    } catch (err: any) {
      setErrorText(errorTextFromThread(err, t('app.communications.errors.load', { defaultValue: 'Failed to auto-assign thread' })))
    } finally {
      setBusyAction(null)
    }
  }, [t, threadId])

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
            setErrorSecondaryTo(null)
            setErrorSecondaryLabel(null)
            if (!firstEmailTtvSentRef.current && String(thread.channel || '').toLowerCase() === 'email') {
              firstEmailTtvSentRef.current = true
              void recordTtvStepCompleted({
                event: 'ttv_step',
                action: 'completed',
                step_key: 'first_email_sent',
              })
            }
          } catch (err: any) {
            setErrorText(
              communicationApiTranslatedDetail(err, t) ??
                errorTextFromThread(
                  err,
                  t('app.communications.email.dispatch_failed', { defaultValue: 'Email is queued but dispatch failed.' }),
                ),
            )
            setErrorSecondaryTo('/app/settings/email')
            setErrorSecondaryLabel(t('app.settings.email.title', { defaultValue: 'Email settings' }))
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
            : prev,
        )
        setDraftText('')
        if (!errorSecondaryTo) setErrorText(null)
      } catch (err: any) {
        setErrorText(
          communicationApiTranslatedDetail(err, t) ??
            errorTextFromThread(err, t('app.communications.errors.load', { defaultValue: 'Failed to send message' })),
        )
        setErrorSecondaryTo(String(thread?.channel || '').toLowerCase() === 'email' ? '/app/settings/email' : threadListPath)
        setErrorSecondaryLabel(
          String(thread?.channel || '').toLowerCase() === 'email'
            ? t('app.settings.email.title', { defaultValue: 'Email settings' })
            : t('app.communications.actions.back_to_hub', { defaultValue: 'Back to inbox' }),
        )
      } finally {
        setSending(false)
      }
    },
    [
      appendSignature,
      applySignature,
      draftSubject,
      draftText,
      errorSecondaryTo,
      internalNote,
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
      setErrorText(null)
      setErrorSecondaryTo(null)
      setErrorSecondaryLabel(null)
    } catch (err: any) {
      setErrorText(
        communicationApiTranslatedDetail(err, t) ??
          errorTextFromThread(err, t('app.communications.errors.load', { defaultValue: 'Failed to dispatch queued messages' })),
      )
      setErrorSecondaryTo(String(thread.channel || '').toLowerCase() === 'email' ? '/app/settings/email' : threadListPath)
      setErrorSecondaryLabel(
        String(thread.channel || '').toLowerCase() === 'email'
          ? t('app.settings.email.title', { defaultValue: 'Email settings' })
          : t('app.communications.actions.back_to_hub', { defaultValue: 'Back to inbox' }),
      )
    } finally {
      setDispatchingQueued(false)
    }
  }, [t, thread, threadListPath])

  const handleDispatchOne = useCallback(
    async (messageId: string) => {
      setDispatchingMessageId(messageId)
      try {
        const result = await dispatchCommunicationMessage(messageId, { mark_delivered: true })
        setMessages((prev) => prev.map((m) => (m.id === messageId ? result.message : m)))
        setThread(result.thread)
        setErrorText(null)
        setErrorSecondaryTo(null)
        setErrorSecondaryLabel(null)
        if (!firstEmailTtvSentRef.current && String(result.thread.channel || '').toLowerCase() === 'email') {
          firstEmailTtvSentRef.current = true
          void recordTtvStepCompleted({
            event: 'ttv_step',
            action: 'completed',
            step_key: 'first_email_sent',
          })
        }
      } catch (err: any) {
        setErrorText(
          communicationApiTranslatedDetail(err, t) ??
            errorTextFromThread(err, t('app.communications.errors.load', { defaultValue: 'Failed to dispatch message' })),
        )
        setErrorSecondaryTo(String(thread?.channel || '').toLowerCase() === 'email' ? '/app/settings/email' : threadListPath)
        setErrorSecondaryLabel(
          String(thread?.channel || '').toLowerCase() === 'email'
            ? t('app.settings.email.title', { defaultValue: 'Email settings' })
            : t('app.communications.actions.back_to_hub', { defaultValue: 'Back to inbox' }),
        )
      } finally {
        setDispatchingMessageId(null)
      }
    },
    [t, thread, threadListPath],
  )

  return {
    thread,
    messages,
    loading,
    errorText,
    errorSecondaryTo,
    errorSecondaryLabel,
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
