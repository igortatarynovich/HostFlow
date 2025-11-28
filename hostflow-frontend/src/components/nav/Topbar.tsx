import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { TenantSummary, WhoAmI } from '../../api/types'
import { listNotifications, resolveAssetUrl } from '../../api/client'
import type { NotificationListResponse } from '../../api/types'
import { usePermissions } from '../../hooks/usePermissions'
import { searchGlobal, type GlobalSearchResult } from '../../api/search'
import { filterRelevantNotifications } from '../../utils/notifications'
import { useI18n, type LocaleCode } from '../../i18n'
import { useAuth } from '../../store/useAuth'

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

export function Topbar({ me, tenant, onLogout, onToggleSidebar }: TopbarProps) {
  const navigate = useNavigate()
  const { can } = usePermissions()
  const { locale, setLocale, t } = useI18n()
  const { canReturnToPlatform, restorePlatformSession } = useAuth()

  const [menuOpen, setMenuOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchResults, setSearchResults] = useState<GlobalSearchResult[]>([])
  const [searchError, setSearchError] = useState<string | null>(null)
  const [remindersCount, setRemindersCount] = useState(0)

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

  useEffect(() => {
    if (!can('notifications.view')) return
    let cancelled = false
    let timeout: number

    const fetchCount = async () => {
      try {
        const data = (await listNotifications({ includeRead: false, limit: 100, scope: 'all' })) as NotificationListResponse
        if (!cancelled) {
          const items = Array.isArray(data?.items) ? data.items : []
          const direct = filterRelevantNotifications(items, me)
          const source = direct.length > 0 ? direct : items
          const unread = source.filter((item) => !item.is_read).length
          setRemindersCount(unread)
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
  }, [can, me])

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

  const navigateToResult = (result: GlobalSearchResult) => {
    setSearchOpen(false)
    setSearchQuery('')
    navigate(result.link)
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
      <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4 shadow-sm lg:px-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="rounded-md p-2 text-gray-600 transition hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            aria-label={t('app.topbar.actions.open_menu')}
            onClick={onToggleSidebar}
          >
            <span className="block h-0.5 w-5 bg-current shadow-[0_6px_0_0_currentColor,0_12px_0_0_currentColor]" />
          </button>
          {tenantLogoUrl ? (
            <img
              src={tenantLogoUrl}
              alt={brandLabel}
              className="max-h-8 w-auto object-contain"
              style={{ maxHeight: 32 }}
            />
          ) : (
            <span className="text-base font-semibold text-gray-700">HostFlow</span>
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
            className="hidden items-center gap-2 rounded-md border border-gray-200 px-4 py-2 text-sm text-gray-600 transition hover:bg-gray-50 lg:inline-flex"
            onClick={() => setSearchOpen(true)}
          >
            <span className="text-gray-400">⌘K</span>
            <span>{t('app.topbar.search.open')}</span>
          </button>

          <button
            type="button"
            className="rounded-md border border-gray-200 px-3 py-2 text-sm font-semibold uppercase text-gray-700 transition hover:bg-gray-50"
            onClick={toggleLang}
          >
            {locale.toUpperCase()}
          </button>

          {can('notifications.view') && (
            <button
              type="button"
              className="relative rounded-full border border-gray-200 p-2 text-gray-700 transition hover:bg-gray-50"
              aria-label={t('app.topbar.actions.reminders')}
              onClick={() => navigate('/app/reminders')}
            >
              <BellIcon />
              {remindersCount > 0 && (
                <span className="absolute -right-1 -top-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-rose-500 px-1 text-[11px] font-semibold text-white">
                  {remindersCount}
                </span>
              )}
            </button>
          )}

          <div className="relative">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-full border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
              onClick={() => setMenuOpen((prev) => !prev)}
            >
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-900 text-white">
                {initials}
              </span>
              <span className="hidden md:inline">{me?.full_name || me?.email || t('app.shell.actions.profile')}</span>
            </button>
            {menuOpen && (
              <div className="absolute right-0 mt-2 w-48 rounded-md border border-gray-100 bg-white py-2 text-sm shadow-lg">
                <button
                  type="button"
                  className="block w-full px-4 py-2 text-left text-gray-700 transition hover:bg-gray-50"
                  onClick={() => {
                    setMenuOpen(false)
                    navigate('/app/profile')
                  }}
                >
                  {t('app.shell.actions.profile')}
                </button>
                <button
                  type="button"
                  className="block w-full px-4 py-2 text-left text-rose-600 transition hover:bg-rose-50"
                  onClick={() => {
                    setMenuOpen(false)
                    onLogout()
                  }}
                >
                  {t('app.shell.actions.logout')}
                </button>
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
                className="rounded-md border border-gray-200 px-3 py-2 text-sm text-gray-600 transition hover:bg-gray-50"
                onClick={() => setSearchOpen(false)}
              >
                {t('common.actions.close')}
              </button>
            </div>

            <div className="mt-4 space-y-4">
              {searchQuery.trim().length < 2 ? (
                <p className="text-sm text-gray-500">{t('app.topbar.search.hint')}</p>
              ) : (
                <>
                  {searchLoading && <div className="text-sm text-gray-500">{t('app.topbar.search.loading')}</div>}
                  {!searchLoading && searchError && (
                    <div className="text-sm text-rose-600">{searchError}</div>
                  )}
                  {!searchLoading && !searchError && searchResults.length === 0 && (
                    <div className="text-sm text-gray-500">{t('app.topbar.search.empty')}</div>
                  )}
                  <ul className="divide-y divide-gray-100 rounded-lg border border-gray-100">
                    {searchResults.map((result) => (
                      <li key={`${result.type}-${result.id}`}>
                        <button
                          type="button"
                          className="flex w-full flex-col items-start gap-1 px-4 py-3 text-left transition hover:bg-gray-50"
                          onClick={() => navigateToResult(result)}
                        >
                          <span className="text-xs uppercase text-gray-400">
                            {t(RESULT_LABEL_KEYS[result.type])}
                          </span>
                          <span className="text-sm font-semibold text-gray-900">{result.title}</span>
                          {result.subtitle && (
                            <span className="text-xs text-gray-500">{result.subtitle}</span>
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
                    className="rounded-lg border border-gray-200 px-4 py-3 text-left text-sm text-gray-700 transition hover:border-brand-500 hover:text-brand-900"
                    onClick={() => {
                      const trimmed = searchQuery.trim()
                      setSearchOpen(false)
                      setSearchQuery('')
                      const dest = trimmed ? `${target.path}?q=${encodeURIComponent(trimmed)}` : target.path
                      navigate(dest)
                    }}
                  >
                    <div className="text-xs uppercase text-gray-400">{t('app.topbar.search.quick_section')}</div>
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

function BellIcon() {
  return (
    <svg
      className="h-5 w-5 text-gray-600"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M15 8a5 5 0 1 0-10 0c0 6-2 7-2 7h14s-2-1-2-7" />
      <path d="M11.73 17a2 2 0 0 1-3.46 0" />
    </svg>
  )
}
