import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  IconBell,
  IconLayoutSidebarLeftExpand,
  IconLogout,
  IconMail,
  IconMenu2,
  IconMessageCircle,
  IconPlus,
  IconUserCircle,
  IconX,
} from '@tabler/icons-react'
import type { TenantSummary, WhoAmI } from '../../api/types'
import {
  listNotifications,
  markNotificationsRead,
  reconcileNotifications,
  listOwnCompanies,
  setActiveOwnCompany,
  ownCompanySettings,
} from '../../api/client'
import type { NotificationItem, NotificationListResponse } from '../../api/types'
import {
  getNotificationAttentionTier,
  getNotificationUosGroup,
  type NotificationAttentionTier,
  type NotificationUosGroup,
} from '../../utils/notificationUos'
import { listCommunicationThreads, reconcileCommunicationThreadUnread } from '../../api/communications'
import { useToast } from '../Toast'
import { useCommunicationsAccess } from '../../hooks/useCommunicationsAccess'
import { usePermissions } from '../../hooks/usePermissions'
import { searchGlobal, type GlobalSearchResult } from '../../api/search'
import { useI18n, type LocaleCode } from '../../i18n'
import { useAuth } from '../../store/useAuth'
import { TopbarNbaMenu } from '../nba/TopbarNbaMenu'
import { usePendingHandoffsCount } from '../../hooks/usePendingHandoffsCount'
import { useBusinessTerminology } from '../../hooks/useBusinessTerminology'
import { communicationsThreadPath } from '../../app/crmAppPaths'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { buildInboxThreadPath } from '../../utils/inboxDeepLinks'
import { formatDistanceToNow } from 'date-fns'
import { enUS, ru, pl } from 'date-fns/locale'

type TenantTopbarSummary = TenantSummary & { status?: string | null; type?: string | null }

type TopbarProps = {
  me: WhoAmI | null
  tenant: TenantTopbarSummary | null
  onLogout: () => void
  onToggleSidebar: () => void
  compact?: boolean
}

const SUPPORTED_LOCALES: LocaleCode[] = ['ru', 'en', 'pl']
const SEARCH_SHORTCUT_HINT = '\u2318K'

const RESULT_LABEL_KEYS: Record<GlobalSearchResult['type'], string> = {
  candidate: 'app.topbar.search.results.candidate',
  company: 'app.topbar.search.results.company',
  document: 'app.topbar.search.results.document',
  vacancy: 'app.topbar.search.results.vacancy',
  lead: 'app.topbar.search.results.lead',
  invoice: 'app.topbar.search.results.invoice',
  service_order: 'app.topbar.search.results.service_order',
  conversation: 'app.topbar.search.results.conversation',
  task: 'app.topbar.search.results.task',
}

function appendSearchQueryParam(path: string, query: string): string {
  const trimmed = query.trim()
  if (!trimmed) return path
  const q = encodeURIComponent(trimmed)
  return path.includes('?') ? `${path}&q=${q}` : `${path}?q=${q}`
}

function humanizeEventType(eventType: string): string {
  return eventType
    .trim()
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/^\w/, (c) => c.toUpperCase())
}

function NotificationAttentionTierChip({
  tier,
  isRead,
  label,
}: {
  tier: NotificationAttentionTier
  isRead: boolean
  label: string
}) {
  const base =
    'shrink-0 rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide'
  if (tier === 'critical') {
    return (
      <span
        className={`${base} ${isRead ? 'bg-rose-100 text-rose-700' : 'bg-rose-600 text-white'}`}
        title={label}
      >
        {label}
      </span>
    )
  }
  if (tier === 'high') {
    return (
      <span
        className={`${base} ${isRead ? 'bg-amber-100 text-amber-900' : 'bg-amber-500 text-white'}`}
        title={label}
      >
        {label}
      </span>
    )
  }
  return (
    <span
      className={`${base} ${isRead ? 'bg-slate-100 text-slate-500' : 'bg-slate-200 text-slate-800'}`}
      title={label}
    >
      {label}
    </span>
  )
}

function isBellAttentionNotification(item: NotificationItem): boolean {
  if (item.is_read) return false
  const t = getNotificationAttentionTier(item)
  return t === 'critical' || t === 'high'
}

/** Bell count: urgent notifications + handoffs (max of API pending vs unread handoff notifs — no double count). */
function notificationThreadId(item: NotificationItem): string {
  const p = item.payload as Record<string, unknown> | undefined
  const raw = p?.thread_id
  if (typeof raw === 'string') return raw.trim()
  if (raw != null) {
    const s = String(raw).trim()
    return s
  }
  return ''
}

function notificationThreadChannel(item: NotificationItem): 'messages' | 'email' | undefined {
  const p = item.payload as Record<string, unknown> | undefined
  const c = String(p?.channel || '').trim().toLowerCase()
  if (c === 'email') return 'email'
  if (c === 'messages' || c === 'message') return 'messages'
  return undefined
}

function computeBellAttentionCount(items: NotificationItem[], pendingHandoffsCount: number): number {
  const unreadHandoffNotifs = items.filter(
    (i) => !i.is_read && String(i.event_type || '').toLowerCase() === 'handoff_requested',
  ).length
  const handoffPart = Math.max(pendingHandoffsCount, unreadHandoffNotifs)
  const notifPart = items.filter((i) => {
    if (!isBellAttentionNotification(i)) return false
    if (String(i.event_type || '').toLowerCase() === 'handoff_requested') return false
    return true
  }).length
  return notifPart + handoffPart
}

function formatThreadUnreadBadge(n: number): string {
  if (n <= 99) return String(n)
  return '99+'
}

export function Topbar({ me, tenant, onLogout, onToggleSidebar, compact = false }: TopbarProps) {
  const navigate = useNavigate()
  const { can, isClientTenant } = usePermissions()
  const { canUseCommunicationsFeature } = useCommunicationsAccess()
  const { locale, setLocale, t } = useI18n()
  const { canReturnToPlatform, restorePlatformSession } = useAuth()
  const { notify } = useToast()
  const [notifOpen, setNotifOpen] = useState(false)
  const [notifItems, setNotifItems] = useState<NotificationItem[]>([])
  const [notifFeedMode, setNotifFeedMode] = useState<'all' | NotificationUosGroup>('all')
  const [notifLoading, setNotifLoading] = useState(false)
  const [notifError, setNotifError] = useState<string | null>(null)
  const notifRef = useRef<HTMLDivElement | null>(null)
  const localeMap = { ru, en: enUS, pl }

  const [menuOpen, setMenuOpen] = useState(false)
  const [langOpen, setLangOpen] = useState(false)
  const [quickCreateOpen, setQuickCreateOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchResults, setSearchResults] = useState<GlobalSearchResult[]>([])
  const [searchError, setSearchError] = useState<string | null>(null)
  const [bellAttentionCount, setBellAttentionCount] = useState(0)
  const [messagesUnreadCount, setMessagesUnreadCount] = useState(0)
  const [emailUnreadCount, setEmailUnreadCount] = useState(0)
  const shownNotificationIdsRef = useRef<Set<string>>(new Set())
  const lastUnreadNotificationsRef = useRef<NotificationItem[]>([])
  const menuRef = useRef<HTMLDivElement | null>(null)
  const langRef = useRef<HTMLDivElement | null>(null)
  const quickCreateRef = useRef<HTMLDivElement | null>(null)
  const pendingHandoffsCount = usePendingHandoffsCount()
  const pendingHandoffsRef = useRef(pendingHandoffsCount)
  pendingHandoffsRef.current = pendingHandoffsCount
  const canSearchTeamReminders = useMemo(() => {
    const r = String(me?.role || '').trim().toLowerCase()
    return ['administrator', 'supervisor', 'superadmin', 'admin', 'manager'].includes(r)
  }, [me?.role])
  const canInboxDeepLink = useMemo(
    () => canUseCommunicationsFeature('messages') || canUseCommunicationsFeature('email'),
    [canUseCommunicationsFeature],
  )
  const [commPollKey, setCommPollKey] = useState(0)
  const [ownCompanies, setOwnCompanies] = useState<Array<{ id: string; name: string }>>([])
  const [activeOwnCompanyId, setActiveOwnCompanyId] = useState<string | null>(() => ownCompanySettings.get())

  useEffect(() => {
    let cancelled = false
    if (!me?.tenant_id) return
    ;(async () => {
      try {
        const res = await listOwnCompanies()
        const items = Array.isArray((res as any)?.items) ? (res as any).items : []
        if (cancelled) return
        setOwnCompanies(items.map((x: any) => ({ id: String(x.id), name: String(x.name || x.id) })))
        const active = String((res as any)?.active_own_company_id || '').trim() || ownCompanySettings.get()
        if (active) {
          setActiveOwnCompanyId(active)
          ownCompanySettings.set(active)
        } else if (items.length > 0) {
          setActiveOwnCompanyId(String(items[0].id))
          ownCompanySettings.set(String(items[0].id))
        }
      } catch {
        if (!cancelled) setOwnCompanies([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [me?.tenant_id])

  const notificationRank = (item: NotificationItem): number => {
    if (item.is_read) return 0
    const payload = (item.payload || {}) as Record<string, any>
    const eventType = String(item.event_type || '').toLowerCase()
    const severity = String(payload.severity || '').toLowerCase()
    const requiresAction = Boolean(payload.requires_action)
    const group = getNotificationUosGroup(item)
    const tier = getNotificationAttentionTier(item)
    let score = 0
    if (tier === 'critical') score += 120
    else if (tier === 'high') score += 60
    if (requiresAction) score += 100
    if (group === 'sla') score += 90
    if (eventType === 'communications_sla_overdue') score += 90
    if (eventType === 'communications_thread_escalated') score += 88
    if (severity === 'high') score += 40
    else if (severity === 'medium') score += 20
    else if (severity === 'low') score += 5
    if (group === 'tasks') score += 15
    if (group === 'messages') score += 10
    return score
  }

  const prioritizeNotifications = (items: NotificationItem[]): NotificationItem[] => {
    return [...items].sort((a, b) => {
      const rankDiff = notificationRank(b) - notificationRank(a)
      if (rankDiff !== 0) return rankDiff
      return Date.parse(b.created_at || '') - Date.parse(a.created_at || '')
    })
  }

  const initials = useMemo(() => {
    if (!me) return 'HF'
    const first = (me.first_name || me.full_name || '').charAt(0)
    const last = (me.last_name || '').charAt(0)
    return (first + last || me.email?.slice(0, 2) || 'HF').toUpperCase()
  }, [me])

  const isTrialTenant = String(tenant?.status || '').trim().toLowerCase() === 'trial'
  const { entityPlural: clientsNavLabel } = useBusinessTerminology()

  const openLang = () => setLangOpen((v) => !v)
  const pickLang = (next: LocaleCode) => {
    setLocale(next)
    setLangOpen(false)
  }

  const getNotificationTitle = (item: NotificationItem): string => {
    const maybeTranslateKey = (value: string): string => {
      const v = String(value || '').trim()
      if (!v) return ''
      if (/^(app|common)\./.test(v)) {
        const localized = t(v as any, { defaultValue: '' })
        if (localized && localized !== v) return localized
      }
      return v
    }
    const eventType = String(item.event_type || '').trim().toLowerCase()
    if (eventType === 'handoff_requested') {
      return t('app.notifications.handoff_requested_title')
    }
    if (eventType === 'handoff_accepted') {
      return t('app.notifications.handoff_accepted_title')
    }
    if (eventType === 'communications_sla_overdue') {
      return t('app.notifications.communications_sla_overdue_title')
    }
    if (eventType === 'communications_thread_escalated') {
      return t('app.notifications.communications_thread_escalated_title')
    }
    if (typeof item.payload?.title === 'string' && item.payload.title.trim()) {
      return maybeTranslateKey(item.payload.title)
    }
    const localized = t(`app.notifications.event_types.${eventType}` as any, { defaultValue: '' })
    if (localized && localized !== `app.notifications.event_types.${eventType}`) {
      return localized
    }
    return humanizeEventType(eventType || 'notification')
  }

  const getNotificationDescription = (item: NotificationItem): string => {
    const payload = (item.payload || {}) as Record<string, any>
    const raw = String(payload.description || '').trim()
    if (!raw) return ''
    if (/^(app|common)\./.test(raw)) {
      const localized = t(raw as any, { defaultValue: '' })
      if (localized && localized !== raw) return localized
    }
    return raw
  }

  const unreadByGroup = useMemo(() => {
    const acc: Record<NotificationUosGroup, number> = { sla: 0, tasks: 0, messages: 0, system: 0 }
    for (const i of notifItems) {
      if (i.is_read) continue
      acc[getNotificationUosGroup(i)] += 1
    }
    return acc
  }, [notifItems])

  const visibleNotifItems = useMemo(() => {
    if (notifFeedMode === 'all') return notifItems
    return notifItems.filter((i) => getNotificationUosGroup(i) === notifFeedMode)
  }, [notifFeedMode, notifItems])

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      if (!notifOpen) return
      if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
        setNotifOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [notifOpen])

  useEffect(() => {
    const onVis = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
        setCommPollKey((k) => k + 1)
      }
    }
    document.addEventListener('visibilitychange', onVis)
    return () => document.removeEventListener('visibilitychange', onVis)
  }, [])

  useEffect(() => {
    const onCommUnreadSync = () => setCommPollKey((k) => k + 1)
    window.addEventListener('hf:communications-unread-sync', onCommUnreadSync)
    return () => window.removeEventListener('hf:communications-unread-sync', onCommUnreadSync)
  }, [])

  useEffect(() => {
    if (!can('notifications.view')) return
    let cancelled = false
    let timeout: number

    const fetchCount = async () => {
      try {
        try {
          await reconcileCommunicationThreadUnread({ limit: 5000 })
        } catch {
          // keep polling even when reconcile is temporarily unavailable
        }
        const [notifData, commData] = await Promise.all([
          listNotifications({ includeRead: false, limit: 100, scope: 'direct' }) as Promise<NotificationListResponse>,
          listCommunicationThreads({ limit: 500 }).catch(() => ({ items: [], total: 0 })),
        ])
        const data = notifData
        if (!cancelled) {
          const items = Array.isArray(data?.items) ? data.items : []
          lastUnreadNotificationsRef.current = items
          setBellAttentionCount(computeBellAttentionCount(items, pendingHandoffsRef.current))
          const threadItems = Array.isArray((commData as any)?.items)
            ? (commData as any).items.filter(
                (th: any) => !th?.is_archived && String(th?.status || '').toLowerCase() !== 'deleted',
              )
            : []
          /** Badge = conversations with any unread, not sum of per-thread counters (avoids inflated 99+). */
          const emailUnread = threadItems.filter(
            (th: any) =>
              String(th?.channel || '').toLowerCase() === 'email' && Number(th?.unread_count || 0) > 0,
          ).length
          const msgUnread = threadItems.filter(
            (th: any) =>
              String(th?.channel || '').toLowerCase() !== 'email' && Number(th?.unread_count || 0) > 0,
          ).length
          setEmailUnreadCount(emailUnread)
          setMessagesUnreadCount(msgUnread)
          const toastCandidates = items.filter((item) => {
            if (item.is_read) return false
            if (!item.id) return false
            if (shownNotificationIdsRef.current.has(String(item.id))) return false
            return ['reminder_due', 'reminder_overdue', 'handoff_requested'].includes(String(item.event_type || '').toLowerCase())
          })
          toastCandidates.slice(0, 1).forEach((evt) => {
            shownNotificationIdsRef.current.add(String(evt.id))
            const title = getNotificationTitle(evt)
            const desc = getNotificationDescription(evt) || String(evt.payload?.entity_type || evt.event_type || '')
            notify({ title, description: desc, variant: evt.event_type === 'reminder_overdue' ? 'error' : 'info' })
          })
          setNotifItems(prioritizeNotifications(items).slice(0, 20))
        }
      } catch (err) {
        if (!cancelled) console.warn('[Topbar] reminders count failed', err)
      } finally {
        if (!cancelled) {
          timeout = window.setTimeout(fetchCount, 60_000)
        }
      }
    }

    fetchCount()

    return () => {
      cancelled = true
      window.clearTimeout(timeout)
    }
  }, [can, commPollKey, notify, t])

  useEffect(() => {
    setBellAttentionCount(
      computeBellAttentionCount(lastUnreadNotificationsRef.current, pendingHandoffsCount),
    )
  }, [pendingHandoffsCount])

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      if (!menuOpen) return
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [menuOpen])

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      if (!langOpen) return
      if (langRef.current && !langRef.current.contains(event.target as Node)) {
        setLangOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [langOpen])

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      if (!quickCreateOpen) return
      if (quickCreateRef.current && !quickCreateRef.current.contains(event.target as Node)) {
        setQuickCreateOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [quickCreateOpen])

  useEffect(() => {
    const onMessagesUnreadSync = (event: Event) => {
      const custom = event as CustomEvent<{ unread?: number }>
      const unread = Math.max(0, Number(custom?.detail?.unread || 0))
      setMessagesUnreadCount(unread)
    }
    window.addEventListener('hf:messages-unread-sync', onMessagesUnreadSync as EventListener)
    return () => window.removeEventListener('hf:messages-unread-sync', onMessagesUnreadSync as EventListener)
  }, [])

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setQuickCreateOpen(false)
        setSearchOpen(true)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  useEffect(() => {
    if (!quickCreateOpen) return
    const onEsc = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setQuickCreateOpen(false)
    }
    window.addEventListener('keydown', onEsc)
    return () => window.removeEventListener('keydown', onEsc)
  }, [quickCreateOpen])

  const quickTargets = useMemo(() => {
    type Target = { key: string; labelKey: string; path: string }
    const items: Target[] = []
    if (can('candidates.view')) {
      items.push({ key: 'candidates', labelKey: 'app.nav.items.candidates', path: CRM_APP_PATHS.candidates })
    }
    if (can('companies.view')) {
      items.push({ key: 'companies', labelKey: 'app.nav.items.clients', path: CRM_APP_PATHS.clientsDirectory })
    }
    if (can('vacancies.view')) {
      items.push({ key: 'vacancies', labelKey: 'app.nav.items.vacancies', path: CRM_APP_PATHS.vacancies })
    }
    if (can('services.view')) {
      items.push({ key: 'orders', labelKey: 'app.nav.items.orders', path: CRM_APP_PATHS.orders })
      items.push({ key: 'invoices', labelKey: 'app.nav.items.invoices', path: CRM_APP_PATHS.invoices })
    }
    if (can('leads.view')) {
      items.push({ key: 'leads', labelKey: 'app.nav.items.leads', path: CRM_APP_PATHS.leads })
    }
    if (can('documents.manage')) {
      items.push({ key: 'documents', labelKey: 'app.nav.items.documents', path: CRM_APP_PATHS.documents })
    }
    if (can('notifications.view')) {
      items.push({ key: 'tasks', labelKey: 'app.nav.items.tasks', path: CRM_APP_PATHS.tasks })
      items.push({ key: 'inbox', labelKey: 'app.nav.items.inbox', path: CRM_APP_PATHS.inbox })
      if (canUseCommunicationsFeature('calendar')) {
        items.push({ key: 'calendar', labelKey: 'app.nav.items.calendar', path: CRM_APP_PATHS.calendar })
      }
      if (!isClientTenant) {
        items.push({
          key: 'automations',
          labelKey: 'app.nav.items.automations',
          path: CRM_APP_PATHS.automations,
        })
      }
    }
    return items
  }, [can, canUseCommunicationsFeature, isClientTenant])

  const quickCreateItems = useMemo(() => {
    type Item = { key: string; to: string; labelKey: string }
    const items: Item[] = []
    if (can('candidates.manage')) {
      items.push({ key: 'candidate', to: CRM_APP_PATHS.candidateNew, labelKey: 'app.topbar.quick_create.candidate' })
    }
    if (can('companies.manage')) {
      items.push({ key: 'client', to: CRM_APP_PATHS.clientNew, labelKey: 'app.topbar.quick_create.client' })
    }
    if (can('vacancies.view')) {
      items.push({ key: 'vacancy', to: CRM_APP_PATHS.vacancyNew, labelKey: 'app.topbar.quick_create.vacancy' })
    }
    if (can('services.view') && can('services.orders.manage')) {
      items.push({ key: 'order', to: CRM_APP_PATHS.orders, labelKey: 'app.topbar.quick_create.order' })
    }
    if (can('notifications.view')) {
      items.push({ key: 'task', to: CRM_APP_PATHS.tasks, labelKey: 'app.topbar.quick_create.task' })
    }
    if (can('notifications.view') && canUseCommunicationsFeature('calendar')) {
      items.push({ key: 'meeting', to: CRM_APP_PATHS.calendar, labelKey: 'app.topbar.quick_create.meeting' })
    }
    if (can('services.view')) {
      items.push({ key: 'invoice', to: CRM_APP_PATHS.invoiceNew, labelKey: 'app.topbar.quick_create.invoice' })
    }
    return items
  }, [can, canUseCommunicationsFeature])

  const loadNotifications = useMemo(() => {
    return async () => {
      if (!can('notifications.view')) return
      setNotifLoading(true)
      setNotifError(null)
      try {
        try {
          await reconcileNotifications()
        } catch {
          // ignore reconcile errors; regular loading still works
        }
        const data = (await listNotifications({ includeRead: true, limit: 20, scope: 'direct' })) as NotificationListResponse
        const items = Array.isArray(data?.items) ? data.items : []
        setNotifItems(prioritizeNotifications(items))
      } catch (err) {
        setNotifError(t('app.reminders.errors.load'))
      } finally {
        setNotifLoading(false)
      }
    }
  }, [can, t])

  const reconcileAndReloadNotifications = async () => {
    if (!can('notifications.view')) return
    setNotifLoading(true)
    setNotifError(null)
    try {
      await reconcileNotifications()
      const unreadData = (await listNotifications({
        includeRead: false,
        limit: 100,
        scope: 'direct',
      })) as NotificationListResponse
      const unreadItems = Array.isArray(unreadData?.items) ? unreadData.items : []
      lastUnreadNotificationsRef.current = unreadItems
      setBellAttentionCount(computeBellAttentionCount(unreadItems, pendingHandoffsCount))
      const data = (await listNotifications({ includeRead: true, limit: 20, scope: 'direct' })) as NotificationListResponse
      const items = Array.isArray(data?.items) ? data.items : []
      setNotifItems(prioritizeNotifications(items))
    } catch {
      setNotifError(t('app.reminders.errors.load'))
    } finally {
      setNotifLoading(false)
    }
  }

  const navigateToResult = (result: GlobalSearchResult) => {
    setSearchOpen(false)
    setSearchQuery('')
    navigate(result.link)
  }

  const toggleNotifications = () => {
    const next = !notifOpen
    setNotifOpen(next)
    if (next) void loadNotifications()
  }

  const markAllRead = async () => {
    try {
      await markNotificationsRead({ markAll: true })
      lastUnreadNotificationsRef.current = []
      setBellAttentionCount(computeBellAttentionCount([], pendingHandoffsCount))
      setNotifItems((prev) => prev.map((i) => ({ ...i, is_read: true })))
    } catch {
      // ignore
    }
  }

  const handleSubmitSearch = () => {
    if (searchResults.length > 0) {
      navigateToResult(searchResults[0])
      return
    }
    if (searchQuery.trim()) {
      const fallbackPath = quickTargets[0]?.path ?? CRM_APP_PATHS.appShellPrefix
      navigate(appendSearchQueryParam(fallbackPath, searchQuery.trim()))
      setSearchOpen(false)
      setSearchQuery('')
    }
  }

  useEffect(() => {
    if (!searchOpen) return
    const trimmed = searchQuery.trim()
    if (trimmed.length < 2) {
      setSearchResults([])
      setSearchError(null)
      setSearchLoading(false)
      return
    }
    setSearchLoading(true)
    setSearchError(null)
    const controller = new AbortController()
    searchGlobal(trimmed, controller.signal, {
      reminderAssigneeScope: canSearchTeamReminders ? 'team' : 'mine',
    })
      .then((results) => {
        setSearchResults(results)
      })
      .catch((err: any) => {
        if (controller.signal.aborted) return
        console.warn('[Topbar] global search failed', err)
        setSearchError(err?.message || t('app.topbar.search.error'))
        setSearchResults([])
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setSearchLoading(false)
        }
      })
    return () => controller.abort()
  }, [searchQuery, searchOpen, t, canSearchTeamReminders])

  return (
    <>
      <header
        className={[
          'relative z-50 flex items-center justify-between gap-2 border-b border-slate-200 bg-white shadow-sm',
          compact ? 'h-14 px-2 sm:px-3 lg:px-4' : 'h-16 px-3 sm:px-4 lg:px-6',
        ].join(' ')}
      >
        <div className="flex min-w-0 items-center gap-2 sm:gap-3">
          <button
            type="button"
            className={[
              'rounded-md text-slate-600 transition hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
              compact ? 'p-1.5' : 'p-2',
            ].join(' ')}
            aria-label={t('app.topbar.actions.open_menu')}
            onClick={onToggleSidebar}
          >
            <IconMenu2 size={20} stroke={1.8} />
          </button>
          <img
            src="/logo_hf.svg"
            alt="HostFlow"
            className={compact ? 'h-7 w-auto sm:h-8' : 'h-8 w-auto sm:h-9'}
            loading="lazy"
          />
          {isTrialTenant ? (
            <span
              className="inline-flex items-center rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-amber-800"
              title={t('app.topbar.trial_badge_hint')}
            >
              {t('app.topbar.trial_badge')}
            </span>
          ) : null}
        </div>

        <div className="flex min-w-0 flex-1 items-center justify-end gap-1 sm:gap-2">
          {ownCompanies.length > 0 && (
            <label className="hidden items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-2 py-1.5 text-xs text-slate-700 sm:inline-flex">
              <span className="text-slate-500">{t('app.topbar.own_company')}</span>
              <select
                className="bg-transparent text-xs font-semibold text-slate-800 outline-none"
                value={activeOwnCompanyId || ''}
                onChange={(e) => {
                  const next = e.target.value
                  setActiveOwnCompanyId(next)
                  ownCompanySettings.set(next)
                  void setActiveOwnCompany(next).catch(() => {})
                }}
              >
                {ownCompanies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          {canReturnToPlatform && (
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-md border border-amber-300 bg-amber-50 px-2 py-2 text-xs font-semibold text-amber-800 transition hover:bg-amber-100 sm:gap-2 sm:px-3 sm:text-sm"
              onClick={() => {
                void restorePlatformSession()
              }}
            >
              <IconLayoutSidebarLeftExpand size={14} stroke={1.9} />
              <span className="hidden sm:inline">{t('app.topbar.actions.return_to_platform')}</span>
            </button>
          )}
          <TopbarNbaMenu />
          <button
            type="button"
            className={[
              'hidden items-center gap-2 rounded-md border border-slate-200 px-4 text-sm text-slate-600 transition hover:bg-slate-50 lg:inline-flex',
              compact ? 'py-1.5' : 'py-2',
            ].join(' ')}
            onClick={() => {
              setQuickCreateOpen(false)
              setSearchOpen(true)
            }}
          >
            <span className="text-slate-400">{SEARCH_SHORTCUT_HINT}</span>
            <span>{t('app.topbar.search.open')}</span>
          </button>

          {quickCreateItems.length > 0 ? (
            <div className="relative" ref={quickCreateRef}>
              <button
                type="button"
                className={[
                  'inline-flex items-center gap-1.5 rounded-md border border-brand-200 bg-brand-50 px-2.5 text-sm font-semibold text-brand-900 transition hover:bg-brand-100 sm:gap-2 sm:px-3',
                  compact ? 'py-1.5' : 'py-2',
                ].join(' ')}
                aria-haspopup="menu"
                aria-expanded={quickCreateOpen}
                title={t('app.topbar.quick_create.button')}
                onClick={() => setQuickCreateOpen((v) => !v)}
              >
                <IconPlus size={18} stroke={1.9} />
                <span className="hidden sm:inline">{t('app.topbar.quick_create.button')}</span>
              </button>
              {quickCreateOpen ? (
                <div
                  className="absolute right-0 z-50 mt-2 w-[min(18rem,calc(100vw-2rem))] overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-2xl"
                  role="menu"
                  aria-label={t('app.topbar.quick_create.menu_label')}
                >
                  {quickCreateItems.map((item) => (
                    <button
                      key={item.key}
                      type="button"
                      role="menuitem"
                      className="flex w-full px-4 py-2.5 text-left text-sm text-slate-800 transition hover:bg-slate-50"
                      onClick={() => {
                        setQuickCreateOpen(false)
                        navigate(item.to)
                      }}
                    >
                      {t(item.labelKey as any)}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}

          {/* Кнопка меню кандидатов - показывается только на странице кандидатов */}
          <CandidatesMenuButton t={t} />

          <div className="relative hidden sm:block" ref={langRef}>
            <button
              type="button"
              className={[
                'inline-flex items-center rounded-md border border-slate-200 px-3 text-sm font-semibold uppercase text-slate-700 transition hover:bg-slate-50',
                compact ? 'py-1.5' : 'py-2',
              ].join(' ')}
              onClick={openLang}
              aria-haspopup="menu"
              aria-expanded={langOpen}
              title={t('app.topbar.actions.language')}
            >
              {locale.toUpperCase()}
            </button>
            {langOpen && (
              <div className="absolute right-0 z-50 mt-2 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl">
                <div className="flex items-center gap-1 bg-slate-50 p-1">
                  {SUPPORTED_LOCALES.map((code) => (
                    <button
                      key={code}
                      type="button"
                      className={[
                        'rounded-lg px-3 py-1.5 text-xs font-semibold uppercase transition',
                        locale === code ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-200',
                      ].join(' ')}
                      onClick={() => pickLang(code)}
                    >
                      {code}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {can('notifications.view') && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="relative rounded-full border border-slate-200 p-2 text-slate-700 transition hover:bg-slate-50"
                aria-label={t('app.nav.items.messages_inbox')}
                onClick={() => navigate(CRM_APP_PATHS.inboxMessagesScoped)}
              >
                <IconMessageCircle size={20} stroke={1.8} />
                {messagesUnreadCount > 0 && (
                  <span className="absolute -right-1 -top-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-sky-500 px-1 text-[11px] font-semibold text-white">
                    {formatThreadUnreadBadge(messagesUnreadCount)}
                  </span>
                )}
              </button>

              <button
                type="button"
                className="relative hidden rounded-full border border-slate-200 p-2 text-slate-700 transition hover:bg-slate-50 sm:inline-flex"
                aria-label={t('app.nav.items.email_inbox')}
                onClick={() => navigate(CRM_APP_PATHS.inboxEmailScoped)}
              >
                <IconMail size={20} stroke={1.8} />
                {emailUnreadCount > 0 && (
                  <span className="absolute -right-1 -top-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-indigo-500 px-1 text-[11px] font-semibold text-white">
                    {formatThreadUnreadBadge(emailUnreadCount)}
                  </span>
                )}
              </button>

              <div className="relative" ref={notifRef}>
                <button
                  type="button"
                  className="relative rounded-full border border-slate-200 p-2 text-slate-700 transition hover:bg-slate-50"
                  aria-label={
                    bellAttentionCount > 0
                      ? t('app.topbar.actions.notifications_with_urgent', {
                          values: { count: bellAttentionCount },
                        })
                      : t('app.topbar.actions.notifications')
                  }
                  onClick={toggleNotifications}
                >
                  <IconBell size={20} stroke={1.8} />
                  {bellAttentionCount > 0 && (
                    <span className="absolute -right-1 -top-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-rose-500 px-1 text-[11px] font-semibold text-white">
                      {bellAttentionCount}
                    </span>
                  )}
                </button>

                {notifOpen && (
                  <div className="absolute right-0 top-10 z-50 w-[min(96vw,34rem)] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
                    <div className="flex flex-col gap-2 border-b border-slate-100 px-4 py-3">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">
                          {t('app.topbar.notifications.title')}
                        </p>
                        <p className="text-xs text-slate-500 break-words">
                          {notifLoading
                            ? t('common.loading')
                            : t('app.topbar.notifications.subtitle', {
                                values: {
                                  total: notifItems.length,
                                  unread: notifItems.filter((i) => !i.is_read).length,
                                },
                              })}
                        </p>
                        {!notifLoading && (
                          <div className="mt-2 flex flex-wrap items-center gap-2">
                            <span className="rounded-md bg-rose-100 px-2 py-0.5 text-[11px] font-medium text-rose-700">
                              {t('app.topbar.notifications.groups.sla')}: {unreadByGroup.sla}
                            </span>
                            <span className="rounded-md bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800">
                              {t('app.topbar.notifications.groups.tasks')}: {unreadByGroup.tasks}
                            </span>
                            <span className="rounded-md bg-sky-100 px-2 py-0.5 text-[11px] font-medium text-sky-800">
                              {t('app.topbar.notifications.groups.messages')}:{' '}
                              {unreadByGroup.messages}
                            </span>
                            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700">
                              {t('app.topbar.notifications.groups.system')}: {unreadByGroup.system}
                            </span>
                          </div>
                        )}
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <button
                          type="button"
                          className="btn-secondary btn-xs"
                          onClick={() => void reconcileAndReloadNotifications()}
                          disabled={notifLoading}
                        >
                          {t('app.reminders.actions.sync')}
                        </button>
                        <button
                          type="button"
                          className="btn-secondary btn-xs"
                          onClick={() => void loadNotifications()}
                          disabled={notifLoading}
                        >
                          {t('app.reminders.actions.refresh')}
                        </button>
                        <button type="button" className="btn-secondary btn-xs" onClick={markAllRead}>
                          {t('app.reminders.actions.mark_all')}
                        </button>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <button
                          type="button"
                          className={[
                            'rounded-md px-2.5 py-1 text-[11px] font-medium',
                            notifFeedMode === 'all' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
                          ].join(' ')}
                          onClick={() => setNotifFeedMode('all')}
                        >
                          {t('app.topbar.notifications.groups.all')} ({notifItems.length})
                        </button>
                        <button
                          type="button"
                          className={[
                            'rounded-md px-2.5 py-1 text-[11px] font-medium',
                            notifFeedMode === 'sla' ? 'bg-rose-600 text-white' : 'bg-rose-100 text-rose-700 hover:bg-rose-200',
                          ].join(' ')}
                          onClick={() => setNotifFeedMode('sla')}
                        >
                          {t('app.topbar.notifications.groups.sla')} ({unreadByGroup.sla})
                        </button>
                        <button
                          type="button"
                          className={[
                            'rounded-md px-2.5 py-1 text-[11px] font-medium',
                            notifFeedMode === 'tasks' ? 'bg-amber-600 text-white' : 'bg-amber-100 text-amber-800 hover:bg-amber-200',
                          ].join(' ')}
                          onClick={() => setNotifFeedMode('tasks')}
                        >
                          {t('app.topbar.notifications.groups.tasks')} ({unreadByGroup.tasks})
                        </button>
                        <button
                          type="button"
                          className={[
                            'rounded-md px-2.5 py-1 text-[11px] font-medium',
                            notifFeedMode === 'messages'
                              ? 'bg-sky-600 text-white'
                              : 'bg-sky-100 text-sky-800 hover:bg-sky-200',
                          ].join(' ')}
                          onClick={() => setNotifFeedMode('messages')}
                        >
                          {t('app.topbar.notifications.groups.messages')} ({unreadByGroup.messages})
                        </button>
                        <button
                          type="button"
                          className={[
                            'rounded-md px-2.5 py-1 text-[11px] font-medium',
                            notifFeedMode === 'system' ? 'bg-slate-700 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
                          ].join(' ')}
                          onClick={() => setNotifFeedMode('system')}
                        >
                          {t('app.topbar.notifications.groups.system')} ({unreadByGroup.system})
                        </button>
                      </div>
                    </div>
                    <div className="max-h-[min(64vh,36rem)] space-y-2 overflow-auto p-3">
                      {notifError && <p className="text-xs text-rose-600">{notifError}</p>}
                      {!notifError && visibleNotifItems.length === 0 && !notifLoading && (
                        <p className="text-sm text-slate-500">{t('app.reminders.states.empty')}</p>
                      )}
                      {visibleNotifItems.map((item) => {
                        const dateLocale = localeMap[locale as keyof typeof localeMap] || enUS
                        const when = item.created_at
                          ? formatDistanceToNow(new Date(item.created_at), { addSuffix: true, locale: dateLocale })
                          : ''
                        const title = getNotificationTitle(item)
                        const isHandoff = item.event_type === 'handoff_requested' || item.event_type === 'handoff_accepted'
                        const uosGroup = getNotificationUosGroup(item)
                        const attentionTier = getNotificationAttentionTier(item)
                        const attentionTierLabelKey =
                          attentionTier === 'critical'
                            ? 'app.topbar.notifications.tier.critical'
                            : attentionTier === 'high'
                              ? 'app.topbar.notifications.tier.high'
                              : 'app.topbar.notifications.tier.normal'
                        const description = getNotificationDescription(item)
                        const threadId = notificationThreadId(item)
                        const threadChannel = notificationThreadChannel(item)
                        return (
                          <div
                            key={item.id}
                            className={[
                              'rounded-xl border border-slate-100 bg-white px-3 py-2 shadow-sm',
                              item.is_read ? 'opacity-80' : 'border-brand-100',
                            ].join(' ')}
                          >
                            <div className="flex min-w-0 items-start justify-between gap-2">
                              <div className="min-w-0 space-y-1">
                                <div className="flex flex-wrap items-center gap-2">
                                  {uosGroup === 'sla' ? (
                                    <span className="rounded-md bg-rose-100 px-2 py-0.5 text-[11px] font-medium text-rose-700">
                                      {t('app.topbar.notifications.groups.sla')}
                                    </span>
                                  ) : uosGroup === 'tasks' ? (
                                    <span className="rounded-md bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800">
                                      {t('app.topbar.notifications.groups.tasks')}
                                    </span>
                                  ) : uosGroup === 'messages' ? (
                                    <span className="rounded-md bg-sky-100 px-2 py-0.5 text-[11px] font-medium text-sky-800">
                                      {t('app.topbar.notifications.groups.messages')}
                                    </span>
                                  ) : (
                                    <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700">
                                      {t('app.topbar.notifications.groups.system')}
                                    </span>
                                  )}
                                  <NotificationAttentionTierChip
                                    tier={attentionTier}
                                    isRead={Boolean(item.is_read)}
                                    label={t(attentionTierLabelKey)}
                                  />
                                  <p className="max-w-full break-words text-sm font-semibold leading-snug text-slate-900 line-clamp-2">{title}</p>
                                </div>
                                {description && (
                                  <p className="max-w-full break-words text-xs text-slate-600 line-clamp-3">{description}</p>
                                )}
                                <p className="text-[11px] uppercase tracking-wide text-slate-400">{when}</p>
                                {isHandoff && (
                                  <button
                                    type="button"
                                    className="mt-1 text-xs font-medium text-brand-600 hover:text-brand-700"
                                    onClick={() => {
                                      setNotifOpen(false)
                                      navigate(CRM_APP_PATHS.procesowani)
                                    }}
                                  >
                                    {t('app.notifications.view_handoffs')}
                                  </button>
                                )}
                                {uosGroup === 'sla' && threadId && canInboxDeepLink && (
                                  <button
                                    type="button"
                                    className="mt-1 text-xs font-medium text-brand-700 hover:text-brand-800"
                                    onClick={() => {
                                      setNotifOpen(false)
                                      navigate(buildInboxThreadPath(threadId, threadChannel ? { channel: threadChannel } : undefined))
                                    }}
                                  >
                                    {t('app.topbar.notifications.open_in_inbox')}
                                  </button>
                                )}
                                {uosGroup === 'sla' && (
                                  <button
                                    type="button"
                                    className="mt-1 text-xs font-medium text-rose-700 hover:text-rose-800"
                                    onClick={() => {
                                      setNotifOpen(false)
                                      navigate(CRM_APP_PATHS.slaIncidents)
                                    }}
                                  >
                                    {t('app.notifications.open_sla_incidents')}
                                  </button>
                                )}
                                {uosGroup === 'messages' && threadId && (
                                  <button
                                    type="button"
                                    className="mt-1 text-xs font-medium text-sky-700 hover:text-sky-800"
                                    onClick={() => {
                                      setNotifOpen(false)
                                      if (canInboxDeepLink) {
                                        navigate(
                                          buildInboxThreadPath(threadId, threadChannel ? { channel: threadChannel } : undefined),
                                        )
                                      } else {
                                        navigate(communicationsThreadPath(threadId))
                                      }
                                    }}
                                  >
                                    {t('app.topbar.notifications.open_thread')}
                                  </button>
                                )}
                                {uosGroup === 'tasks' && (
                                  <button
                                    type="button"
                                    className="mt-1 text-xs font-medium text-amber-800 hover:text-amber-900"
                                    onClick={() => {
                                      setNotifOpen(false)
                                      navigate(CRM_APP_PATHS.tasks)
                                    }}
                                  >
                                    {t('app.reminders.actions.open_page')}
                                  </button>
                                )}
                              </div>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 p-3">
                      {pendingHandoffsCount > 0 && (
                        <button
                          type="button"
                          className="text-sm font-semibold text-brand-700 hover:text-brand-800"
                          onClick={() => {
                            setNotifOpen(false)
                            navigate(CRM_APP_PATHS.procesowani)
                          }}
                        >
                          {t('app.notifications.view_handoffs')}{' '}
                          ({pendingHandoffsCount})
                        </button>
                      )}
                      <div className="ml-auto flex flex-wrap items-center justify-end gap-3">
                        {canInboxDeepLink && (
                          <button
                            type="button"
                            className="text-sm font-semibold text-brand-700 hover:text-brand-800"
                            onClick={() => {
                              setNotifOpen(false)
                              navigate(CRM_APP_PATHS.inbox)
                            }}
                          >
                            {t('app.nav.items.inbox')}
                          </button>
                        )}
                        <button
                          type="button"
                          className="text-sm font-semibold text-rose-700 hover:text-rose-800"
                          onClick={() => {
                            setNotifOpen(false)
                            navigate(CRM_APP_PATHS.slaIncidents)
                          }}
                        >
                          {t('app.notifications.open_sla_incidents')}
                        </button>
                        <button
                          type="button"
                          className="text-sm font-semibold text-slate-700 hover:text-slate-800"
                          onClick={() => {
                            setNotifOpen(false)
                            navigate(CRM_APP_PATHS.tasks)
                          }}
                        >
                          {t('app.reminders.actions.open_page')}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="relative" ref={menuRef}>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-2 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 sm:px-3"
              onClick={() => setMenuOpen((prev) => !prev)}
            >
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-900 text-white">
                {initials}
              </span>
              <span className="hidden md:inline">{me?.full_name || me?.email || t('app.shell.actions.profile')}</span>
            </button>
            {menuOpen && (
              <div className="absolute right-0 z-[100] mt-2 w-[min(96vw,320px)] overflow-hidden rounded-xl border border-slate-200 bg-white py-2 text-sm shadow-2xl">
                <div className="border-b border-slate-100 px-4 py-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                    {t('app.shell.account.my_account')}
                  </p>
                  <button
                    type="button"
                    className="mt-1 flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-slate-700 transition hover:bg-slate-50"
                    onClick={() => {
                      setMenuOpen(false)
                      navigate(CRM_APP_PATHS.profile)
                    }}
                  >
                    <IconUserCircle size={16} />
                    <span>{t('app.shell.actions.profile')}</span>
                  </button>
                </div>

                <div className="px-4 py-2">
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-rose-600 transition hover:bg-rose-50"
                    onClick={() => {
                      setMenuOpen(false)
                      onLogout()
                    }}
                  >
                    <IconLogout size={16} />
                    <span>{t('app.shell.actions.logout')}</span>
                  </button>
                </div>
              </div>
            )}
          </div>

        </div>
      </header>

      {searchOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 p-4" role="dialog" aria-modal="true">
          <div className="mx-auto max-w-2xl rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-center gap-3">
              <input
                autoFocus
                className="input flex-1"
                placeholder={t('app.topbar.search.placeholder')}
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    handleSubmitSearch()
                  } else if (event.key === 'Escape') {
                    setSearchOpen(false)
                  }
                }}
              />
              <button
                type="button"
                className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-50"
                onClick={() => setSearchOpen(false)}
              >
                {t('common.actions.close')}
              </button>
            </div>

            <div className="mt-4 space-y-4">
              {searchQuery.trim().length < 2 ? (
                <p className="text-sm text-slate-500">{t('app.topbar.search.hint')}</p>
              ) : (
                <>
                  {searchLoading && <div className="text-sm text-slate-500">{t('app.topbar.search.loading')}</div>}
                  {!searchLoading && searchError && (
                    <div className="text-sm text-rose-600">{searchError}</div>
                  )}
                  {!searchLoading && !searchError && searchResults.length === 0 && (
                    <div className="text-sm text-slate-500">{t('app.topbar.search.empty')}</div>
                  )}
                  <ul className="divide-y divide-slate-100 rounded-lg border border-slate-100">
                    {searchResults.map((result) => (
                      <li key={`${result.type}-${result.id}`}>
                        <button
                          type="button"
                          className="flex w-full flex-col items-start gap-1 px-4 py-3 text-left transition hover:bg-slate-50"
                          onClick={() => navigateToResult(result)}
                        >
                          <span className="text-xs uppercase text-slate-400">
                            {t(RESULT_LABEL_KEYS[result.type])}
                          </span>
                          <span className="text-sm font-semibold text-slate-900">{result.title}</span>
                          {result.subtitle && (
                            <span className="text-xs text-slate-500">{result.subtitle}</span>
                          )}
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}

              <div className="grid gap-2 grid-cols-2 sm:grid-cols-3 xl:grid-cols-4">
                {quickTargets.map((target) => (
                  <button
                    key={target.key}
                    type="button"
                    className="rounded-lg border border-slate-200 px-4 py-3 text-left text-sm text-slate-700 transition hover:border-brand-500 hover:text-brand-900"
                    onClick={() => {
                      const trimmed = searchQuery.trim()
                      setSearchOpen(false)
                      setSearchQuery('')
                      navigate(appendSearchQueryParam(target.path, trimmed))
                    }}
                  >
                    <div className="text-xs uppercase text-slate-400">{t('app.topbar.search.quick_section')}</div>
                    <div className="text-base font-semibold">
                      {target.key === 'companies' ? clientsNavLabel : t(target.labelKey)}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

// Кнопка меню кандидатов - использует события для связи со страницей кандидатов
function CandidatesMenuButton({ t }: { t: (key: string) => string }) {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  // Показываем кнопку только на главной странице кандидатов (не на /new или /:id)
  const isCandidatesPage = location.pathname === CRM_APP_PATHS.candidates

  useEffect(() => {
    if (!isCandidatesPage) return

    // Слушаем события от страницы кандидатов
    const handleSidebarToggle = (e: CustomEvent<{ open: boolean }>) => {
      setSidebarOpen(e.detail.open)
    }

    const handleSidebarState = (e: CustomEvent<{ open: boolean }>) => {
      setSidebarOpen(e.detail.open)
    }

    window.addEventListener('candidates-sidebar-toggle', handleSidebarToggle as EventListener)
    window.addEventListener('candidates-sidebar-state', handleSidebarState as EventListener)

    // Запрашиваем текущее состояние только при монтировании
    window.dispatchEvent(new CustomEvent('candidates-sidebar-request-state'))

    return () => {
      window.removeEventListener('candidates-sidebar-toggle', handleSidebarToggle as EventListener)
      window.removeEventListener('candidates-sidebar-state', handleSidebarState as EventListener)
    }
  }, [isCandidatesPage])

  const handleClick = () => {
    if (!isCandidatesPage) return
    const newState = !sidebarOpen
    setSidebarOpen(newState)
    // Отправляем событие на страницу кандидатов
    window.dispatchEvent(new CustomEvent('candidates-sidebar-toggle', { detail: { open: newState } }))
  }

  // Показываем кнопку только на главной странице кандидатов
  if (!isCandidatesPage) return null

  return (
    <button
      type="button"
      onClick={handleClick}
      className="flex items-center gap-2 rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-700 transition hover:bg-slate-50"
      title={sidebarOpen ? t('app.candidates.menu.close') : t('app.candidates.menu.open')}
      aria-label={sidebarOpen ? t('app.candidates.menu.close') : t('app.candidates.menu.open')}
    >
      {sidebarOpen ? (
        <>
          <IconX size={18} stroke={2} />
          <span className="hidden sm:inline">{t('app.candidates.menu.close')}</span>
        </>
      ) : (
        <>
          <IconLayoutSidebarLeftExpand size={18} stroke={2} />
          <span className="hidden sm:inline">{t('app.candidates.menu.open')}</span>
        </>
      )}
    </button>
  )
}
