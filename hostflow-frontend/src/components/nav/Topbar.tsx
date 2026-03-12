import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  IconBell,
  IconBuilding,
  IconCreditCard,
  IconLayoutSidebarLeftExpand,
  IconLogout,
  IconMail,
  IconMenu2,
  IconMessageCircle,
  IconSettings,
  IconUserCircle,
  IconUsers,
  IconX,
} from '@tabler/icons-react'
import type { TenantSummary, WhoAmI } from '../../api/types'
import { listNotifications, markNotificationsRead, reconcileNotifications, resolveAssetUrl } from '../../api/client'
import type { NotificationItem, NotificationListResponse } from '../../api/types'
import { listCommunicationThreads, reconcileCommunicationThreadUnread } from '../../api/communications'
import { useToast } from '../Toast'
import { usePermissions } from '../../hooks/usePermissions'
import { searchGlobal, type GlobalSearchResult } from '../../api/search'
import { useI18n, type LocaleCode } from '../../i18n'
import { useAuth } from '../../store/useAuth'
import { usePendingHandoffsCount } from '../../hooks/usePendingHandoffsCount'
import { formatDistanceToNow } from 'date-fns'
import { enUS, ru, pl } from 'date-fns/locale'

type TopbarProps = {
  me: WhoAmI | null
  tenant: TenantSummary | null
  onLogout: () => void
  onToggleSidebar: () => void
}

const SUPPORTED_LOCALES: LocaleCode[] = ['ru', 'en', 'pl']

const RESULT_LABEL_KEYS: Record<GlobalSearchResult['type'], string> = {
  candidate: 'app.topbar.search.results.candidate',
  company: 'app.topbar.search.results.company',
  document: 'app.topbar.search.results.document',
}

function humanizeEventType(eventType: string): string {
  return eventType
    .trim()
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/^\w/, (c) => c.toUpperCase())
}

export function Topbar({ me, tenant, onLogout, onToggleSidebar }: TopbarProps) {
  const navigate = useNavigate()
  const { can } = usePermissions()
  const { locale, setLocale, t } = useI18n()
  const { canReturnToPlatform, restorePlatformSession } = useAuth()
  const { notify } = useToast()
  const [notifOpen, setNotifOpen] = useState(false)
  const [notifItems, setNotifItems] = useState<NotificationItem[]>([])
  const [notifFeedMode, setNotifFeedMode] = useState<'all' | 'sla' | 'events'>('all')
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
  const [remindersCount, setRemindersCount] = useState(0)
  const [messagesUnreadCount, setMessagesUnreadCount] = useState(0)
  const [emailUnreadCount, setEmailUnreadCount] = useState(0)
  const shownNotificationIdsRef = useRef<Set<string>>(new Set())
  const unreadReconcileDoneRef = useRef(false)
  const menuRef = useRef<HTMLDivElement | null>(null)
  const pendingHandoffsCount = usePendingHandoffsCount()

  const notificationRank = (item: NotificationItem): number => {
    if (item.is_read) return 0
    const payload = (item.payload || {}) as Record<string, any>
    const eventType = String(item.event_type || '').toLowerCase()
    const severity = String(payload.severity || '').toLowerCase()
    const requiresAction = Boolean(payload.requires_action)
    let score = 0
    if (requiresAction) score += 100
    if (eventType === 'communications_sla_overdue') score += 90
    if (severity === 'high') score += 40
    else if (severity === 'medium') score += 20
    else if (severity === 'low') score += 5
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

  const brandLabel = tenant?.workspace_label?.trim() || tenant?.name || 'HostFlow'
  const tenantLogoUrl = useMemo(() => (tenant?.logo_url ? resolveAssetUrl(tenant.logo_url) : null), [tenant?.logo_url])

  const toggleLang = () => {
    const index = SUPPORTED_LOCALES.indexOf(locale)
    const next = SUPPORTED_LOCALES[(index + 1) % SUPPORTED_LOCALES.length]
    setLocale(next)
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
      return t('app.notifications.handoff_requested_title', { defaultValue: 'New candidate to process' })
    }
    if (eventType === 'handoff_accepted') {
      return t('app.notifications.handoff_accepted_title', { defaultValue: 'Candidate handed off' })
    }
    if (eventType === 'communications_sla_overdue') {
      return t('app.notifications.communications_sla_overdue_title', { defaultValue: 'SLA overdue: reply required in dialog' })
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

  const isSlaNotification = (item: NotificationItem): boolean =>
    String(item.event_type || '').trim().toLowerCase() === 'communications_sla_overdue'

  const slaUnreadCount = useMemo(
    () => notifItems.filter((i) => !i.is_read && isSlaNotification(i)).length,
    [notifItems],
  )
  const eventsUnreadCount = useMemo(
    () => notifItems.filter((i) => !i.is_read && !isSlaNotification(i)).length,
    [notifItems],
  )
  const visibleNotifItems = useMemo(() => {
    if (notifFeedMode === 'sla') return notifItems.filter((i) => isSlaNotification(i))
    if (notifFeedMode === 'events') return notifItems.filter((i) => !isSlaNotification(i))
    return notifItems
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
    if (!can('notifications.view')) return
    let cancelled = false
    let timeout: number

    const fetchCount = async () => {
      try {
        if (!unreadReconcileDoneRef.current) {
          unreadReconcileDoneRef.current = true
          try {
            await reconcileCommunicationThreadUnread({ limit: 500 })
          } catch {
            // keep polling even when reconcile is temporarily unavailable
          }
        }
        const [notifData, commData] = await Promise.all([
          listNotifications({ includeRead: false, limit: 100, scope: 'direct' }) as Promise<NotificationListResponse>,
          listCommunicationThreads({ limit: 300 }).catch(() => ({ items: [], total: 0 })),
        ])
        const data = notifData
        if (!cancelled) {
          const items = Array.isArray(data?.items) ? data.items : []
          const unread = items.filter((item) => !item.is_read).length
          setRemindersCount(unread)
          const threadItems = Array.isArray((commData as any)?.items)
            ? (commData as any).items.filter(
                (th: any) => !Boolean(th?.is_archived) && String(th?.status || '').toLowerCase() !== 'deleted',
              )
            : []
          const emailUnread = threadItems
            .filter((th: any) => String(th?.channel || '').toLowerCase() === 'email')
            .reduce((acc: number, th: any) => acc + Math.max(0, Number(th?.unread_count || 0)), 0)
          const msgUnread = threadItems
            .filter((th: any) => String(th?.channel || '').toLowerCase() !== 'email')
            .reduce((acc: number, th: any) => acc + Math.max(0, Number(th?.unread_count || 0)), 0)
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
  }, [can, notify, t])

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
        setSearchOpen(true)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const quickTargets = [
    { key: 'candidates', labelKey: 'app.nav.items.candidates', path: '/app/candidates' },
    { key: 'companies', labelKey: 'app.nav.items.clients', path: '/app/clients' },
    { key: 'documents', labelKey: 'app.nav.items.documents', path: '/app/documents' },
  ]

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
      const data = (await listNotifications({ includeRead: true, limit: 20, scope: 'direct' })) as NotificationListResponse
      const items = Array.isArray(data?.items) ? data.items : []
      setNotifItems(prioritizeNotifications(items))
      setRemindersCount(items.filter((item) => !item.is_read).length)
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
      setNotifItems((prev) => prev.map((i) => ({ ...i, is_read: true })))
      setRemindersCount(0)
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
      const fallback = quickTargets[0]
      navigate(`${fallback.path}?q=${encodeURIComponent(searchQuery.trim())}`)
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
    searchGlobal(trimmed, controller.signal)
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
  }, [searchQuery, searchOpen, t])

  return (
    <>
      <header className="relative z-50 flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 shadow-sm lg:px-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="rounded-md p-2 text-slate-600 transition hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            aria-label={t('app.topbar.actions.open_menu')}
            onClick={onToggleSidebar}
          >
            <IconMenu2 size={20} stroke={1.8} />
          </button>
          {tenantLogoUrl ? (
            <img
              src={tenantLogoUrl}
              alt={brandLabel}
              className="max-h-8 w-auto object-contain"
              style={{ maxHeight: 32 }}
            />
          ) : (
            <span className="text-base font-semibold text-slate-700">HostFlow</span>
          )}
        </div>

        <div className="flex flex-1 items-center justify-end gap-2">
          {canReturnToPlatform && (
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-800 transition hover:bg-amber-100"
              onClick={() => {
                void restorePlatformSession()
              }}
            >
              {t('app.topbar.actions.return_to_platform')}
            </button>
          )}
          <button
            type="button"
            className="hidden items-center gap-2 rounded-md border border-slate-200 px-4 py-2 text-sm text-slate-600 transition hover:bg-slate-50 lg:inline-flex"
            onClick={() => setSearchOpen(true)}
          >
            <span className="text-slate-400">⌘K</span>
            <span>{t('app.topbar.search.open')}</span>
          </button>

          {/* Кнопка меню кандидатов - показывается только на странице кандидатов */}
          <CandidatesMenuButton t={t} />

          <button
            type="button"
            className="rounded-md border border-slate-200 px-3 py-2 text-sm font-semibold uppercase text-slate-700 transition hover:bg-slate-50"
            onClick={toggleLang}
          >
            {locale.toUpperCase()}
          </button>

          {can('notifications.view') && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="relative rounded-full border border-slate-200 p-2 text-slate-700 transition hover:bg-slate-50"
                aria-label={t('app.nav.items.messages', { defaultValue: 'Messages' })}
                onClick={() => navigate('/app/messages')}
              >
                <IconMessageCircle size={20} stroke={1.8} />
                {messagesUnreadCount > 0 && (
                  <span className="absolute -right-1 -top-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-sky-500 px-1 text-[11px] font-semibold text-white">
                    {messagesUnreadCount}
                  </span>
                )}
              </button>

              <button
                type="button"
                className="relative rounded-full border border-slate-200 p-2 text-slate-700 transition hover:bg-slate-50"
                aria-label={t('app.nav.items.email', { defaultValue: 'Email' })}
                onClick={() => navigate('/app/email')}
              >
                <IconMail size={20} stroke={1.8} />
                {emailUnreadCount > 0 && (
                  <span className="absolute -right-1 -top-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-indigo-500 px-1 text-[11px] font-semibold text-white">
                    {emailUnreadCount}
                  </span>
                )}
              </button>

              <div className="relative" ref={notifRef}>
                <button
                  type="button"
                  className="relative rounded-full border border-slate-200 p-2 text-slate-700 transition hover:bg-slate-50"
                  aria-label={t('app.topbar.actions.reminders')}
                  onClick={toggleNotifications}
                >
                  <IconBell size={20} stroke={1.8} />
                  {(remindersCount > 0 || pendingHandoffsCount > 0) && (
                    <span className="absolute -right-1 -top-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-rose-500 px-1 text-[11px] font-semibold text-white">
                      {remindersCount + pendingHandoffsCount}
                    </span>
                  )}
                </button>

                {notifOpen && (
                  <div className="absolute right-0 top-10 z-50 w-[min(96vw,34rem)] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
                    <div className="flex flex-col gap-2 border-b border-slate-100 px-4 py-3">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{t('app.reminders.title')}</p>
                        <p className="text-xs text-slate-500 break-words">
                          {notifLoading
                            ? t('common.loading')
                            : t('app.reminders.subtitle', {
                                values: {
                                  scope: t('app.reminders.scope_labels.all'),
                                  total: notifItems.length,
                                  unread: notifItems.filter((i) => !i.is_read).length,
                                },
                              })}
                        </p>
                        {!notifLoading && (
                          <div className="mt-2 flex flex-wrap items-center gap-2">
                            <span className="rounded-md bg-rose-100 px-2 py-0.5 text-[11px] font-medium text-rose-700">
                              {t('app.sla_incidents.title')}: {slaUnreadCount}
                            </span>
                            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700">
                              {t('app.reminders.states.unread', { defaultValue: 'Unread' })}: {notifItems.filter((i) => !i.is_read).length}
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
                          {t('app.reminders.actions.sync', { defaultValue: 'Sync' })}
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
                          {t('app.reminders.scopes.all', { defaultValue: 'All' })} ({notifItems.length})
                        </button>
                        <button
                          type="button"
                          className={[
                            'rounded-md px-2.5 py-1 text-[11px] font-medium',
                            notifFeedMode === 'sla' ? 'bg-rose-600 text-white' : 'bg-rose-100 text-rose-700 hover:bg-rose-200',
                          ].join(' ')}
                          onClick={() => setNotifFeedMode('sla')}
                        >
                          {t('app.sla_incidents.title')} ({slaUnreadCount})
                        </button>
                        <button
                          type="button"
                          className={[
                            'rounded-md px-2.5 py-1 text-[11px] font-medium',
                            notifFeedMode === 'events' ? 'bg-slate-700 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
                          ].join(' ')}
                          onClick={() => setNotifFeedMode('events')}
                        >
                          {t('app.reminders.tabs.events', { defaultValue: 'Events' })} ({eventsUnreadCount})
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
                        const isSla = item.event_type === 'communications_sla_overdue'
                        const description = getNotificationDescription(item)
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
                                  {isSla ? (
                                    <span className="rounded-md bg-rose-100 px-2 py-0.5 text-[11px] font-medium text-rose-700">
                                      {t('app.sla_incidents.title')}
                                    </span>
                                  ) : (
                                    <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700">
                                      {t('app.reminders.tabs.events')}
                                    </span>
                                  )}
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
                                      navigate('/app/procesowani')
                                    }}
                                  >
                                    {t('app.notifications.view_handoffs', {
                                      defaultValue: 'Перейти к обработке',
                                    })}
                                  </button>
                                )}
                                {isSla && (
                                  <button
                                    type="button"
                                    className="mt-1 text-xs font-medium text-rose-700 hover:text-rose-800"
                                    onClick={() => {
                                      setNotifOpen(false)
                                      navigate('/app/sla-incidents')
                                    }}
                                  >
                                    {t('app.notifications.open_sla_incidents', {
                                      defaultValue: 'Открыть SLA-инциденты',
                                    })}
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
                            navigate('/app/procesowani')
                          }}
                        >
                          {t('app.notifications.view_handoffs', {
                            defaultValue: 'На обработку',
                          })}{' '}
                          ({pendingHandoffsCount})
                        </button>
                      )}
                      <div className="ml-auto flex items-center gap-3">
                        <button
                          type="button"
                          className="text-sm font-semibold text-rose-700 hover:text-rose-800"
                          onClick={() => {
                            setNotifOpen(false)
                            navigate('/app/sla-incidents')
                          }}
                        >
                          {t('app.notifications.open_sla_incidents')}
                        </button>
                        <button
                          type="button"
                          className="text-sm font-semibold text-slate-700 hover:text-slate-800"
                          onClick={() => {
                            setNotifOpen(false)
                            navigate('/app/reminders')
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
              className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
              onClick={() => setMenuOpen((prev) => !prev)}
            >
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-900 text-white">
                {initials}
              </span>
              <span className="hidden md:inline">{me?.full_name || me?.email || t('app.shell.actions.profile')}</span>
            </button>
            {menuOpen && (
              <div className="absolute right-0 z-[100] mt-2 w-[320px] overflow-hidden rounded-xl border border-slate-200 bg-white py-2 text-sm shadow-2xl">
                <div className="border-b border-slate-100 px-4 py-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                    {t('app.shell.account.my_account', { defaultValue: 'My account' })}
                  </p>
                  <button
                    type="button"
                    className="mt-1 flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-slate-700 transition hover:bg-slate-50"
                    onClick={() => {
                      setMenuOpen(false)
                      navigate('/app/profile')
                    }}
                  >
                    <IconUserCircle size={16} />
                    <span>{t('app.shell.actions.profile')}</span>
                  </button>
                </div>

                <div className="border-b border-slate-100 px-4 py-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                    {t('app.shell.account.company_overview', { defaultValue: 'Company overview' })}
                  </p>
                  <button
                    type="button"
                    className="mt-1 flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-slate-700 transition hover:bg-slate-50"
                    onClick={() => {
                      setMenuOpen(false)
                      navigate('/app/settings')
                    }}
                  >
                    <IconSettings size={16} />
                    <span>{t('app.shell.account.company_settings', { defaultValue: 'Company settings' })}</span>
                  </button>
                  {(can('admin.users') || can('users.manage') || can('users.view')) && (
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-slate-700 transition hover:bg-slate-50"
                      onClick={() => {
                        setMenuOpen(false)
                        navigate('/app/settings/users')
                      }}
                    >
                      <IconUsers size={16} />
                      <span>{t('app.shell.account.manage_users', { defaultValue: 'Manage users' })}</span>
                    </button>
                  )}
                  {can('admin.users') && (
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-slate-700 transition hover:bg-slate-50"
                      onClick={() => {
                        setMenuOpen(false)
                        navigate('/app/settings/billing')
                      }}
                    >
                      <IconCreditCard size={16} />
                      <span>{t('app.shell.account.billing', { defaultValue: 'Billing' })}</span>
                    </button>
                  )}
                  {can('admin.metaLeads') && (
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-slate-700 transition hover:bg-slate-50"
                      onClick={() => {
                        setMenuOpen(false)
                        navigate('/app/settings/integrations')
                      }}
                    >
                      <IconBuilding size={16} />
                      <span>{t('app.shell.account.tools_apps', { defaultValue: 'Tools and apps' })}</span>
                    </button>
                  )}
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

              <div className="grid gap-2 md:grid-cols-3">
                {quickTargets.map((target) => (
                  <button
                    key={target.key}
                    type="button"
                    className="rounded-lg border border-slate-200 px-4 py-3 text-left text-sm text-slate-700 transition hover:border-brand-500 hover:text-brand-900"
                    onClick={() => {
                      const trimmed = searchQuery.trim()
                      setSearchOpen(false)
                      setSearchQuery('')
                      const dest = trimmed ? `${target.path}?q=${encodeURIComponent(trimmed)}` : target.path
                      navigate(dest)
                    }}
                  >
                    <div className="text-xs uppercase text-slate-400">{t('app.topbar.search.quick_section')}</div>
                    <div className="text-base font-semibold">{t(target.labelKey)}</div>
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
  const isCandidatesPage = location.pathname === '/app/candidates'

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
      className="flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700 transition hover:bg-slate-50"
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
