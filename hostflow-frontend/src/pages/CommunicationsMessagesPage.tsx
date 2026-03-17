import { useEffect, useMemo, useRef, useState } from 'react'
import clsx from 'clsx'
import { useSearchParams } from 'react-router-dom'
import { IconPinned } from '@tabler/icons-react'
import { api } from '../api/client'
import {
  createCommunicationMessage,
  createCommunicationPlannerEvent,
  getCommunicationsSettings,
  dispatchCommunicationMessage,
  listCommunicationMessageTemplates,
  listCommunicationMessages,
  listCommunicationThreads,
  markCommunicationThreadRead,
  patchCommunicationThread,
  reconcileCommunicationThreadUnread,
  type CommunicationMessage,
  type CommunicationThread,
} from '../api/communications'
import { searchCandidates } from '../api/candidates'
import type { Candidate } from '../api/types'
import { patchUserMe } from '../api/users'
import { listTenantManagers } from '../api/users'
import type { ManagerOption } from '../api/types'
import { useI18n } from '../i18n'
import { useAuth } from '../store/auth'
import {
  noReplyNeededFromThread,
  opsModeFromThread,
  opsModeLabel,
  slaMutedFromThread,
  slaSnoozedUntilFromThread,
  type CommunicationOpsMode,
} from '../utils/communicationsOpsMode'
import EmptyStatePanel from '../components/EmptyStatePanel'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import WorkspaceTopNav from '../components/communications/WorkspaceTopNav'

const LS_KEY = 'hf:messages-chat:v1'
const QUICK_EMOJIS = ['👍', '✅', '📞', '📄', '🙏']
const DEFAULT_ESCALATION_ROLE_OPTIONS = ['supervisor', 'admin', 'manager'] as const
const DEFAULT_ESCALATION_QUEUE_OPTIONS = ['priority', 'manual_review', 'supervisor_desk'] as const
const DEFAULT_QUICK_TEMPLATES = [
  'Hello! Thank you for your message.',
  'Please confirm you received this update.',
  'We will call you shortly.',
  'Please send the requested documents.',
]
const TAG_COLORS = ['#0284c7', '#0891b2', '#0f766e', '#15803d', '#ca8a04', '#c2410c', '#be123c', '#7c3aed', '#475569']

type PersonalTag = { name: string; color: string; archived?: boolean }
type OpsMode = CommunicationOpsMode
type OpsModeFilter = 'all' | OpsMode

function errorTextFrom(err: any, fallback: string) {
  const status = Number(err?.response?.status || 0)
  const code = String(err?.code || '').trim().toUpperCase()
  const offline = typeof navigator !== 'undefined' && navigator?.onLine === false
  if (offline || code === 'ERR_NETWORK') {
    return 'No internet connection. Check network and retry.'
  }
  if (code === 'ECONNABORTED') {
    return 'Request timed out. Retry in a few seconds.'
  }
  if (status === 401 || status === 403) {
    return 'Access denied for this action. Refresh session or contact admin.'
  }
  if (status === 429) {
    return 'Too many requests. Wait a moment and retry.'
  }
  if (status >= 500) {
    return 'Service is temporarily unavailable. Please retry shortly.'
  }
  const d = err?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    const msg = d.map((x) => (typeof x?.msg === 'string' ? x.msg : null)).filter(Boolean).join('; ')
    if (msg) return msg
  }
  if (d && typeof d === 'object') {
    if (typeof d.msg === 'string') return d.msg
    try {
      return JSON.stringify(d)
    } catch {
      // ignore
    }
  }
  return err?.message || fallback
}

function dt(value?: string | null): number {
  if (!value) return 0
  const t = Date.parse(value)
  return Number.isNaN(t) ? 0 : t
}

function formatDateTime(value?: string | null): string {
  const ts = dt(value)
  if (!ts) return '—'
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(ts))
}

function formatDateOnly(value?: string | null): string {
  const ts = dt(value)
  if (!ts) return ''
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(ts))
}

function dayKey(value?: string | null): string {
  const ts = dt(value)
  if (!ts) return ''
  const d = new Date(ts)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function deliveryLabel(status?: string | null): string {
  const s = String(status || '').toLowerCase()
  if (s === 'read') return 'Read'
  if (s === 'delivered') return 'Delivered'
  if (s === 'sent') return 'Sent'
  if (s === 'queued') return 'Queued'
  if (s === 'failed') return 'Failed'
  return s || 'Sent'
}

function tagsOf(th: CommunicationThread): string[] {
  return (Array.isArray(th.tags_json) ? th.tags_json : []).map((x) => String(x || '').trim()).filter(Boolean)
}

const noReplyNeededOf = noReplyNeededFromThread
const opsModeOf = opsModeFromThread
const slaSnoozedUntilOf = slaSnoozedUntilFromThread
const slaMutedOf = slaMutedFromThread

function isTelegramCommandMessage(msg: CommunicationMessage): boolean {
  if (String(msg.channel || '').toLowerCase() !== 'telegram') return false
  const payload = (msg.payload || {}) as Record<string, any>
  if (payload.telegram_command) return true
  const text = String(msg.body_text || '').trim()
  return text.startsWith('/')
}

function hasUnreadInbound(rows: CommunicationMessage[]): boolean {
  return rows.some((msg) => msg.direction === 'inbound' && !msg.read_at && !isTelegramCommandMessage(msg))
}

function titleOf(th: CommunicationThread): string {
  const subject = String(th.subject || '').trim()
  if (subject) return subject
  const preview = String(th.last_message_preview || '').trim()
  if (preview) return preview
  return `${String(th.channel || '').toUpperCase()} thread`
}

function inferThreadRecipient(th: CommunicationThread | null): string {
  if (!th) return ''
  const participants = (th.participants_json || {}) as Record<string, any>
  const meta = (th.thread_meta || {}) as Record<string, any>
  const candidates = [
    participants.recipient,
    participants.recipient_address,
    participants.contact,
    participants.phone,
    participants.email,
    participants.username,
    meta.recipient,
    meta.recipient_address,
    meta.phone,
    meta.email,
    meta.channel_user_id,
    meta.channel_account_id,
  ]
  for (const raw of candidates) {
    const normalized = String(raw || '').trim()
    if (normalized) return normalized
  }
  return ''
}

function textOf(msg: CommunicationMessage): string {
  const text = String(msg.body_text || '').trim()
  if (text) return text
  const html = String(msg.body_html || '').replace(/<[^>]+>/g, ' ').trim()
  if (html) return html
  return '—'
}

function candidateLabel(candidate: Candidate): string {
  const first = String(candidate.first_name || '').trim()
  const last = String(candidate.last_name || '').trim()
  const full = [first, last].filter(Boolean).join(' ').trim()
  const short = String(candidate.short_id || '').trim()
  if (full && short) return `${full} (${short})`
  if (full) return full
  if (short) return short
  return String(candidate.id || '')
}

export default function CommunicationsMessagesPage() {
  const { t } = useI18n()
  const { me, preferences, updatePreferences } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const saved = useMemo(() => {
    try {
      const raw = window.localStorage.getItem(LS_KEY)
      return raw ? JSON.parse(raw) : {}
    } catch {
      return {}
    }
  }, [])

  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [errorText, setErrorText] = useState<string | null>(null)

  const [threads, setThreads] = useState<CommunicationThread[]>([])
  const [q, setQ] = useState(String(saved.q || ''))
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(searchParams.get('threadId'))

  const [messages, setMessages] = useState<CommunicationMessage[]>([])
  const [messagesLoading, setMessagesLoading] = useState(false)

  const [managerOptions, setManagerOptions] = useState<ManagerOption[]>([])
  const [assigneeDraft, setAssigneeDraft] = useState('')
  const [quickTag, setQuickTag] = useState('')
  const [candidateQuery, setCandidateQuery] = useState('')
  const [candidateResults, setCandidateResults] = useState<Candidate[]>([])
  const [candidatePickId, setCandidatePickId] = useState('')
  const [candidateSearching, setCandidateSearching] = useState(false)
  const [personalTags, setPersonalTags] = useState<PersonalTag[]>([])
  const [tagPick, setTagPick] = useState('')
  const [newTagName, setNewTagName] = useState('')
  const [newTagColor, setNewTagColor] = useState(TAG_COLORS[0])
  const [tagManagerOpen, setTagManagerOpen] = useState(false)
  const [dragThreadId, setDragThreadId] = useState<string | null>(null)
  const [activeToolsPanel, setActiveToolsPanel] = useState<'manager' | 'tags' | 'candidate' | null>(null)
  const [candidateNamesById, setCandidateNamesById] = useState<Record<string, string>>({})
  const [quickTemplates, setQuickTemplates] = useState<string[]>(DEFAULT_QUICK_TEMPLATES)
  const [opsModeFilter, setOpsModeFilter] = useState<OpsModeFilter>('all')

  const [taskModalOpen, setTaskModalOpen] = useState(false)
  const [taskTitle, setTaskTitle] = useState('')
  const [taskAt, setTaskAt] = useState('')
  const [pauseModalOpen, setPauseModalOpen] = useState(false)
  const [pauseHoursDraft, setPauseHoursDraft] = useState('4')
  const [escalationModalOpen, setEscalationModalOpen] = useState(false)
  const [escalationReasonDraft, setEscalationReasonDraft] = useState('')
  const [escalationTargetTypeDraft, setEscalationTargetTypeDraft] = useState<'role' | 'queue' | 'user'>('role')
  const [escalationTargetValueDraft, setEscalationTargetValueDraft] = useState('supervisor')
  const [escalationRoleOptions, setEscalationRoleOptions] = useState<string[]>([...DEFAULT_ESCALATION_ROLE_OPTIONS])
  const [escalationQueueOptions, setEscalationQueueOptions] = useState<string[]>([...DEFAULT_ESCALATION_QUEUE_OPTIONS])

  const [replyRecipient, setReplyRecipient] = useState('')
  const [replyText, setReplyText] = useState('')
  const [userScrolledUp, setUserScrolledUp] = useState(false)
  const timelineRef = useRef<HTMLDivElement | null>(null)
  const threadsLoadInFlightRef = useRef(false)
  const messagesLoadInFlightRef = useRef(false)
  const markReadInFlightRef = useRef<Record<string, boolean>>({})
  const markReadLastCallAtRef = useRef<Record<string, number>>({})
  const [isMobile, setIsMobile] = useState(false)
  const [mobilePane, setMobilePane] = useState<'list' | 'chat'>('list')
  const [showMobileFilters, setShowMobileFilters] = useState(false)
  const [openActionMenu, setOpenActionMenu] = useState<null | 'workflow' | 'sla' | 'more'>(null)
  const [mobileToolsOpen, setMobileToolsOpen] = useState(false)
  const [quickRepliesOpen, setQuickRepliesOpen] = useState(false)
  const [showRecipientField, setShowRecipientField] = useState(false)
  const workflowMenuRef = useRef<HTMLDivElement | null>(null)
  const slaMenuRef = useRef<HTMLDivElement | null>(null)
  const moreMenuRef = useRef<HTMLDivElement | null>(null)

  const opsModeText = (mode: OpsMode | null): string => {
    if (!mode) return t('app.communications_messages.ops.none')
    return t(`app.communications_messages.ops.${mode}`)
  }

  const maybeTranslateKey = (value?: string | null): string => {
    const normalized = String(value || '').trim()
    if (!normalized) return ''
    if (/^(app|common)\./.test(normalized)) {
      const localized = t(normalized as any, { defaultValue: '' })
      if (localized && localized !== normalized) return localized
    }
    return normalized
  }

  const escalationApiErrorText = (err: any): string | null => {
    const detail = err?.response?.data?.detail
    const code = String(detail?.code || '').trim().toLowerCase()
    if (!code) return null
    if (code === 'ops_escalation_reason_required') {
      return t('app.communications_messages.ops.escalation_reason_required', { defaultValue: 'Escalation reason is required.' })
    }
    if (code === 'ops_escalation_target_required') {
      return t('app.communications_messages.ops.escalation_target_required', { defaultValue: 'Escalation target is required.' })
    }
    if (code === 'ops_escalation_target_unknown_queue') {
      const allowed = Array.isArray(detail?.allowed_targets)
        ? detail.allowed_targets.map((x: any) => String(x || '').trim()).filter(Boolean).join(', ')
        : ''
      return t('app.communications_messages.ops.escalation_error_unknown_queue', {
        defaultValue: allowed
          ? 'Selected queue is not allowed. Allowed queues: {allowed}.'
          : 'Selected queue is not allowed for this tenant.',
        values: { allowed },
      })
    }
    if (code === 'ops_escalation_target_invalid_role') {
      return t('app.communications_messages.ops.escalation_error_invalid_role', {
        defaultValue: 'Role target has invalid format.',
      })
    }
    if (code === 'ops_escalation_target_unknown_role') {
      const allowed = Array.isArray(detail?.allowed_roles)
        ? detail.allowed_roles.map((x: any) => String(x || '').trim()).filter(Boolean).join(', ')
        : ''
      return t('app.communications_messages.ops.escalation_error_unknown_role', {
        defaultValue: allowed
          ? 'Selected role is not allowed. Allowed roles: {allowed}.'
          : 'Selected role is not allowed for this tenant.',
        values: { allowed },
      })
    }
    if (code === 'ops_escalation_target_invalid_user_id') {
      return t('app.communications_messages.ops.escalation_error_invalid_user', {
        defaultValue: 'Selected user has invalid identifier.',
      })
    }
    if (code === 'ops_escalation_target_unknown_user') {
      return t('app.communications_messages.ops.escalation_error_unknown_user', {
        defaultValue: 'Selected user is inactive or belongs to another tenant.',
      })
    }
    return null
  }

  const loadThreads = async (silent = false) => {
    if (threadsLoadInFlightRef.current) return
    threadsLoadInFlightRef.current = true
    if (!silent) setLoading(true)
    setErrorText(null)
    try {
      const res = await listCommunicationThreads({ limit: 300, includeArchived: false })
      const items = (Array.isArray(res.items) ? res.items : [])
        .filter((th) => String(th.channel || '').toLowerCase() !== 'email')
        .filter((th) => !th.is_archived && String(th.status || '').toLowerCase() !== 'deleted')
      setThreads(items)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to load messages'))
    } finally {
      threadsLoadInFlightRef.current = false
      if (!silent) setLoading(false)
    }
  }

  const loadThreadMessages = async (threadId: string, silent = false) => {
    if (messagesLoadInFlightRef.current) return
    messagesLoadInFlightRef.current = true
    if (!silent) setMessagesLoading(true)
    try {
      const res = await listCommunicationMessages(threadId, { limit: 200 })
      const rows = Array.isArray(res.items) ? [...res.items] : []
      rows.sort((a, b) => dt(a.created_at) - dt(b.created_at))
      setMessages(rows)
      if (hasUnreadInbound(rows)) {
        void markThreadRead(threadId)
      }
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to load dialog messages'))
    } finally {
      messagesLoadInFlightRef.current = false
      if (!silent) setMessagesLoading(false)
    }
  }

  const markThreadRead = async (threadId: string, opts?: { force?: boolean }) => {
    const now = Date.now()
    const lastCallAt = Number(markReadLastCallAtRef.current[threadId] || 0)
    if (!opts?.force && now - lastCallAt < 4000) return
    if (markReadInFlightRef.current[threadId]) return

    let shouldCallApi = Boolean(opts?.force)
    setThreads((prev) => {
      const current = prev.find((x) => x.id === threadId)
      if (!current) return prev
      if (Number(current.unread_count || 0) > 0) shouldCallApi = true
      if (Number(current.unread_count || 0) <= 0) return prev
      return prev.map((x) => (x.id === threadId ? { ...x, unread_count: 0 } : x))
    })
    if (!shouldCallApi) return
    // Optimistic update: remove unread badge immediately.
    markReadInFlightRef.current[threadId] = true
    markReadLastCallAtRef.current[threadId] = now
    try {
      const updated = await markCommunicationThreadRead(threadId, { mark_thread: true })
      setThreads((prev) => prev.map((x) => (x.id === threadId ? { ...x, unread_count: Number(updated.unread_count || 0) } : x)))
    } catch {
      // Keep UI responsive; list poll will eventually sync value.
    } finally {
      markReadInFlightRef.current[threadId] = false
    }
  }

  useEffect(() => {
    let canceled = false
    ;(async () => {
      try {
        await reconcileCommunicationThreadUnread({ limit: 1000 })
      } catch {
        // ignore reconcile errors; normal loading still works
      }
      if (!canceled) await loadThreads()
    })()
    return () => {
      canceled = true
    }
  }, [])

  useEffect(() => {
    const raw = (preferences as any)?.ui?.messages_tags
    const normalized = Array.isArray(raw)
      ? raw
          .map((x: any) => ({
            name: String(x?.name || '').trim(),
            color: String(x?.color || '').trim(),
            archived: Boolean(x?.archived),
          }))
          .filter((x: PersonalTag) => x.name)
      : []
    setPersonalTags(normalized)
    const active = normalized.filter((x: PersonalTag) => !x.archived)
    if (active.length > 0) {
      setTagPick((prev) => (prev && active.some((x: PersonalTag) => x.name === prev) ? prev : active[0].name))
    } else {
      setTagPick('')
    }
  }, [preferences])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const rows = await listTenantManagers()
        if (mounted) setManagerOptions(Array.isArray(rows) ? rows : [])
      } catch {
        if (mounted) setManagerOptions([])
      }
    })()
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const settings = await getCommunicationsSettings()
        if (!mounted) return
        const roles = settings?.access?.roles
        const roleBag = new Set<string>()
        const keys: Array<keyof NonNullable<typeof roles>> = [
          'messages',
          'email',
          'calendar',
          'planner',
          'teamAvailability',
          'myAvailability',
          'timeOffRequests',
          'communicationsAdmin',
        ]
        for (const k of keys) {
          const arr = Array.isArray(roles?.[k]) ? roles?.[k] : []
          for (const role of arr || []) {
            const normalized = String(role || '').trim().toLowerCase()
            if (normalized) roleBag.add(normalized)
          }
        }
        const nextRoles = Array.from(roleBag)
        setEscalationRoleOptions(nextRoles.length ? nextRoles : [...DEFAULT_ESCALATION_ROLE_OPTIONS])
        const queueTargets = Array.isArray(settings?.sla?.escalationTargets)
          ? settings.sla.escalationTargets.map((x) => String(x || '').trim()).filter(Boolean)
          : []
        setEscalationQueueOptions(queueTargets.length ? queueTargets : [...DEFAULT_ESCALATION_QUEUE_OPTIONS])
      } catch {
        if (mounted) {
          setEscalationRoleOptions([...DEFAULT_ESCALATION_ROLE_OPTIONS])
          setEscalationQueueOptions([...DEFAULT_ESCALATION_QUEUE_OPTIONS])
        }
      }
    })()
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const res = await listCommunicationMessageTemplates({ target: 'messages' })
        const uid = String(me?.sub || '').trim()
        const rows = (Array.isArray(res.items) ? res.items : [])
          .filter((tpl) => tpl.enabled !== false)
          .filter((tpl) => tpl.visibility === 'company' || (tpl.visibility === 'private' && (!tpl.ownerUserId || String(tpl.ownerUserId) === uid)))
          .map((tpl) => maybeTranslateKey(String(tpl.body || '').trim()))
          .filter(Boolean)
        if (!mounted) return
        setQuickTemplates(rows.length ? rows : DEFAULT_QUICK_TEMPLATES)
      } catch {
        if (mounted) setQuickTemplates(DEFAULT_QUICK_TEMPLATES)
      }
    })()
    return () => {
      mounted = false
    }
  }, [me?.sub])

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_KEY, JSON.stringify({ q }))
    } catch {
      // ignore storage errors
    }
  }, [q])

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 1024px)')
    const apply = () => setIsMobile(Boolean(mq.matches))
    apply()
    mq.addEventListener('change', apply)
    return () => mq.removeEventListener('change', apply)
  }, [])

  const isPinned = (th: CommunicationThread): boolean => Boolean((th.thread_meta || {})?.ui_pinned)
  const orderOf = (th: CommunicationThread): number => {
    const raw = (th.thread_meta || {})?.ui_order
    const num = typeof raw === 'number' ? raw : Number(raw)
    return Number.isFinite(num) && num > 0 ? num : Number.MAX_SAFE_INTEGER
  }
  const activePersonalTags = useMemo(() => personalTags.filter((tag) => !tag.archived), [personalTags])
  const candidateFilterId = String(searchParams.get('candidateId') || '').trim()
  const personalTagColor = useMemo(() => {
    const map = new Map<string, string>()
    for (const tag of personalTags) map.set(tag.name.toLowerCase(), tag.color || TAG_COLORS[0])
    return map
  }, [personalTags])
  const managerLabelById = useMemo(() => {
    const map = new Map<string, string>()
    for (const m of managerOptions) map.set(String(m.id), String(m.label || m.full_name || m.email || m.id))
    return map
  }, [managerOptions])

  const displayTitle = (th: CommunicationThread): string => {
    const linkedId = String(th.linked_candidate_id || '').trim()
    if (linkedId) {
      const metaName = String((th.thread_meta || {})?.linked_candidate_name || '').trim()
      if (metaName) return metaName
      const fetched = String(candidateNamesById[linkedId] || '').trim()
      if (fetched) return fetched
    }
    return titleOf(th)
  }

  const primaryTagColor = (th: CommunicationThread): string | null => {
    const first = tagsOf(th)[0]
    if (!first) return null
    return personalTagColor.get(first.toLowerCase()) || null
  }

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return threads
      .filter((th) => (opsModeFilter === 'all' ? true : opsModeOf(th) === opsModeFilter))
      .filter((th) => (candidateFilterId ? String(th.linked_candidate_id || '') === candidateFilterId : true))
      .filter((th) => {
        if (!needle) return true
        const hay = [titleOf(th), th.last_message_preview, th.id, th.assignee_id, th.status, th.channel, tagsOf(th).join(' ')]
          .join(' ')
          .toLowerCase()
        return hay.includes(needle)
      })
      .sort((a, b) => {
        const ap = isPinned(a) ? 1 : 0
        const bp = isPinned(b) ? 1 : 0
        if (ap !== bp) return bp - ap
        const ao = orderOf(a)
        const bo = orderOf(b)
        if (ao !== bo) return ao - bo
        const ak = Math.max(dt(a.last_message_at), dt(a.updated_at))
        const bk = Math.max(dt(b.last_message_at), dt(b.updated_at))
        return bk - ak
      })
  }, [candidateFilterId, opsModeFilter, q, threads])

  useEffect(() => {
    const unread = threads.reduce((acc, th) => acc + Math.max(0, Number(th.unread_count || 0)), 0)
    window.dispatchEvent(
      new CustomEvent('hf:messages-unread-sync', {
        detail: { unread },
      }),
    )
  }, [threads])

  useEffect(() => {
    if (!filtered.length) {
      setSelectedThreadId(null)
      setMessages([])
      setMobilePane('list')
      return
    }
    if (!selectedThreadId || !filtered.some((x) => x.id === selectedThreadId)) {
      setSelectedThreadId(filtered[0].id)
    }
  }, [filtered, selectedThreadId])

  const selectedThread = useMemo(() => filtered.find((x) => x.id === selectedThreadId) || null, [filtered, selectedThreadId])
  const selectedThreadExists = useMemo(
    () => Boolean(selectedThreadId && threads.some((th) => th.id === selectedThreadId)),
    [selectedThreadId, threads],
  )

  useEffect(() => {
    if (!selectedThreadId) {
      setMessages([])
      setUserScrolledUp(false)
      return
    }
    // Guard against URL threadId loops when dialogs list is empty or not loaded yet.
    if (!selectedThreadExists) {
      return
    }
    void loadThreadMessages(selectedThreadId)
    // Force mark-read on open to avoid stale unread counter after refresh/race.
    void markThreadRead(selectedThreadId, { force: true })
  }, [selectedThreadId, selectedThreadExists])

  useEffect(() => {
    if (!selectedThread) return
    setAssigneeDraft(selectedThread.assignee_id || '')
    setReplyRecipient(inferThreadRecipient(selectedThread))
    setCandidateQuery('')
    setCandidatePickId('')
    setCandidateResults([])
    setActiveToolsPanel(null)
    setOpenActionMenu(null)
  }, [selectedThread])

  useEffect(() => {
    if (!openActionMenu) return
    const onPointerDown = (event: MouseEvent | TouchEvent) => {
      const target = event.target as Node | null
      const refs = [workflowMenuRef.current, slaMenuRef.current, moreMenuRef.current]
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

  useEffect(() => {
    const threadId = searchParams.get('threadId')
    if (!threadId || threadId === selectedThreadId) return
    // Apply URL selection only when thread is present in current list.
    if (threads.some((th) => th.id === threadId)) {
      setSelectedThreadId(threadId)
    }
  }, [searchParams, selectedThreadId, threads])

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.hidden) return
      void loadThreads(true)
      if (selectedThreadId) void loadThreadMessages(selectedThreadId, true)
    }, 15000)
    return () => window.clearInterval(timer)
  }, [selectedThreadId])

  useEffect(() => {
    if (!timelineRef.current) return
    if (!userScrolledUp) timelineRef.current.scrollTop = timelineRef.current.scrollHeight
  }, [messages, userScrolledUp])

  useEffect(() => {
    let canceled = false
    const run = async () => {
      const ids = Array.from(
        new Set(
          threads
            .map((th) => String(th.linked_candidate_id || '').trim())
            .filter(Boolean)
            .filter((id) => !candidateNamesById[id] && !String((threads.find((x) => String(x.linked_candidate_id || '') === id)?.thread_meta || {}).linked_candidate_name || '').trim()),
        ),
      ).slice(0, 40)
      if (!ids.length) return
      const pairs = await Promise.all(
        ids.map(async (id) => {
          try {
            const { data } = await api.get(`/candidates/${id}`)
            const item = data?.item || data
            const first = String(item?.first_name || '').trim()
            const last = String(item?.last_name || '').trim()
            const full = [first, last].filter(Boolean).join(' ').trim()
            return [id, full || String(item?.short_id || '').trim() || id] as const
          } catch {
            return [id, id] as const
          }
        }),
      )
      if (canceled) return
      setCandidateNamesById((prev) => {
        const next = { ...prev }
        for (const [id, name] of pairs) next[id] = name
        return next
      })
    }
    void run()
    return () => {
      canceled = true
    }
  }, [threads, candidateNamesById])

  const saveAssignee = async () => {
    if (!selectedThread) return
    setBusy(true)
    setErrorText(null)
    try {
      await patchCommunicationThread(selectedThread.id, { assignee_id: assigneeDraft || null })
      await loadThreads(true)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to update assignee'))
    } finally {
      setBusy(false)
    }
  }

  const savePersonalTags = async (next: PersonalTag[]) => {
    const filtered = next
      .map((x) => ({
        name: String(x.name || '').trim(),
        color: String(x.color || '').trim() || TAG_COLORS[0],
        archived: Boolean(x.archived),
      }))
      .filter((x) => x.name)
    const currentPrefs = preferences || ({} as any)
    const currentUi = ((currentPrefs as any).ui || {}) as Record<string, any>
    const updatedPrefs = {
      ...(currentPrefs as any),
      ui: {
        ...currentUi,
        messages_tags: filtered,
      },
    } as any
    await patchUserMe({
      preferences: {
        ui: {
          ...(currentUi || {}),
          messages_tags: filtered,
        },
      } as any,
    })
    updatePreferences(updatedPrefs)
    setPersonalTags(filtered)
    const active = filtered.filter((x) => !x.archived)
    if (active.length > 0) setTagPick((prev) => (prev && active.some((x) => x.name === prev) ? prev : active[0].name))
    else setTagPick('')
  }

  const createPersonalTag = async () => {
    const name = newTagName.trim()
    if (!name) return
    if (personalTags.some((x) => x.name.toLowerCase() === name.toLowerCase())) return
    setBusy(true)
    setErrorText(null)
    try {
      await savePersonalTags([...personalTags, { name, color: newTagColor || TAG_COLORS[0], archived: false }])
      setNewTagName('')
      setTagPick(name)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to save personal tags'))
    } finally {
      setBusy(false)
    }
  }

  const removePersonalTag = async (name: string) => {
    setBusy(true)
    setErrorText(null)
    try {
      await savePersonalTags(personalTags.filter((x) => x.name !== name))
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to delete personal tag'))
    } finally {
      setBusy(false)
    }
  }

  const updatePersonalTag = async (name: string, patch: Partial<PersonalTag>) => {
    setBusy(true)
    setErrorText(null)
    try {
      const next = personalTags.map((tag) => (tag.name === name ? { ...tag, ...patch } : tag))
      await savePersonalTags(next)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to update personal tag'))
    } finally {
      setBusy(false)
    }
  }

  const addQuickTag = async () => {
    if (!selectedThread) return
    const tag = quickTag.trim()
    if (!tag) return
    setBusy(true)
    setErrorText(null)
    try {
      const next = Array.from(new Set([...tagsOf(selectedThread), tag]))
      await patchCommunicationThread(selectedThread.id, { tags_json: next })
      setQuickTag('')
      await loadThreads(true)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to add tag'))
    } finally {
      setBusy(false)
    }
  }

  const addSelectedTag = async () => {
    if (!selectedThread) return
    const tag = String(tagPick || '').trim()
    if (!tag) return
    setBusy(true)
    setErrorText(null)
    try {
      const next = Array.from(new Set([...tagsOf(selectedThread), tag]))
      await patchCommunicationThread(selectedThread.id, { tags_json: next })
      await loadThreads(true)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to add tag'))
    } finally {
      setBusy(false)
    }
  }

  const removeThreadTag = async (tag: string) => {
    if (!selectedThread) return
    setBusy(true)
    setErrorText(null)
    try {
      const next = tagsOf(selectedThread).filter((x) => x !== tag)
      await patchCommunicationThread(selectedThread.id, { tags_json: next })
      await loadThreads(true)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to remove tag'))
    } finally {
      setBusy(false)
    }
  }

  const runCandidateSearch = async () => {
    const q = candidateQuery.trim()
    if (q.length < 2) {
      setCandidateResults([])
      setCandidatePickId('')
      return
    }
    setCandidateSearching(true)
    setErrorText(null)
    try {
      const rows = await searchCandidates({ q, limit: 15 })
      const list = Array.isArray(rows) ? rows : []
      setCandidateResults(list)
      const firstId = list[0]?.id ? String(list[0].id) : ''
      setCandidatePickId((prev) => (prev && list.some((x) => String(x.id) === prev) ? prev : firstId))
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to search candidates'))
    } finally {
      setCandidateSearching(false)
    }
  }

  const bindCandidate = async (candidateId: string | null) => {
    if (!selectedThread) return
    setBusy(true)
    setErrorText(null)
    try {
      const selectedCandidate =
        candidateId && candidateResults.length
          ? candidateResults.find((c) => String(c.id) === String(candidateId))
          : null
      const linkedName = selectedCandidate
        ? [String(selectedCandidate.first_name || '').trim(), String(selectedCandidate.last_name || '').trim()].filter(Boolean).join(' ').trim()
        : ''
      const nextMeta = {
        ...(selectedThread.thread_meta || {}),
        linked_candidate_name: candidateId ? linkedName || undefined : null,
      }
      await patchCommunicationThread(selectedThread.id, {
        linked_candidate_id: candidateId,
        thread_meta: nextMeta,
      })
      if (candidateId && linkedName) {
        setCandidateNamesById((prev) => ({ ...prev, [String(candidateId)]: linkedName }))
      }
      await loadThreads(true)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to link candidate'))
    } finally {
      setBusy(false)
    }
  }

  const createTaskForThread = async () => {
    if (!selectedThread) return
    const title = taskTitle.trim()
    if (!title) return
    const start = taskAt ? new Date(taskAt).toISOString() : new Date(Date.now() + 60 * 60 * 1000).toISOString()
    const end = new Date(new Date(start).getTime() + 30 * 60 * 1000).toISOString()
    setBusy(true)
    setErrorText(null)
    try {
      await createCommunicationPlannerEvent({
        title,
        description: `From dialog ${selectedThread.id}`,
        kind: 'task',
        status: 'planned',
        priority: 'normal',
        start_at: start,
        end_at: end,
        assignee_id: assigneeDraft || selectedThread.assignee_id || undefined,
        source: 'messages',
      })
      setTaskTitle('')
      setTaskAt('')
      setTaskModalOpen(false)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to create task'))
    } finally {
      setBusy(false)
    }
  }

  const toggleNoReplyNeeded = async () => {
    if (!selectedThread) return
    setBusy(true)
    setErrorText(null)
    try {
      const current = noReplyNeededOf(selectedThread)
      const threadMeta = (selectedThread.thread_meta || {}) as Record<string, any>
      const slaPolicy = (threadMeta.sla_policy || {}) as Record<string, any>
      await patchCommunicationThread(selectedThread.id, {
        thread_meta: {
          ...threadMeta,
          no_reply_needed: !current,
          sla_policy: {
            ...slaPolicy,
            no_reply_needed: !current,
            ...(current ? {} : { snoozed_until: null }),
          },
        },
      })
      await loadThreads(true)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to update reply requirement'))
    } finally {
      setBusy(false)
    }
  }

  const toggleSlaMuted = async () => {
    if (!selectedThread) return
    setBusy(true)
    setErrorText(null)
    try {
      const current = slaMutedOf(selectedThread)
      const threadMeta = (selectedThread.thread_meta || {}) as Record<string, any>
      const slaPolicy = (threadMeta.sla_policy || {}) as Record<string, any>
      await patchCommunicationThread(selectedThread.id, {
        thread_meta: {
          ...threadMeta,
          sla_muted: !current,
          sla_policy: {
            ...slaPolicy,
            muted: !current,
          },
        },
      })
      await loadThreads(true)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to update SLA mute'))
    } finally {
      setBusy(false)
    }
  }

  const setOpsMode = async (
    mode: OpsMode,
    options?: {
      pausedUntil?: string | null
      escalationReason?: string
      escalationTargetRole?: string
      escalationTargetQueue?: string
      escalationTargetUserId?: string
    },
  ) => {
    if (!selectedThread) return
    setBusy(true)
    setErrorText(null)
    try {
      const threadMeta = (selectedThread.thread_meta || {}) as Record<string, any>
      const slaPolicy = (threadMeta.sla_policy || {}) as Record<string, any>
      const ops = (threadMeta.ops || {}) as Record<string, any>
      const nowIso = new Date().toISOString()
      const noReply = mode === 'no_reply_needed'
      const escalationTarget: Record<string, any> = {
        ...(options?.escalationTargetRole ? { role: String(options.escalationTargetRole).trim() } : {}),
        ...(options?.escalationTargetQueue ? { queue: String(options.escalationTargetQueue).trim() } : {}),
        ...(options?.escalationTargetUserId ? { user_id: String(options.escalationTargetUserId).trim() } : {}),
      }
      const nextOps: Record<string, any> = {
        ...ops,
        mode,
        updated_at: nowIso,
        by_user_id: me?.sub || null,
      }
      if (mode === 'later') {
        nextOps.paused_until = options?.pausedUntil || null
      }
      if (mode === 'escalated') {
        nextOps.escalation = {
          ...((ops.escalation || {}) as Record<string, any>),
          reason: String(options?.escalationReason || '').trim(),
          target: escalationTarget,
          escalated_at: nowIso,
        }
      }
      await patchCommunicationThread(selectedThread.id, {
        priority: mode === 'escalated' ? 'high' : selectedThread.priority,
        thread_meta: {
          ...threadMeta,
          no_reply_needed: noReply,
          ops: nextOps,
          sla_policy: {
            ...slaPolicy,
            no_reply_needed: noReply,
            ...(noReply ? { snoozed_until: null } : {}),
            ...(mode === 'later' ? { snoozed_until: options?.pausedUntil || null } : {}),
          },
        },
      })
      await loadThreads(true)
    } catch (err: any) {
      const escalationFriendly = escalationApiErrorText(err)
      setErrorText(escalationFriendly || errorTextFrom(err, 'Failed to update operational mode'))
    } finally {
      setBusy(false)
    }
  }

  const submitPauseOpsMode = async () => {
    const hours = Number(pauseHoursDraft)
    if (!Number.isFinite(hours) || hours <= 0) {
      setErrorText(t('app.communications_messages.ops.pause_hours_invalid', { defaultValue: 'Enter a valid number of hours (> 0).' }))
      return
    }
    const pausedUntil = new Date(Date.now() + hours * 60 * 60 * 1000).toISOString()
    await setOpsMode('later', { pausedUntil })
    setPauseModalOpen(false)
  }

  const submitEscalationOpsMode = async () => {
    const reason = escalationReasonDraft.trim()
    if (!reason) {
      setErrorText(t('app.communications_messages.ops.escalation_reason_required', { defaultValue: 'Escalation reason is required.' }))
      return
    }
    const targetValue = escalationTargetValueDraft.trim()
    if (!targetValue) {
      setErrorText(t('app.communications_messages.ops.escalation_target_required', { defaultValue: 'Escalation target is required.' }))
      return
    }
    const escalationTargetRole = escalationTargetTypeDraft === 'role' ? targetValue : ''
    const escalationTargetQueue = escalationTargetTypeDraft === 'queue' ? targetValue : ''
    const escalationTargetUserId = escalationTargetTypeDraft === 'user' ? targetValue : ''
    await setOpsMode('escalated', {
      escalationReason: reason,
      escalationTargetRole,
      escalationTargetQueue,
      escalationTargetUserId,
    })
    setEscalationModalOpen(false)
  }

  useEffect(() => {
    if (escalationTargetTypeDraft === 'role') {
      const fallback = escalationRoleOptions[0] || 'supervisor'
      if (!escalationRoleOptions.includes(escalationTargetValueDraft)) {
        setEscalationTargetValueDraft(fallback)
      }
      return
    }
    if (escalationTargetTypeDraft === 'queue') {
      const fallback = escalationQueueOptions[0] || 'priority'
      if (!escalationQueueOptions.includes(escalationTargetValueDraft)) {
        setEscalationTargetValueDraft(fallback)
      }
      return
    }
    const userIds = new Set(managerOptions.map((m) => String(m.id)))
    if (!userIds.has(escalationTargetValueDraft)) {
      setEscalationTargetValueDraft(String(managerOptions[0]?.id || ''))
    }
  }, [escalationTargetTypeDraft, escalationTargetValueDraft, escalationRoleOptions, escalationQueueOptions, managerOptions])

  const sendReply = async () => {
    if (!selectedThread || !replyText.trim()) return
    setBusy(true)
    setErrorText(null)
    try {
      const messageType = selectedThread.channel === 'sms' ? 'sms' : 'text'
      const recipient = replyRecipient.trim() || inferThreadRecipient(selectedThread)
      const msg = await createCommunicationMessage(selectedThread.id, {
        direction: 'outbound',
        message_type: messageType,
        body_text: replyText.trim(),
        recipient_address: recipient || undefined,
        delivery_status: 'queued',
      })
      await dispatchCommunicationMessage(msg.id, { mark_delivered: true })
      setReplyText('')
      await loadThreads(true)
      await loadThreadMessages(selectedThread.id, true)
      setUserScrolledUp(false)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to send message'))
    } finally {
      setBusy(false)
    }
  }

  const snoozeSla = async (hours: number) => {
    if (!selectedThread) return
    if (noReplyNeededOf(selectedThread)) return
    setBusy(true)
    setErrorText(null)
    try {
      const until = new Date(Date.now() + Math.max(1, hours) * 60 * 60 * 1000).toISOString()
      const threadMeta = (selectedThread.thread_meta || {}) as Record<string, any>
      const slaPolicy = (threadMeta.sla_policy || {}) as Record<string, any>
      await patchCommunicationThread(selectedThread.id, {
        thread_meta: {
          ...threadMeta,
          no_reply_needed: false,
          sla_policy: {
            ...slaPolicy,
            no_reply_needed: false,
            snoozed_until: until,
          },
        },
      })
      await loadThreads(true)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to snooze SLA'))
    } finally {
      setBusy(false)
    }
  }

  const addToComposer = (chunk: string) => {
    setReplyText((prev) => (prev ? `${prev} ${chunk}` : chunk))
  }

  const openThread = (threadId: string) => {
    setSelectedThreadId(threadId)
    const next = new URLSearchParams(searchParams)
    next.set('threadId', threadId)
    setSearchParams(next, { replace: true })
    if (isMobile) {
      setMobilePane('chat')
      setMobileToolsOpen(false)
      setQuickRepliesOpen(false)
      setShowRecipientField(false)
    }
  }

  const patchThreadMeta = async (thread: CommunicationThread, patch: Record<string, any>) => {
    const nextMeta = { ...(thread.thread_meta || {}), ...patch }
    await patchCommunicationThread(thread.id, { thread_meta: nextMeta })
  }

  const togglePin = async (thread: CommunicationThread) => {
    setBusy(true)
    setErrorText(null)
    try {
      await patchThreadMeta(thread, { ui_pinned: !isPinned(thread) })
      await loadThreads(true)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to toggle pin'))
    } finally {
      setBusy(false)
    }
  }

  const persistThreadOrder = async (ordered: CommunicationThread[]) => {
    const updates: Promise<any>[] = []
    ordered.forEach((th, idx) => {
      const currentOrder = orderOf(th)
      const nextOrder = idx + 1
      if (currentOrder !== nextOrder) {
        updates.push(patchThreadMeta(th, { ui_order: nextOrder }))
      }
    })
    if (updates.length) {
      await Promise.all(updates)
    }
  }

  const handleDropReorder = async (targetThreadId: string) => {
    if (!dragThreadId || dragThreadId === targetThreadId) return
    setBusy(true)
    setErrorText(null)
    try {
      const sourceIndex = filtered.findIndex((x) => x.id === dragThreadId)
      const targetIndex = filtered.findIndex((x) => x.id === targetThreadId)
      if (sourceIndex < 0 || targetIndex < 0) return
      const next = [...filtered]
      const [moved] = next.splice(sourceIndex, 1)
      next.splice(targetIndex, 0, moved)
      await persistThreadOrder(next)
      await loadThreads(true)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to reorder dialogs'))
    } finally {
      setBusy(false)
      setDragThreadId(null)
    }
  }

  return (
    <div className={clsx('flex flex-col', isMobile ? 'gap-2' : 'space-y-4')}>
      <WorkspaceTopNav active="messages" />
      <header className={clsx('flex flex-nowrap items-center gap-2', isMobile && 'min-h-0 shrink-0')}>
        <div className="min-w-0 flex-1">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="w-full input py-2"
            placeholder={t('app.communications_messages.search.placeholder')}
          />
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {!isMobile && (
            <button
              type="button"
              onClick={() => setTagManagerOpen(true)}
              className="btn-secondary"
            >
              {t('app.communications_messages.tags.manager')}
            </button>
          )}
          <button
            type="button"
            onClick={() => void loadThreads()}
            className="btn-secondary"
          >
            {t('common.actions.refresh', { defaultValue: 'Refresh' })}
          </button>
        </div>
      </header>

      {errorText && (
        <ErrorRecoveryBanner
          compact
          info={{ title: errorText, hint: 'Retry action or refresh dialogs.' }}
          onRetry={() => void loadThreads()}
          retryLabel={t('common.retry', { defaultValue: 'Retry' })}
          secondaryTo="/app/setup/communications"
          secondaryLabel={t('app.communications.states.empty_cta_setup', { defaultValue: 'Open communications setup' })}
        />
      )}

      {candidateFilterId && (
        <div className="alert-info flex items-center gap-2 text-sm">
          <span>{t('app.communications_messages.candidate_filter')}: {candidateFilterId}</span>
          <button
            type="button"
            onClick={() => {
              const next = new URLSearchParams(searchParams)
              next.delete('candidateId')
              setSearchParams(next, { replace: true })
            }}
            className="btn-secondary btn-xs"
          >
            {t('common.actions.clear', { defaultValue: 'Clear' })}
          </button>
        </div>
      )}

      <div className={clsx('grid gap-4 xl:grid-cols-[340px_minmax(600px,1fr)]', isMobile && 'min-h-0 flex-1')}>
        <section className={clsx('rounded-lg border border-slate-200 bg-white flex flex-col', isMobile && mobilePane === 'chat' && 'hidden', isMobile && 'min-h-[55vh]')}>
          <div className="border-b border-slate-100 px-4 py-3 shrink-0">
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-semibold text-slate-900">{t('app.communications_messages.dialogs.title')}</div>
              {isMobile && (
                <button
                  type="button"
                  onClick={() => setShowMobileFilters((prev) => !prev)}
                  className="btn-secondary btn-xs"
                >
                  {showMobileFilters
                    ? t('common.actions.hide', { defaultValue: 'Hide' })
                    : t('common.actions.show', { defaultValue: 'Show' })}{' '}
                  {t('app.communications_messages.dialogs.filters_label', { defaultValue: 'filters' })}
                </button>
              )}
            </div>
            {(!isMobile || showMobileFilters) && (
              <>
                <div className="mt-2 flex flex-wrap gap-1">
                  {(['all', 'in_work', 'later', 'no_reply_needed', 'escalated'] as OpsModeFilter[]).map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => setOpsModeFilter(mode)}
                      className={clsx(
                        'btn-secondary btn-xs',
                        opsModeFilter === mode && 'border-brand-600 bg-brand-50 text-brand-800',
                      )}
                    >
                      {mode === 'all'
                        ? t('app.communications_messages.ops.all_modes')
                        : opsModeText(mode)}
                    </button>
                  ))}
                </div>
                <div className="mt-1 text-[11px] text-slate-500">{t('app.communications_messages.dialogs.reorder_hint')}</div>
              </>
            )}
          </div>
          {loading && <div className="px-4 py-4 text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>}
          {!loading && filtered.length === 0 && (
            <div className="px-4 py-6">
              <EmptyStatePanel
                compact
                title={t('app.communications.states.empty_title', { defaultValue: 'No dialogs yet' })}
                description={t('app.communications.states.empty_desc', {
                  defaultValue: 'Connect messaging channels and start a conversation to see dialogs here.',
                })}
                primaryAction={{
                  label: t('app.communications.states.empty_cta_setup', { defaultValue: 'Open communications setup' }),
                  to: '/app/setup/communications',
                }}
                secondaryAction={{
                  label: t('app.communications.states.empty_cta_email', { defaultValue: 'Open email inbox' }),
                  to: '/app/email',
                }}
              />
            </div>
          )}
          {!loading && filtered.length > 0 && (
            <div className={clsx('divide-y divide-slate-100 overflow-auto', isMobile ? 'min-h-0 flex-1' : 'max-h-[70vh]')}>
              {filtered.map((th) => (
                <div
                  key={th.id}
                  draggable
                  onDragStart={() => setDragThreadId(th.id)}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => {
                    void handleDropReorder(th.id)
                  }}
                  onClick={() => openThread(th.id)}
                  className={clsx(
                    'w-full cursor-pointer px-4 py-3 text-left',
                    selectedThreadId === th.id ? 'bg-brand-50' : 'hover:bg-slate-50',
                    dragThreadId === th.id && 'opacity-60',
                  )}
                  style={{ borderLeft: `6px solid ${primaryTagColor(th) || 'transparent'}` }}
                >
                  <div className="flex items-start gap-2">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        void togglePin(th)
                      }}
                      title={isPinned(th) ? 'Unpin dialog' : 'Pin dialog'}
                      className={clsx(
                        'mt-0.5 inline-flex h-5 w-5 items-center justify-center rounded-md',
                        isPinned(th) ? 'bg-amber-100 text-amber-700' : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600',
                      )}
                    >
                      <IconPinned size={12} />
                    </button>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-semibold text-slate-900">{displayTitle(th)}</div>
                      <div className="mt-1 truncate text-xs text-slate-500">{th.last_message_preview || '—'}</div>
                      {tagsOf(th).length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {tagsOf(th).slice(0, 2).map((tag, idx) => (
                            <span
                              key={tag}
                              className={clsx('rounded px-1.5 py-0.5 font-medium', idx === 0 ? 'text-[11px]' : 'text-[10px]')}
                              style={{ backgroundColor: `${personalTagColor.get(tag.toLowerCase()) || '#e2e8f0'}44`, color: personalTagColor.get(tag.toLowerCase()) || '#334155' }}
                            >
                              {maybeTranslateKey(tag)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    {Number(th.unread_count || 0) > 0 && (
                      <span className="rounded-md bg-brand-600 px-2 py-0.5 text-xs text-white">{th.unread_count}</span>
                    )}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1 text-[11px] text-slate-500">
                    <span>{String(th.channel || '').toUpperCase()}</span>
                    <span>•</span>
                    <span>{th.assignee_id ? (managerLabelById.get(String(th.assignee_id)) || 'assigned') : 'unassigned'}</span>
                    <span>•</span>
                    <span>{th.linked_candidate_id ? 'candidate linked' : 'no candidate'}</span>
                    {tagsOf(th).length > 0 && (
                      <>
                        <span>•</span>
                        <span className="font-medium" style={{ color: primaryTagColor(th) || undefined }}>
                          #{maybeTranslateKey(tagsOf(th)[0])}
                        </span>
                      </>
                    )}
                    {noReplyNeededOf(th) && (
                      <>
                        <span>•</span>
                        <span className="text-emerald-700">
                          {t('app.communications_messages.ops.no_reply_needed')}
                        </span>
                      </>
                    )}
                    {opsModeOf(th) && (
                      <>
                        <span>•</span>
                        <span className="badge bg-slate-100 text-[10px] font-medium text-slate-700">{opsModeText(opsModeOf(th))}</span>
                      </>
                    )}
                    <span>•</span>
                    <span>{formatDateTime(th.last_message_at || th.updated_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className={clsx('rounded-lg border border-slate-200 bg-white', isMobile && mobilePane === 'list' && 'hidden')}>
          {!selectedThread && (
            <div className="px-6 py-8 text-sm text-slate-500">{t('app.communications_messages.dialogs.select_prompt')}</div>
          )}

          {selectedThread && (
            <div className="flex h-[70vh] flex-col">
              <div className="border-b border-slate-100 px-3 py-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      {isMobile && (
                        <button
                          type="button"
                          onClick={() => setMobilePane('list')}
                          className="btn-secondary btn-xs"
                        >
                          {t('common.actions.back', { defaultValue: 'Back' })}
                        </button>
                      )}
                      <div className="truncate text-sm font-semibold text-slate-900">{displayTitle(selectedThread)}</div>
                    </div>
                    <div className="mt-0.5 text-xs text-slate-500">
                      {String(selectedThread.channel || '').toUpperCase()} · {selectedThread.status} · {formatDateTime(selectedThread.last_message_at || selectedThread.updated_at)}
                      {slaSnoozedUntilOf(selectedThread) && !noReplyNeededOf(selectedThread) ? ` · SLA snoozed until ${formatDateTime(slaSnoozedUntilOf(selectedThread))}` : ''}
                      {slaMutedOf(selectedThread)
                        ? ` · ${t('app.communications_messages.sla.sla_muted')}`
                        : ''}
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-1">
                    <span className="badge bg-slate-100 text-[11px] text-slate-700">
                      {t('app.communications_messages.manager.label')}: {selectedThread.assignee_id ? (managerLabelById.get(String(selectedThread.assignee_id)) || selectedThread.assignee_id) : t('app.communications_messages.manager.unassigned')}
                    </span>
                    <span className="badge bg-slate-100 text-[11px] text-slate-700">
                      {t('app.communications_messages.tags.label')}: {tagsOf(selectedThread).length}
                    </span>
                    {opsModeOf(selectedThread) && (
                      <span className="badge bg-slate-100 text-[11px] text-slate-700">
                        {opsModeText(opsModeOf(selectedThread))}
                      </span>
                    )}
                  </div>
                </div>

                <div className="mt-2 flex flex-wrap items-start gap-2">
                  {isMobile && (
                    <button
                      type="button"
                      onClick={() => setMobileToolsOpen((prev) => !prev)}
                      className="btn-secondary btn-sm"
                    >
                      {mobileToolsOpen
                        ? t('common.actions.hide', { defaultValue: 'Hide' })
                        : t('common.actions.show', { defaultValue: 'Show' })}{' '}
                      tools
                    </button>
                  )}
                </div>

                {(!isMobile || mobileToolsOpen) && (
                  <div className="mt-2 flex flex-wrap items-start gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setOpenActionMenu(null)
                      setActiveToolsPanel((prev) => (prev === 'manager' ? null : 'manager'))
                    }}
                    className={clsx(
                      'btn-secondary btn-sm',
                      activeToolsPanel === 'manager' && 'border-slate-400 bg-slate-100 text-slate-900',
                    )}
                  >
                    {t('app.communications_messages.manager.label')}
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setOpenActionMenu(null)
                      setActiveToolsPanel((prev) => (prev === 'tags' ? null : 'tags'))
                    }}
                    className={clsx(
                      'btn-secondary btn-sm',
                      activeToolsPanel === 'tags' && 'border-slate-400 bg-slate-100 text-slate-900',
                    )}
                  >
                    {t('app.communications_messages.tags.label')}
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setOpenActionMenu(null)
                      setActiveToolsPanel((prev) => (prev === 'candidate' ? null : 'candidate'))
                    }}
                    className={clsx(
                      'btn-secondary btn-sm',
                      activeToolsPanel === 'candidate'
                        ? 'border-emerald-400 bg-emerald-50 text-emerald-900'
                        : selectedThread.linked_candidate_id
                          ? 'border-emerald-300 bg-white text-emerald-900'
                          : 'border-slate-300 bg-white text-slate-700',
                    )}
                  >
                    {t('app.communications_messages.candidate.label')}
                  </button>

                  <div className="relative" ref={workflowMenuRef}>
                    <button
                      type="button"
                      onClick={() => setOpenActionMenu((prev) => (prev === 'workflow' ? null : 'workflow'))}
                      className="btn-secondary btn-sm"
                    >
                      {t('app.communications_messages.action_groups.workflow', { defaultValue: 'Workflow' })}
                    </button>
                    {openActionMenu === 'workflow' && (
                      <div className="absolute left-0 z-20 mt-1 w-[min(18rem,calc(100vw-2rem))] max-h-72 overflow-auto rounded border border-slate-200 bg-white p-1 shadow-lg">
                        <button
                          type="button"
                          onClick={() => {
                            setOpenActionMenu(null)
                            void toggleNoReplyNeeded()
                          }}
                          disabled={busy}
                          className={clsx(
                            'dropdown-item disabled:opacity-50',
                            noReplyNeededOf(selectedThread) ? 'bg-emerald-50 text-emerald-900' : 'text-slate-700',
                          )}
                        >
                          {noReplyNeededOf(selectedThread)
                            ? t('app.communications_messages.ops.no_reply_needed')
                            : t('app.communications_messages.reply_required')}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setOpenActionMenu(null)
                            void setOpsMode('in_work')
                          }}
                          disabled={busy}
                          className={clsx(
                            'dropdown-item disabled:opacity-50',
                            opsModeOf(selectedThread) === 'in_work' && 'bg-emerald-50 text-emerald-900',
                          )}
                        >
                          <span className="inline-flex items-center gap-2">
                            <span className="h-2 w-2 rounded-full bg-emerald-500" />
                            {t('app.communications_messages.ops.in_work')}
                          </span>
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setOpenActionMenu(null)
                            setPauseHoursDraft('4')
                            setPauseModalOpen(true)
                          }}
                          disabled={busy}
                          className={clsx(
                            'dropdown-item disabled:opacity-50',
                            opsModeOf(selectedThread) === 'later' && 'bg-amber-50 text-amber-900',
                          )}
                        >
                          <span className="inline-flex items-center gap-2">
                            <span className="h-2 w-2 rounded-full bg-amber-500" />
                            {t('app.communications_messages.ops.later')}
                          </span>
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setOpenActionMenu(null)
                            setEscalationReasonDraft('')
                            setEscalationTargetTypeDraft('role')
                            setEscalationTargetValueDraft(String(escalationRoleOptions[0] || 'supervisor'))
                            setEscalationModalOpen(true)
                          }}
                          disabled={busy}
                          title={t('app.communications_messages.ops.escalated_hint', {
                            defaultValue: 'Escalation routes this dialog for supervisor attention and requires a reason.',
                          })}
                          className={clsx(
                            'dropdown-item disabled:opacity-50',
                            opsModeOf(selectedThread) === 'escalated' && 'bg-rose-50 text-rose-900',
                          )}
                        >
                          <span className="inline-flex items-center gap-2">
                            <span className="h-2 w-2 rounded-full bg-rose-500" />
                            {t('app.communications_messages.ops.escalated')}
                          </span>
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="relative" ref={slaMenuRef}>
                    <button
                      type="button"
                      onClick={() => setOpenActionMenu((prev) => (prev === 'sla' ? null : 'sla'))}
                      className="btn-secondary btn-sm"
                    >
                      {t('app.communications_messages.action_groups.sla', { defaultValue: 'SLA' })}
                    </button>
                    {openActionMenu === 'sla' && (
                      <div className="absolute left-0 z-20 mt-1 w-[min(18rem,calc(100vw-2rem))] max-h-72 overflow-auto rounded border border-slate-200 bg-white p-1 shadow-lg">
                        <button
                          type="button"
                          onClick={() => {
                            setOpenActionMenu(null)
                            void toggleSlaMuted()
                          }}
                          disabled={busy}
                          title={slaMutedOf(selectedThread)
                            ? t('app.communications_messages.sla.unmute_hint', {
                                defaultValue: 'Unmute SLA to resume overdue checks and reminders for this dialog.',
                              })
                            : t('app.communications_messages.sla.mute_hint', {
                                defaultValue: 'Mute SLA to stop overdue alerts and reminders for this dialog.',
                              })}
                          className={clsx(
                            'dropdown-item disabled:opacity-50',
                            slaMutedOf(selectedThread) && 'bg-amber-50 text-amber-900',
                          )}
                        >
                          <span className="inline-flex items-center gap-2">
                            <span className={clsx('h-2 w-2 rounded-full', slaMutedOf(selectedThread) ? 'bg-amber-500' : 'bg-slate-400')} />
                            {slaMutedOf(selectedThread)
                              ? t('app.communications_messages.sla.sla_muted')
                              : t('app.communications_messages.sla.mute_sla')}
                          </span>
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setOpenActionMenu(null)
                            void snoozeSla(1)
                          }}
                          disabled={busy || noReplyNeededOf(selectedThread) || slaMutedOf(selectedThread)}
                          className="dropdown-item disabled:opacity-50"
                        >
                          <span className="inline-flex items-center gap-2">
                            <span className="h-2 w-2 rounded-full bg-brand-500" />
                            {t('app.communications_messages.sla.snooze_1h', { defaultValue: 'Snooze +1h' })}
                          </span>
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setOpenActionMenu(null)
                            void snoozeSla(4)
                          }}
                          disabled={busy || noReplyNeededOf(selectedThread) || slaMutedOf(selectedThread)}
                          className="dropdown-item disabled:opacity-50"
                        >
                          <span className="inline-flex items-center gap-2">
                            <span className="h-2 w-2 rounded-full bg-brand-600" />
                            {t('app.communications_messages.sla.snooze_4h', { defaultValue: 'Snooze +4h' })}
                          </span>
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="relative" ref={moreMenuRef}>
                    <button
                      type="button"
                      onClick={() => setOpenActionMenu((prev) => (prev === 'more' ? null : 'more'))}
                      className="btn-secondary btn-sm"
                    >
                      {t('app.communications_messages.action_groups.more', { defaultValue: 'More' })}
                    </button>
                    {openActionMenu === 'more' && (
                      <div className="absolute left-0 z-20 mt-1 w-[min(18rem,calc(100vw-2rem))] max-h-72 overflow-auto rounded border border-slate-200 bg-white p-1 shadow-lg">
                        {selectedThread.linked_candidate_id && (
                          <a
                            href={`/app/candidates/${selectedThread.linked_candidate_id}?from=messages&threadId=${selectedThread.id}`}
                            className="dropdown-item"
                          >
                            {t('app.communications_messages.candidate.card')}
                          </a>
                        )}
                        <button
                          type="button"
                          onClick={() => {
                            setOpenActionMenu(null)
                            setTaskModalOpen(true)
                          }}
                          className="dropdown-item"
                        >
                          {t('app.communications_messages.task.button')}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setOpenActionMenu(null)
                            setTagManagerOpen(true)
                          }}
                          className="dropdown-item"
                        >
                          {t('app.communications_messages.tags.manage')}
                        </button>
                      </div>
                    )}
                  </div>
                  </div>
                )}

                {(!isMobile || mobileToolsOpen) && activeToolsPanel === 'manager' && (
                  <div className="mt-1 flex flex-wrap items-center gap-2 rounded border border-slate-200 bg-slate-50 p-2">
                    <select value={assigneeDraft} onChange={(e) => setAssigneeDraft(e.target.value)} className="input">
                      <option value="">{t('app.communications_messages.manager.unassigned')}</option>
                      {managerOptions.map((m) => (
                        <option key={m.id} value={m.id}>{m.label}</option>
                      ))}
                    </select>
                    <button type="button" onClick={() => void saveAssignee()} disabled={busy} className="btn-secondary btn-sm disabled:opacity-50">{t('app.communications_messages.manager.save')}</button>
                  </div>
                )}

                {(!isMobile || mobileToolsOpen) && activeToolsPanel === 'tags' && (
                  <div className="mt-1 flex flex-wrap items-center gap-2 rounded border border-slate-200 bg-slate-50 p-2">
                    <select value={tagPick} onChange={(e) => setTagPick(e.target.value)} className="input">
                      <option value="">{t('app.communications_messages.tags.select')}</option>
                      {activePersonalTags.map((tag) => (
                        <option key={tag.name} value={tag.name}>{maybeTranslateKey(tag.name)}</option>
                      ))}
                    </select>
                    <button type="button" onClick={() => void addSelectedTag()} disabled={busy || !tagPick} className="btn-secondary btn-sm disabled:opacity-50">{t('common.actions.apply', { defaultValue: 'Apply' })}</button>
                    <input value={quickTag} onChange={(e) => setQuickTag(e.target.value)} placeholder={t('app.communications_messages.tags.ad_hoc')} className="w-[150px] input" />
                    <button type="button" onClick={() => void addQuickTag()} disabled={busy || !quickTag.trim()} className="btn-secondary btn-sm disabled:opacity-50">{t('app.communications_messages.tags.quick_add')}</button>
                    <button type="button" onClick={() => setTagManagerOpen(true)} className="btn-secondary btn-sm">{t('app.communications_messages.tags.manage')}</button>
                  </div>
                )}

                {(!isMobile || mobileToolsOpen) && activeToolsPanel === 'candidate' && (
                  <div className="mt-1 rounded border border-slate-200 bg-slate-50 p-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        value={candidateQuery}
                        onChange={(e) => setCandidateQuery(e.target.value)}
                        placeholder={t('app.communications_messages.candidate.search_placeholder')}
                        className="min-w-[220px] flex-1 input"
                      />
                      <button
                        type="button"
                        onClick={() => void runCandidateSearch()}
                        disabled={busy || candidateSearching || candidateQuery.trim().length < 2}
                        className="btn-secondary btn-sm disabled:opacity-50"
                      >
                        {candidateSearching
                          ? t('app.communications_messages.candidate.searching')
                          : t('app.communications_messages.actions.search')}
                      </button>
                      {selectedThread.linked_candidate_id && (
                        <button
                          type="button"
                          onClick={() => void bindCandidate(null)}
                          disabled={busy}
                          className="btn-danger btn-sm disabled:opacity-50"
                        >
                          {t('app.communications_messages.candidate.unlink')}
                        </button>
                      )}
                    </div>
                    {candidateResults.length > 0 && (
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <select
                          value={candidatePickId}
                          onChange={(e) => setCandidatePickId(e.target.value)}
                          className="min-w-[240px] flex-1 input"
                        >
                          {candidateResults.map((c) => (
                            <option key={c.id} value={c.id}>
                              {candidateLabel(c)}
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          onClick={() => void bindCandidate(candidatePickId || null)}
                          disabled={busy || !candidatePickId}
                          className="btn-primary btn-sm disabled:opacity-50"
                        >
                          {t('app.communications_messages.candidate.link')}
                        </button>
                      </div>
                    )}
                  </div>
                )}

                <div className={clsx('mt-1 flex flex-wrap gap-2', isMobile && !mobileToolsOpen && 'hidden')}>
                  {tagsOf(selectedThread).map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => void removeThreadTag(tag)}
                      className="rounded px-2 py-0.5 text-xs font-medium"
                      style={{ backgroundColor: `${personalTagColor.get(tag.toLowerCase()) || '#94a3b8'}33`, color: personalTagColor.get(tag.toLowerCase()) || '#334155' }}
                      title="Click to remove from dialog"
                    >
                      {tag} ×
                    </button>
                  ))}
                </div>
              </div>

              <div
                ref={timelineRef}
                onScroll={(e) => {
                  const el = e.currentTarget
                  const gap = el.scrollHeight - el.scrollTop - el.clientHeight
                  setUserScrolledUp(gap > 60)
                }}
                className="flex-1 space-y-2 overflow-auto bg-slate-50 p-4"
              >
                {messagesLoading && <div className="text-xs text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>}
                {!messagesLoading && messages.length === 0 && (
                  <div className="text-xs text-slate-500">{t('app.communications_messages.timeline.empty')}</div>
                )}
                {messages.map((msg, idx) => {
                  const outbound = msg.direction === 'outbound'
                  const ts = msg.sent_at || msg.created_at
                  const prevTs = idx > 0 ? (messages[idx - 1].sent_at || messages[idx - 1].created_at) : null
                  const showDay = idx === 0 || dayKey(ts) !== dayKey(prevTs)
                  return (
                    <div key={msg.id}>
                      {showDay && (
                        <div className="sticky top-0 z-10 mb-2 flex justify-center">
                          <span className="badge border border-slate-200 bg-white text-slate-500 shadow-sm">
                            {formatDateOnly(ts)}
                          </span>
                        </div>
                      )}
                      <div className={clsx('flex', outbound ? 'justify-end' : 'justify-start')}>
                        <div className={clsx('max-w-[75%] rounded-lg px-3 py-2 text-sm shadow-sm', outbound ? 'bg-brand-600 text-white' : 'bg-white text-slate-900')}>
                          <div className={clsx('whitespace-pre-wrap', outbound ? 'text-white' : 'text-slate-900')}>{textOf(msg)}</div>
                          <div className={clsx('mt-1 text-[11px]', outbound ? 'text-brand-100' : 'text-slate-500')}>
                            {formatDateTime(ts)}
                            {outbound ? ` · ${deliveryLabel(msg.delivery_status)}` : ''}
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>

              <div className="border-t border-slate-100 p-3">
                <div className="mb-2 flex flex-wrap items-center gap-1">
                  {QUICK_EMOJIS.map((token) => (
                    <button
                      key={token}
                      type="button"
                      onClick={() => addToComposer(token)}
                      className="btn-secondary btn-xs"
                    >
                      {token}
                    </button>
                  ))}
                  {!isMobile && quickTemplates.map((tpl) => (
                    <button
                      key={tpl}
                      type="button"
                      onClick={() => setReplyText(tpl)}
                      className="btn-secondary btn-xs"
                    >
                      {maybeTranslateKey(tpl)}
                    </button>
                  ))}
                  {isMobile && (
                    <button type="button" onClick={() => setQuickRepliesOpen((prev) => !prev)} className="btn-secondary btn-xs">
                      {quickRepliesOpen ? 'Hide quick replies' : 'Quick replies'}
                    </button>
                  )}
                  {isMobile && (
                    <button type="button" onClick={() => setShowRecipientField((prev) => !prev)} className="btn-secondary btn-xs">
                      {showRecipientField ? 'Hide recipient' : 'Recipient'}
                    </button>
                  )}
                </div>
                {isMobile && quickRepliesOpen && (
                  <div className="mb-2 flex flex-wrap gap-1">
                    {quickTemplates.map((tpl) => (
                      <button
                        key={tpl}
                        type="button"
                        onClick={() => setReplyText(tpl)}
                        className="btn-secondary btn-xs"
                      >
                        {maybeTranslateKey(tpl)}
                      </button>
                    ))}
                  </div>
                )}
                {(!isMobile || showRecipientField) && (
                  <input
                    value={replyRecipient}
                    onChange={(e) => setReplyRecipient(e.target.value)}
                    className="mb-2 w-full input"
                    placeholder={t('app.communications_messages.compose.recipient_placeholder')}
                  />
                )}
                <div className="flex gap-2">
                  <textarea
                    rows={isMobile ? 2 : 3}
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    onKeyDown={(e) => {
                      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                        e.preventDefault()
                        if (!busy && replyText.trim()) {
                          void sendReply()
                        }
                      }
                    }}
                    className="w-full textarea"
                    placeholder={t('app.communications_messages.compose.message_placeholder')}
                  />
                  <button
                    type="button"
                    disabled={busy || !replyText.trim()}
                    onClick={() => void sendReply()}
                    className="h-fit btn-primary disabled:opacity-50"
                  >
                    {t('app.communications_messages.actions.send')}
                  </button>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>

      {tagManagerOpen && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-2xl rounded-lg border border-slate-200 bg-white p-4 shadow-xl">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-slate-900">{t('app.communications_messages.tags.manager')}</div>
                <div className="text-xs text-slate-500">{t('app.communications_messages.tags.manager_hint')}</div>
              </div>
              <button
                type="button"
                onClick={() => setTagManagerOpen(false)}
                className="btn-secondary btn-xs"
              >
                {t('common.actions.close', { defaultValue: 'Close' })}
              </button>
            </div>
            <div className="space-y-2">
              <div className="grid grid-cols-[minmax(180px,1fr)_140px_auto] items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <div>{t('app.communications_messages.tags.columns.name')}</div>
                <div>{t('app.communications_messages.tags.columns.color')}</div>
                <div>{t('app.communications_messages.tags.columns.state')}</div>
              </div>
              <div className="max-h-[40vh] space-y-2 overflow-auto pr-1">
                {personalTags.map((tag) => (
                  <div key={tag.name} className="grid grid-cols-[minmax(180px,1fr)_140px_auto] items-center gap-2 rounded border border-slate-200 p-2">
                    <input
                      value={tag.name}
                      onChange={(e) => {
                        const nextName = e.target.value
                        setPersonalTags((prev) => prev.map((x) => (x.name === tag.name ? { ...x, name: nextName } : x)))
                      }}
                      onBlur={async (e) => {
                        const nextName = e.target.value.trim()
                        if (!nextName || nextName === tag.name) return
                        const duplicate = personalTags.some((x) => x.name.toLowerCase() === nextName.toLowerCase() && x.name !== tag.name)
                        if (duplicate) return
                        const next = personalTags.map((x) => (x.name === tag.name ? { ...x, name: nextName } : x))
                        await savePersonalTags(next)
                      }}
                      className="input"
                    />
                    <input
                      type="color"
                      value={tag.color || TAG_COLORS[0]}
                      onChange={(e) => {
                        void updatePersonalTag(tag.name, { color: e.target.value })
                      }}
                      className="h-9 w-full input p-1"
                    />
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => void updatePersonalTag(tag.name, { archived: !tag.archived })}
                        className={clsx(
                          'btn-secondary btn-xs',
                          tag.archived ? 'border-amber-300 bg-amber-50 text-amber-900' : 'border-emerald-300 bg-emerald-50 text-emerald-900',
                        )}
                      >
                        {tag.archived
                          ? t('app.communications_messages.tags.archived')
                          : t('app.communications_messages.tags.active')}
                      </button>
                      <button
                        type="button"
                        onClick={() => void removePersonalTag(tag.name)}
                        className="btn-danger btn-xs"
                      >
                        {t('common.actions.delete', { defaultValue: 'Delete' })}
                      </button>
                    </div>
                  </div>
                ))}
                {personalTags.length === 0 && (
                  <div className="rounded-lg border border-dashed border-slate-300 p-3 text-sm text-slate-500">{t('app.communications_messages.tags.empty')}</div>
                )}
              </div>
              <div className="mt-2 rounded border border-slate-200 bg-slate-50 p-3">
                <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.communications_messages.tags.create_new')}</div>
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    value={newTagName}
                    onChange={(e) => setNewTagName(e.target.value)}
                    placeholder={t('app.communications_messages.tags.name_placeholder')}
                    className="min-w-[180px] input"
                  />
                  <select
                    value={newTagColor}
                    onChange={(e) => setNewTagColor(e.target.value)}
                    className="input"
                  >
                    {TAG_COLORS.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => void createPersonalTag()}
                    disabled={busy || !newTagName.trim()}
                    className="btn-primary btn-sm disabled:opacity-50"
                  >
                    {t('app.communications_messages.tags.create')}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {taskModalOpen && selectedThread && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-xl rounded-lg border border-slate-200 bg-white p-4 shadow-xl">
            <div className="mb-3 text-sm font-semibold text-slate-900">{t('app.communications_messages.task.modal_title')}</div>
            <div className="space-y-2">
              <input
                value={taskTitle}
                onChange={(e) => setTaskTitle(e.target.value)}
                placeholder={t('app.communications_messages.task.title_placeholder')}
                className="w-full input"
              />
              <input
                type="datetime-local"
                value={taskAt}
                onChange={(e) => setTaskAt(e.target.value)}
                className="w-full input"
              />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setTaskModalOpen(false)}
                className="btn-secondary btn-sm"
              >
                {t('common.actions.cancel', { defaultValue: 'Cancel' })}
              </button>
              <button
                type="button"
                onClick={() => void createTaskForThread()}
                disabled={busy || !taskTitle.trim()}
                className="btn-primary btn-sm disabled:opacity-50"
              >
                {t('common.actions.create', { defaultValue: 'Create' })}
              </button>
            </div>
          </div>
        </div>
      )}

      {pauseModalOpen && selectedThread && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-4 shadow-xl">
            <div className="mb-3 text-sm font-semibold text-slate-900">
              {t('app.communications_messages.ops.pause_modal_title', { defaultValue: 'Pause dialog' })}
            </div>
            <label className="block">
              <div className="mb-1 text-xs font-medium text-slate-600">
                {t('app.communications_messages.ops.pause_hours_label', { defaultValue: 'Pause duration (hours)' })}
              </div>
              <input
                type="number"
                min={1}
                step={1}
                value={pauseHoursDraft}
                onChange={(e) => setPauseHoursDraft(e.target.value)}
                className="w-full input"
              />
            </label>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setPauseModalOpen(false)}
                className="btn-secondary btn-sm"
              >
                {t('common.actions.cancel', { defaultValue: 'Cancel' })}
              </button>
              <button
                type="button"
                onClick={() => void submitPauseOpsMode()}
                disabled={busy}
                className="btn-primary btn-sm disabled:opacity-50"
              >
                {t('common.actions.apply', { defaultValue: 'Apply' })}
              </button>
            </div>
          </div>
        </div>
      )}

      {escalationModalOpen && selectedThread && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-lg border border-slate-200 bg-white p-4 shadow-xl">
            <div className="mb-3 text-sm font-semibold text-slate-900">
              {t('app.communications_messages.ops.escalation_modal_title', { defaultValue: 'Escalate dialog' })}
            </div>
            <div className="space-y-2">
              <label className="block">
                <div className="mb-1 text-xs font-medium text-slate-600">
                  {t('app.communications_messages.ops.escalation_reason_prompt', { defaultValue: 'Escalation reason' })}
                </div>
                <textarea
                  rows={3}
                  value={escalationReasonDraft}
                  onChange={(e) => setEscalationReasonDraft(e.target.value)}
                  className="w-full textarea"
                />
              </label>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
                <label className="block md:col-span-1">
                  <div className="mb-1 text-xs font-medium text-slate-600">
                    {t('app.communications_messages.ops.escalation_target_type_label', { defaultValue: 'Target type' })}
                  </div>
                  <select
                    value={escalationTargetTypeDraft}
                    onChange={(e) => setEscalationTargetTypeDraft(e.target.value as 'role' | 'queue' | 'user')}
                    className="w-full input"
                  >
                    <option value="role">{t('app.communications_messages.ops.target_type_role', { defaultValue: 'Role' })}</option>
                    <option value="queue">{t('app.communications_messages.ops.target_type_queue', { defaultValue: 'Queue' })}</option>
                    <option value="user">{t('app.communications_messages.ops.target_type_user', { defaultValue: 'User' })}</option>
                  </select>
                </label>
                <label className="block md:col-span-2">
                  <div className="mb-1 text-xs font-medium text-slate-600">
                    {t('app.communications_messages.ops.escalation_target_value_label', { defaultValue: 'Target value' })}
                  </div>
                  {escalationTargetTypeDraft === 'role' && (
                    <select
                      value={escalationTargetValueDraft}
                      onChange={(e) => setEscalationTargetValueDraft(e.target.value)}
                      className="w-full input"
                    >
                      {escalationRoleOptions.map((role) => (
                        <option key={role} value={role}>{role}</option>
                      ))}
                    </select>
                  )}
                  {escalationTargetTypeDraft === 'queue' && (
                    <select
                      value={escalationTargetValueDraft}
                      onChange={(e) => setEscalationTargetValueDraft(e.target.value)}
                      className="w-full input"
                    >
                      {escalationQueueOptions.map((queueId) => (
                        <option key={queueId} value={queueId}>{queueId}</option>
                      ))}
                    </select>
                  )}
                  {escalationTargetTypeDraft === 'user' && (
                    <select
                      value={escalationTargetValueDraft}
                      onChange={(e) => setEscalationTargetValueDraft(e.target.value)}
                      className="w-full input"
                    >
                      {managerOptions.length === 0 && (
                        <option value="">{t('app.communications_messages.manager.unassigned')}</option>
                      )}
                      {managerOptions.map((m) => (
                        <option key={m.id} value={String(m.id)}>{String(m.label || m.full_name || m.email || m.id)}</option>
                      ))}
                    </select>
                  )}
                </label>
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setEscalationModalOpen(false)}
                className="btn-secondary btn-sm"
              >
                {t('common.actions.cancel', { defaultValue: 'Cancel' })}
              </button>
              <button
                type="button"
                onClick={() => void submitEscalationOpsMode()}
                disabled={busy}
                className="btn-primary btn-sm disabled:opacity-50"
              >
                {t('common.actions.apply', { defaultValue: 'Apply' })}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
