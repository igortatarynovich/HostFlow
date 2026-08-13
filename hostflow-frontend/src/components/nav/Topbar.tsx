import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  IconAlertTriangle,
  IconBell,
  IconBuilding,
  IconChecklist,
  IconHome,
  IconLayoutSidebarLeftExpand,
  IconLogout,
  IconMail,
  IconMenu2,
  IconMessageCircle,
  IconSettings,
  IconUserCircle,
} from '@tabler/icons-react'
import type { TenantSummary, WhoAmI } from '../../api/types'
import { listNotifications, markNotificationsRead, reconcileNotifications } from '../../api/client'
import type { NotificationItem, NotificationListResponse } from '../../api/types'
import { getNotificationAttentionTier, getNotificationUosGroup } from '../../utils/notificationUos'
import {
  notificationThreadChannel,
  notificationThreadId,
  resolveNotificationOpenPath,
} from '../../utils/resolveNotificationOpenPath'
import {
  executeWorkspaceCommand,
  listCommunicationThreads,
  reconcileCommunicationThreadUnread,
  type CommunicationThread,
} from '../../api/communications'
import { useToast } from '../Toast'
import { useCommunicationsAccess } from '../../hooks/useCommunicationsAccess'
import { canUseTeamAssigneeScope } from '../../auth/trustRoles'
import { usePermissions } from '../../hooks/usePermissions'
import { searchGlobal, type GlobalSearchResult } from '../../api/search'
import { useI18n } from '../../i18n'
import { useAuth } from '../../store/useAuth'
import { usePendingHandoffsCount } from '../../hooks/usePendingHandoffsCount'
import { useBusinessTerminology } from '../../hooks/useBusinessTerminology'
import { communicationsThreadPath, CRM_APP_PATHS } from '../../app/crmAppPaths'
import { isPlatformSuperadminRole } from '../../utils/platformSuperadmin'
import { Modal } from '../Modal'
import { TodayTasksPeek } from './TodayTasksPeek'
import { buildInboxThreadPath } from '../../utils/inboxDeepLinks'
import { isEmailThread, threadRecencyMs, threadTitle } from '../communications/InboxUnifiedThreadList'
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

function isBellAttentionNotification(item: NotificationItem): boolean {
  if (item.is_read) return false
  const t = getNotificationAttentionTier(item)
  return t === 'critical' || t === 'high'
}

/** Bell count: urgent notifications + handoffs (max of API pending vs unread handoff notifs — no double count). */

function resolveThreadOpenPath(th: CommunicationThread, canInboxDeepLink: boolean): string | null {
  const id = String(th.id || '').trim()
  if (!id) return null
  if (!canInboxDeepLink) return communicationsThreadPath(id)
  const ch = isEmailThread(th) ? 'email' : 'messages'
  return buildInboxThreadPath(id, { channel: ch })
}

function filterUnreadThreadsForUser(
  threads: CommunicationThread[],
  canUseCommunicationsFeature: (feature: 'email' | 'messages') => boolean,
): CommunicationThread[] {
  return threads.filter((th) => {
    if (th.is_archived || String(th.status || '').toLowerCase() === 'deleted') return false
    if (Number(th.unread_count || 0) <= 0) return false
    if (isEmailThread(th)) return canUseCommunicationsFeature('email')
    return canUseCommunicationsFeature('messages')
  })
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

const REMINDER_BELL_EVENT_TYPES = new Set(['reminder_due', 'reminder_overdue'])

function isReminderBellItem(item: NotificationItem): boolean {
  return REMINDER_BELL_EVENT_TYPES.has(String(item.event_type || '').toLowerCase())
}

function reminderGroupKey(item: NotificationItem): string | null {
  // Only group reminder_due / reminder_overdue rows that carry both
  // entity_type and entity_id. Without an entity we have nothing to roll up.
  if (!isReminderBellItem(item)) return null
  const et = String(item.entity_type || '').trim().toLowerCase()
  const eid = String(item.entity_id || '').trim()
  if (!et || !eid) return null
  return `${et}:${eid}`
}

/**
 * G-9: count reminder bell rows after rolling them up by entity.
 * Non-reminder notifications count 1:1.
 * Reminder rows for the same entity collapse into a single "row".
 */
function countNotifPanelRowsGrouped(items: NotificationItem[]): number {
  const seenGroups = new Set<string>()
  let single = 0
  for (const item of items) {
    if (item.is_read) continue
    const key = reminderGroupKey(item)
    if (key === null) {
      single += 1
      continue
    }
    if (seenGroups.has(key)) continue
    seenGroups.add(key)
    single += 1
  }
  return single
}

function formatThreadUnreadBadge(n: number): string {
  if (n <= 99) return String(n)
  return '99+'
}

// Bell drawer is intentionally lightweight (ADR-012): list + unread count + open/dismiss
// + [Open Notification Center] + [Clear all]. Filtering / sorting / SLA-focus / severity /
// bulk actions live on the Notification Center page, not in this transient overlay.

function isHttpForbidden(err: unknown): boolean {
  return Boolean((err as { response?: { status?: number } } | null)?.response?.status === 403)
}

export function Topbar({ me, tenant, onLogout, onToggleSidebar, compact = false }: TopbarProps) {
  const navigate = useNavigate()
  const { can, isClientTenant, rawRole, presetId } = usePermissions()
  const { canUseCommunicationsFeature, loading: commAccessLoading } = useCommunicationsAccess()
  const { locale, t } = useI18n()
  const { canReturnToPlatform, restorePlatformSession } = useAuth()
  const { notify } = useToast()
  const [notifOpen, setNotifOpen] = useState(false)
  const [notifItems, setNotifItems] = useState<NotificationItem[]>([])
  const [panelThreads, setPanelThreads] = useState<CommunicationThread[]>([])
  const [notifLoading, setNotifLoading] = useState(false)
  const [notifError, setNotifError] = useState<string | null>(null)
  const notifRef = useRef<HTMLDivElement | null>(null)
  const localeMap = { ru, en: enUS, pl }

  const [menuOpen, setMenuOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchResults, setSearchResults] = useState<GlobalSearchResult[]>([])
  const [searchError, setSearchError] = useState<string | null>(null)
  const [bellAttentionCount, setBellAttentionCount] = useState(0)
  const [bellBadgeCount, setBellBadgeCount] = useState(0)
  const shownNotificationIdsRef = useRef<Set<string>>(new Set())
  const lastUnreadNotificationsRef = useRef<NotificationItem[]>([])
  const menuRef = useRef<HTMLDivElement | null>(null)
  /** After server 403, stop hammering threads/reconcile for this session (role/tenant ACL). */
  const commsApiDeniedRef = useRef(false)
  const pendingHandoffsCount = usePendingHandoffsCount()
  const pendingHandoffsRef = useRef(pendingHandoffsCount)
  pendingHandoffsRef.current = pendingHandoffsCount
  const canSearchTeamReminders = useMemo(() => {
    return canUseTeamAssigneeScope({ role: rawRole || me?.role, presetId })
  }, [me?.role, presetId, rawRole])
  const canInboxDeepLink = useMemo(
    () => canUseCommunicationsFeature('messages') || canUseCommunicationsFeature('email'),
    [canUseCommunicationsFeature],
  )
  const [commPollKey, setCommPollKey] = useState(0)
  const [reminderDuePopup, setReminderDuePopup] = useState<NotificationItem | null>(null)

  // Severity / SLA / requires-action ranking used to sort drawer rows; that policy now lives
  // on the Notification Center page (ADR-012). Drawer renders newest-first only — see
  // `unifiedPanelRows` (sorted by sortAt desc).

  const initials = useMemo(() => {
    if (!me) return 'HF'
    const first = (me.first_name || me.full_name || '').charAt(0)
    const last = (me.last_name || '').charAt(0)
    return (first + last || me.email?.slice(0, 2) || 'HF').toUpperCase()
  }, [me])

  const isTrialTenant = String(tenant?.status || '').trim().toLowerCase() === 'trial'
  const isSuperAdmin = isPlatformSuperadminRole(me?.role)
  const { entityPlural: clientsNavLabel } = useBusinessTerminology()

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
    if (eventType === 'lead_public_intake_client') {
      return t('app.notifications.lead_public_intake_client_title')
    }
    if (eventType === 'intake_client_lead_skipped_no_company') {
      return t('app.notifications.intake_client_lead_skipped_no_company_title')
    }
    if (eventType === 'intake.questionnaire.submitted') {
      return t('app.notifications.intake_questionnaire_submitted_title', {
        defaultValue: 'Клиент заполнил анкету',
      })
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
    const eventType = String(item.event_type || '').trim().toLowerCase()
    if (eventType === 'lead_public_intake_client') {
      return t('app.notifications.lead_public_intake_client_desc', {
        values: { name: String(payload.candidate_name || '').trim() || '—' },
      })
    }
    if (eventType === 'intake_client_lead_skipped_no_company') {
      return t('app.notifications.intake_client_lead_skipped_no_company_desc', {
        values: { name: String(payload.candidate_name || '').trim() || '—' },
      })
    }
    if (eventType === 'intake.questionnaire.submitted') {
      const line = String(payload.description || payload.body || '').trim()
      if (line) return line
      const contact = String(payload.contact_name || '').trim() || '—'
      const company = String(payload.company_name || '').trim() || '—'
      return t('app.notifications.intake_questionnaire_submitted_desc', {
        defaultValue: '{contact} — {company}',
        values: { contact, company },
      })
    }
    const raw = String(payload.description || payload.body || '').trim()
    if (!raw) return ''
    if (/^(app|common)\./.test(raw)) {
      const localized = t(raw as any, { defaultValue: '' })
      if (localized && localized !== raw) return localized
    }
    return raw
  }

  const unifiedPanelRows = useMemo(() => {
    type Row =
      | { kind: 'thread'; thread: CommunicationThread; sortAt: number }
      | { kind: 'notif'; item: NotificationItem; sortAt: number }
      | {
          kind: 'notif_group'
          key: string
          representative: NotificationItem
          items: NotificationItem[]
          count: number
          sortAt: number
        }
    const threadIds = new Set(panelThreads.map((t) => t.id))
    const rows: Row[] = panelThreads.map((thread) => ({
      kind: 'thread' as const,
      thread,
      sortAt: threadRecencyMs(thread),
    }))
    // G-9: roll up reminder_due/reminder_overdue rows that share an entity.
    const groupBuckets = new Map<string, NotificationItem[]>()
    const ungrouped: NotificationItem[] = []
    for (const item of notifItems) {
      if (item.is_read) continue
      const tid = notificationThreadId(item)
      if (tid && threadIds.has(tid)) continue
      const key = reminderGroupKey(item)
      if (key === null) {
        ungrouped.push(item)
        continue
      }
      const bucket = groupBuckets.get(key)
      if (bucket) {
        bucket.push(item)
      } else {
        groupBuckets.set(key, [item])
      }
    }
    for (const item of ungrouped) {
      const ms = Date.parse(item.created_at || '') || 0
      rows.push({ kind: 'notif', item, sortAt: ms })
    }
    for (const [key, bucket] of groupBuckets) {
      const sorted = [...bucket].sort(
        (a, b) => (Date.parse(b.created_at || '') || 0) - (Date.parse(a.created_at || '') || 0),
      )
      const representative = sorted[0]
      const sortAt = Date.parse(representative?.created_at || '') || 0
      if (bucket.length === 1) {
        // Single reminder for the entity — render as a normal notif row, no rollup chrome.
        rows.push({ kind: 'notif', item: representative, sortAt })
      } else {
        rows.push({
          kind: 'notif_group',
          key,
          representative,
          items: sorted,
          count: bucket.length,
          sortAt,
        })
      }
    }
    rows.sort((a, b) => b.sortAt - a.sortAt)
    return rows
  }, [panelThreads, notifItems])

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
    // Wait until communications access is resolved so we do not poll with stale defaults.
    if (commAccessLoading) return
    let cancelled = false
    let timeout: number

    const canPollComms =
      canInboxDeepLink && !commsApiDeniedRef.current

    const fetchCount = async () => {
      try {
        let commData: { items?: CommunicationThread[]; total?: number } = { items: [], total: 0 }
        if (canPollComms && !commsApiDeniedRef.current) {
          try {
            await reconcileCommunicationThreadUnread({ limit: 5000 })
          } catch (err) {
            if (isHttpForbidden(err)) {
              commsApiDeniedRef.current = true
            }
            // keep polling notifications even when reconcile is temporarily unavailable
          }
        }
        const notifPromise = listNotifications({
          includeRead: false,
          limit: 100,
          scope: 'direct',
        }) as Promise<NotificationListResponse>
        const commPromise =
          canPollComms && !commsApiDeniedRef.current
            ? listCommunicationThreads({ limit: 500 }).catch((err) => {
                if (isHttpForbidden(err)) {
                  commsApiDeniedRef.current = true
                }
                return { items: [] as CommunicationThread[], total: 0 }
              })
            : Promise.resolve({ items: [] as CommunicationThread[], total: 0 })
        const [notifData, commRes] = await Promise.all([notifPromise, commPromise])
        commData = commRes
        const data = notifData
        if (!cancelled) {
          const items = Array.isArray(data?.items) ? data.items : []
          lastUnreadNotificationsRef.current = items
          setBellAttentionCount(computeBellAttentionCount(items, pendingHandoffsRef.current))
          const threadItemsRaw = Array.isArray(commData?.items)
            ? commData.items.filter(
                (th) => !th?.is_archived && String(th?.status || '').toLowerCase() !== 'deleted',
              )
            : []
          const allowedUnreadThreads = filterUnreadThreadsForUser(threadItemsRaw, canUseCommunicationsFeature)
          const unreadThreadIds = new Set(allowedUnreadThreads.map((th) => String(th.id)))
          const dedupedUnreadNotifs = items.filter((i) => {
            if (i.is_read) return false
            const tid = notificationThreadId(i)
            if (tid && unreadThreadIds.has(tid)) return false
            return true
          })
          // G-9: badge counts the rolled-up rows (3 reminder_due for same entity = 1 row).
          setBellBadgeCount(allowedUnreadThreads.length + countNotifPanelRowsGrouped(dedupedUnreadNotifs))
          const toastCandidates = items.filter((item) => {
            if (item.is_read) return false
            if (!item.id) return false
            if (shownNotificationIdsRef.current.has(String(item.id))) return false
            return ['reminder_due', 'reminder_overdue', 'handoff_requested'].includes(String(item.event_type || '').toLowerCase())
          })
          const reminderToast = toastCandidates.find((i) =>
            ['reminder_due', 'reminder_overdue'].includes(String(i.event_type || '').toLowerCase()),
          )
          const handoffToast = toastCandidates.find((i) => String(i.event_type || '').toLowerCase() === 'handoff_requested')
          if (reminderToast) {
            shownNotificationIdsRef.current.add(String(reminderToast.id))
            setReminderDuePopup((prev) => prev ?? reminderToast)
          } else if (handoffToast) {
            shownNotificationIdsRef.current.add(String(handoffToast.id))
            const title = getNotificationTitle(handoffToast)
            const desc = getNotificationDescription(handoffToast) || String(handoffToast.payload?.entity_type || handoffToast.event_type || '')
            notify({ title, description: desc, variant: 'info' })
          }
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
  }, [can, canInboxDeepLink, canUseCommunicationsFeature, commAccessLoading, commPollKey, notify, t])

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
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setSearchOpen(true)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const quickTargets = useMemo(() => {
    type Target = { key: string; labelKey: string; path: string }
    const items: Target[] = []
    if (can('candidates.view')) {
      items.push({ key: 'candidates', labelKey: 'app.nav.items.candidates', path: CRM_APP_PATHS.candidates })
    }
    if (can('companies.view')) {
      items.push({ key: 'companies', labelKey: 'app.nav.items.clients', path: CRM_APP_PATHS.clientsDirectory })
      items.push({ key: 'fleet', labelKey: 'app.nav.items.fleet', path: CRM_APP_PATHS.fleet })
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
        items.push({ key: 'calendar', labelKey: 'app.nav.items.calendar', path: CRM_APP_PATHS.workCalendar })
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

  const loadNotificationPanel = useCallback(async () => {
    if (!can('notifications.view')) return
    setNotifLoading(true)
    setNotifError(null)
    try {
      try {
        await reconcileNotifications()
      } catch {
        // ignore reconcile errors; regular loading still works
      }
      const shouldFetchThreads =
        !commAccessLoading && canInboxDeepLink && !commsApiDeniedRef.current
      const [notifData, threadsRes] = await Promise.all([
        listNotifications({ includeRead: false, limit: 100, scope: 'direct' }) as Promise<NotificationListResponse>,
        shouldFetchThreads
          ? listCommunicationThreads({ limit: 200 }).catch((err) => {
              if (isHttpForbidden(err)) {
                commsApiDeniedRef.current = true
              }
              return { items: [] as CommunicationThread[] }
            })
          : Promise.resolve({ items: [] as CommunicationThread[] }),
      ])
      const rawItems = Array.isArray(notifData?.items) ? notifData.items : []
      const threads = Array.isArray(threadsRes.items) ? threadsRes.items : []
      const activeUnreadThreads = filterUnreadThreadsForUser(threads, canUseCommunicationsFeature)
      const threadIds = new Set(activeUnreadThreads.map((th) => th.id))
      const notifFiltered = rawItems.filter((item) => {
        if (item.is_read) return false
        const tid = notificationThreadId(item)
        if (tid && threadIds.has(tid)) return false
        return true
      })
      setPanelThreads([...activeUnreadThreads].sort((a, b) => threadRecencyMs(b) - threadRecencyMs(a)))
      setNotifItems(notifFiltered)
    } catch {
      setNotifError(t('app.reminders.errors.load'))
    } finally {
      setNotifLoading(false)
    }
  }, [can, canInboxDeepLink, canUseCommunicationsFeature, commAccessLoading, t])

  const navigateToResult = (result: GlobalSearchResult) => {
    setSearchOpen(false)
    setSearchQuery('')
    navigate(result.link)
  }

  const toggleNotifications = () => {
    const next = !notifOpen
    setNotifOpen(next)
    if (next) void loadNotificationPanel()
  }

  const dismissNotif = async (id: string) => {
    try {
      await markNotificationsRead({ ids: [id] })
      setNotifItems((prev) => prev.filter((i) => String(i.id) !== id))
      lastUnreadNotificationsRef.current = lastUnreadNotificationsRef.current.filter((i) => String(i.id) !== id)
      setBellAttentionCount(computeBellAttentionCount(lastUnreadNotificationsRef.current, pendingHandoffsCount))
      setCommPollKey((k) => k + 1)
    } catch {
      // ignore
    }
  }

  const dismissNotifGroup = async (ids: string[]) => {
    if (ids.length === 0) return
    const idSet = new Set(ids.map(String))
    try {
      await markNotificationsRead({ ids })
      setNotifItems((prev) => prev.filter((i) => !idSet.has(String(i.id))))
      lastUnreadNotificationsRef.current = lastUnreadNotificationsRef.current.filter(
        (i) => !idSet.has(String(i.id)),
      )
      setBellAttentionCount(computeBellAttentionCount(lastUnreadNotificationsRef.current, pendingHandoffsCount))
      setCommPollKey((k) => k + 1)
    } catch {
      // ignore
    }
  }

  const dismissThread = async (threadId: string) => {
    try {
      await executeWorkspaceCommand(threadId, 'MarkThreadRead')
      setPanelThreads((prev) => prev.filter((t) => t.id !== threadId))
      setCommPollKey((k) => k + 1)
    } catch {
      // ignore
    }
  }

  const clearAllPanelItems = async () => {
    const threadsSnap = [...panelThreads]
    try {
      await markNotificationsRead({ markAll: true })
      await Promise.all(
        threadsSnap.map((th) => executeWorkspaceCommand(th.id, 'MarkThreadRead').catch(() => {})),
      )
      setPanelThreads([])
      setNotifItems([])
      lastUnreadNotificationsRef.current = []
      setBellAttentionCount(computeBellAttentionCount([], pendingHandoffsCount))
      setBellBadgeCount(0)
      setCommPollKey((k) => k + 1)
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
          <a
            href={CRM_APP_PATHS.work}
            className="shrink-0 rounded-md outline-none ring-brand-500 transition hover:opacity-90 focus-visible:ring-2"
            title="HostFlow"
            aria-label="HostFlow"
            onClick={(e) => {
              e.preventDefault()
              navigate(CRM_APP_PATHS.work)
            }}
          >
            <img
              src="/logo_hf.svg"
              alt=""
              className={compact ? 'h-7 w-auto' : 'h-8 w-auto'}
              width={120}
              height={32}
            />
          </a>
          {isTrialTenant && !isSuperAdmin ? (
            <span
              className="inline-flex items-center rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-amber-800"
              title={t('app.topbar.trial_badge_hint')}
            >
              {t('app.topbar.trial_badge')}
            </span>
          ) : null}
        </div>

        <div className="flex min-w-0 flex-1 items-center justify-end gap-1 sm:gap-2">
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
          <button
            type="button"
            className={[
              'hidden items-center gap-2 rounded-md border border-slate-200 px-4 text-sm text-slate-600 transition hover:bg-slate-50 lg:inline-flex',
              compact ? 'py-1.5' : 'py-2',
            ].join(' ')}
            onClick={() => setSearchOpen(true)}
          >
            <span className="text-slate-400">{SEARCH_SHORTCUT_HINT}</span>
            <span>{t('app.topbar.search.open')}</span>
          </button>

          {can('notifications.view') ? <TodayTasksPeek /> : null}

          {can('notifications.view') && (
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
                {bellBadgeCount > 0 && (
                  <span className="absolute -right-1 -top-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-rose-500 px-1 text-[11px] font-semibold text-white">
                    {formatThreadUnreadBadge(bellBadgeCount)}
                  </span>
                )}
              </button>

              {notifOpen && (
                <div className="absolute right-0 top-10 z-50 w-[min(96vw,28rem)] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
                  <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
                    <p className="text-sm font-semibold text-slate-900">
                      {t('app.topbar.notifications.title')}
                    </p>
                    {unifiedPanelRows.length > 0 && (
                      <span
                        className="inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-rose-500 px-1 text-[11px] font-semibold text-white"
                        aria-label={t('app.topbar.notifications.panel_subtitle', {
                          values: { count: unifiedPanelRows.length },
                        })}
                      >
                        {formatThreadUnreadBadge(unifiedPanelRows.length)}
                      </span>
                    )}
                  </div>
                  <div className="max-h-[min(60vh,32rem)] space-y-2 overflow-auto p-3">
                    {notifLoading && unifiedPanelRows.length === 0 && (
                      <p className="text-sm text-slate-500">{t('common.loading')}</p>
                    )}
                    {notifError && <p className="text-xs text-rose-600">{notifError}</p>}
                    {!notifError && !notifLoading && unifiedPanelRows.length === 0 && (
                      <p className="text-sm text-slate-500">{t('app.reminders.states.empty')}</p>
                    )}
                    {unifiedPanelRows.map((row) => {
                      const dateLocale = localeMap[locale as keyof typeof localeMap] || enUS
                      if (row.kind === 'thread') {
                        const th = row.thread
                        const when = th.last_message_at
                          ? formatDistanceToNow(new Date(th.last_message_at), { addSuffix: true, locale: dateLocale })
                          : th.updated_at
                            ? formatDistanceToNow(new Date(th.updated_at), { addSuffix: true, locale: dateLocale })
                            : ''
                        const openPath = resolveThreadOpenPath(th, canInboxDeepLink)
                        const preview = String(th.last_message_preview || '').trim()
                        const TypeIcon = isEmailThread(th) ? IconMail : IconMessageCircle
                        const iconClass = isEmailThread(th) ? 'text-indigo-600' : 'text-sky-600'
                        return (
                          <div
                            key={`th-${th.id}`}
                            className="rounded-xl border border-brand-100 bg-white px-3 py-2 shadow-sm"
                          >
                            <div className="flex min-w-0 gap-2">
                              <span className={`mt-0.5 shrink-0 ${iconClass}`} aria-hidden>
                                <TypeIcon size={20} stroke={1.8} />
                              </span>
                              <div className="min-w-0 flex-1 space-y-1">
                                <p className="break-words text-sm font-semibold leading-snug text-slate-900 line-clamp-2">
                                  {threadTitle(th)}
                                </p>
                                {preview ? (
                                  <p className="break-words text-xs text-slate-600 line-clamp-2">{preview}</p>
                                ) : null}
                                <p className="text-[11px] uppercase tracking-wide text-slate-400">{when}</p>
                                <div className="flex flex-wrap gap-2 pt-1">
                                  {openPath ? (
                                    <button
                                      type="button"
                                      className="text-xs font-semibold text-brand-700 hover:text-brand-800"
                                      onClick={() => {
                                        setNotifOpen(false)
                                        navigate(openPath)
                                      }}
                                    >
                                      {t('app.topbar.notifications.open')}
                                    </button>
                                  ) : null}
                                  <button
                                    type="button"
                                    className="text-xs font-semibold text-slate-600 hover:text-slate-800"
                                    onClick={() => void dismissThread(th.id)}
                                  >
                                    {t('app.topbar.notifications.clear')}
                                  </button>
                                </div>
                              </div>
                            </div>
                          </div>
                        )
                      }
                      if (row.kind === 'notif_group') {
                        const repr = row.representative
                        const when = repr.created_at
                          ? formatDistanceToNow(new Date(repr.created_at), { addSuffix: true, locale: dateLocale })
                          : ''
                        const reprTitle = getNotificationTitle(repr)
                        const groupTitle = t('app.topbar.notifications.reminder_group_title', {
                          values: { count: row.count },
                          defaultValue: `${row.count} pending tasks for this entity`,
                        })
                        const description = reprTitle
                        const openPath = resolveNotificationOpenPath(repr, { canInboxDeepLink })
                        const ids = row.items.map((n) => String(n.id)).filter(Boolean)
                        return (
                          <div
                            key={`nfgrp-${row.key}`}
                            className="rounded-xl border border-amber-200 bg-amber-50/40 px-3 py-2 shadow-sm"
                          >
                            <div className="flex min-w-0 gap-2">
                              <span className="mt-0.5 shrink-0 text-amber-700" aria-hidden>
                                <IconChecklist size={20} stroke={1.8} />
                              </span>
                              <div className="min-w-0 flex-1 space-y-1">
                                <div className="flex flex-wrap items-center gap-2">
                                  <p className="break-words text-sm font-semibold leading-snug text-slate-900 line-clamp-2">
                                    {groupTitle}
                                  </p>
                                  <span className="inline-flex items-center rounded-full bg-amber-200/80 px-2 py-0.5 text-[11px] font-semibold text-amber-900">
                                    ×{row.count}
                                  </span>
                                </div>
                                {description ? (
                                  <p className="break-words text-xs text-slate-600 line-clamp-2">
                                    {description}
                                  </p>
                                ) : null}
                                <p className="text-[11px] uppercase tracking-wide text-slate-400">{when}</p>
                                <div className="flex flex-wrap gap-2 pt-1">
                                  {openPath ? (
                                    <button
                                      type="button"
                                      className="text-xs font-semibold text-brand-700 hover:text-brand-800"
                                      onClick={() => {
                                        setNotifOpen(false)
                                        navigate(openPath)
                                      }}
                                    >
                                      {t('app.topbar.notifications.open')}
                                    </button>
                                  ) : null}
                                  {ids.length > 0 ? (
                                    <button
                                      type="button"
                                      className="text-xs font-semibold text-slate-600 hover:text-slate-800"
                                      onClick={() => void dismissNotifGroup(ids)}
                                    >
                                      {t('app.topbar.notifications.clear_group', {
                                        values: { count: row.count },
                                        defaultValue: `Clear all (${row.count})`,
                                      })}
                                    </button>
                                  ) : null}
                                </div>
                              </div>
                            </div>
                          </div>
                        )
                      }
                      const item = row.item
                      const when = item.created_at
                        ? formatDistanceToNow(new Date(item.created_at), { addSuffix: true, locale: dateLocale })
                        : ''
                      const title = getNotificationTitle(item)
                      const uosGroup = getNotificationUosGroup(item)
                      const description = getNotificationDescription(item)
                      const openPath = resolveNotificationOpenPath(item, { canInboxDeepLink })
                      const TypeIcon =
                        uosGroup === 'sla'
                          ? IconAlertTriangle
                          : uosGroup === 'tasks'
                            ? IconChecklist
                            : uosGroup === 'messages'
                              ? IconMessageCircle
                              : IconSettings
                      const iconClass =
                        uosGroup === 'sla'
                          ? 'text-rose-600'
                          : uosGroup === 'tasks'
                            ? 'text-amber-700'
                            : uosGroup === 'messages'
                              ? 'text-sky-600'
                              : 'text-slate-500'
                      return (
                        <div
                          key={`nf-${item.id}`}
                          className="rounded-xl border border-brand-100 bg-white px-3 py-2 shadow-sm"
                        >
                          <div className="flex min-w-0 gap-2">
                            <span className={`mt-0.5 shrink-0 ${iconClass}`} aria-hidden>
                              <TypeIcon size={20} stroke={1.8} />
                            </span>
                            <div className="min-w-0 flex-1 space-y-1">
                              <p className="break-words text-sm font-semibold leading-snug text-slate-900 line-clamp-2">
                                {title}
                              </p>
                              {description ? (
                                <p className="break-words text-xs text-slate-600 line-clamp-3">{description}</p>
                              ) : null}
                              <p className="text-[11px] uppercase tracking-wide text-slate-400">{when}</p>
                              <div className="flex flex-wrap gap-2 pt-1">
                                {openPath ? (
                                  <button
                                    type="button"
                                    className="text-xs font-semibold text-brand-700 hover:text-brand-800"
                                    onClick={() => {
                                      setNotifOpen(false)
                                      navigate(openPath)
                                    }}
                                  >
                                    {t('app.topbar.notifications.open')}
                                  </button>
                                ) : null}
                                {item.id ? (
                                  <button
                                    type="button"
                                    className="text-xs font-semibold text-slate-600 hover:text-slate-800"
                                    onClick={() => void dismissNotif(String(item.id))}
                                  >
                                    {t('app.topbar.notifications.clear')}
                                  </button>
                                ) : null}
                              </div>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                  <div className="flex items-center justify-between gap-2 border-t border-slate-100 px-4 py-2">
                    <button
                      type="button"
                      className="text-xs font-semibold text-brand-700 hover:text-brand-800"
                      onClick={() => {
                        setNotifOpen(false)
                        navigate(CRM_APP_PATHS.notificationAlerts)
                      }}
                    >
                      {t('app.topbar.notifications.open_center')}
                    </button>
                    <button
                      type="button"
                      className="text-xs font-semibold text-slate-600 hover:text-slate-800 disabled:opacity-50"
                      onClick={() => void clearAllPanelItems()}
                      disabled={notifLoading || unifiedPanelRows.length === 0}
                    >
                      {t('app.topbar.notifications.clear_all')}
                    </button>
                  </div>
                </div>
              )}
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
              <div className="absolute right-0 z-[100] mt-2 max-h-[min(80vh,28rem)] w-[min(96vw,320px)] overflow-y-auto rounded-xl border border-slate-200 bg-white py-2 text-sm shadow-2xl">
                <div className="border-b border-slate-100 px-4 py-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                    {t('app.shell.sidebar.section_personal')}
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

                {(can('companies.view') || can('settings.view') || can('admin.users')) && (
                  <div className="border-b border-slate-100 px-4 py-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                      {t('app.shell.sidebar.section_organization')}
                    </p>
                    <button
                      type="button"
                      className="mt-1 flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-slate-700 transition hover:bg-slate-50"
                      onClick={() => {
                        setMenuOpen(false)
                        navigate(CRM_APP_PATHS.organization)
                      }}
                    >
                      <IconHome size={16} stroke={1.8} />
                      <span>{t('app.nav.items.organization', { defaultValue: 'Organization' })}</span>
                    </button>
                    {can('companies.view') ? (
                      <button
                        type="button"
                        className="mt-1 flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-slate-700 transition hover:bg-slate-50"
                        onClick={() => {
                          setMenuOpen(false)
                          navigate(CRM_APP_PATHS.myCompany)
                        }}
                      >
                        <IconBuilding size={16} stroke={1.8} />
                        <span>{t('app.nav.items.my_company')}</span>
                      </button>
                    ) : null}
                  </div>
                )}

                {can('settings.view') && (
                  <div className="border-b border-slate-100 px-4 py-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                      {t('app.shell.sidebar.section_settings')}
                    </p>
                    <button
                      type="button"
                      className="mt-1 flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-slate-700 transition hover:bg-slate-50"
                      onClick={() => {
                        setMenuOpen(false)
                        navigate(CRM_APP_PATHS.settings)
                      }}
                    >
                      <IconSettings size={16} stroke={1.8} />
                      <span>{t('app.nav.items.settings')}</span>
                    </button>
                  </div>
                )}

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

      <Modal
        open={Boolean(reminderDuePopup)}
        onClose={() => setReminderDuePopup(null)}
        title={reminderDuePopup ? getNotificationTitle(reminderDuePopup) : undefined}
        size="md"
        surfaceClassName={
          String(reminderDuePopup?.event_type || '').toLowerCase() === 'reminder_overdue'
            ? 'border-rose-200 ring-2 ring-rose-300/50'
            : 'border-amber-100 ring-2 ring-amber-200/40'
        }
      >
        {reminderDuePopup ? (
          <div className="space-y-4">
            {(() => {
              const desc = getNotificationDescription(reminderDuePopup)
              const dueRaw = (reminderDuePopup.payload as Record<string, unknown> | undefined)?.due_at
              const dueStr = dueRaw != null && String(dueRaw).trim() ? String(dueRaw) : ''
              let dueLabel = ''
              if (dueStr) {
                try {
                  dueLabel = new Intl.DateTimeFormat(
                    locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : 'en-US',
                    { dateStyle: 'medium', timeStyle: 'short' },
                  ).format(new Date(dueStr))
                } catch {
                  dueLabel = dueStr
                }
              }
              const payload = (reminderDuePopup.payload || {}) as Record<string, unknown>
              const entityType = String(payload.entity_type || reminderDuePopup.entity_type || '').toLowerCase()
              const entityId = String(payload.entity_id || reminderDuePopup.entity_id || '').trim()
              const isCandidate = entityType === 'candidate' && Boolean(entityId)

              const ackAndClear = async () => {
                const id = String(reminderDuePopup.id || '')
                setReminderDuePopup(null)
                if (id) {
                  try {
                    await markNotificationsRead({ ids: [id] })
                  } catch {
                    /* ignore */
                  }
                }
              }

              return (
                <>
                  {desc ? <p className="text-sm text-slate-700">{desc}</p> : null}
                  {dueLabel ? (
                    <p className="text-sm text-slate-600">
                      <span className="font-semibold text-slate-800">
                        {t('app.notifications.reminder_popup.due_label', { defaultValue: 'Due' })}:
                      </span>{' '}
                      {dueLabel}
                    </p>
                  ) : null}
                  <div className="flex flex-wrap gap-2 pt-1">
                    {isCandidate ? (
                      <button
                        type="button"
                        className="btn-primary"
                        onClick={() => {
                          void ackAndClear()
                          navigate(`${CRM_APP_PATHS.candidates}/${encodeURIComponent(entityId)}`)
                        }}
                      >
                        {t('app.notifications.reminder_popup.open_candidate', { defaultValue: 'Open candidate' })}
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className={isCandidate ? 'btn-secondary' : 'btn-primary'}
                      onClick={() => {
                        void ackAndClear()
                        navigate(CRM_APP_PATHS.notificationAlerts)
                      }}
                    >
                      {t('app.notifications.reminder_popup.all_reminders', { defaultValue: 'All reminders' })}
                    </button>
                    <button type="button" className="btn-secondary" onClick={() => setReminderDuePopup(null)}>
                      {t('app.notifications.reminder_popup.later', { defaultValue: 'Later' })}
                    </button>
                  </div>
                </>
              )
            })()}
          </div>
        ) : null}
      </Modal>

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

