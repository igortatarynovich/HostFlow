import clsx from 'clsx'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import type { WhoAmI } from '../api/types'
import { usePermissions } from '../hooks/usePermissions'
import { useI18n } from '../i18n'
import { PublicBrandingLogo } from '../components/public/PublicLogo'

const SIDEBAR_WIDTH = 256
const SIDEBAR_STORAGE_KEY = 'hf:ui:sidebar_open'

// Main application layout (sidebar + topbar + content)
export function Layout({ me, onLogout, children }:{
  me: WhoAmI | null
  onLogout: () => void
  children: React.ReactNode
}){
  const { t } = useI18n()
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    try {
      const stored = window.localStorage.getItem(SIDEBAR_STORAGE_KEY)
      if (stored === 'closed') return false
      if (stored === 'open') return true
    } catch {}
    return false
  })
  const navigate = useNavigate()

  useEffect(() => {
    try {
      window.localStorage.setItem(SIDEBAR_STORAGE_KEY, sidebarOpen ? 'open' : 'closed')
    } catch {}
  }, [sidebarOpen])

  const toggleSidebar = () => setSidebarOpen((value) => !value)
  const closeSidebar = () => setSidebarOpen(false)
  const handleNavigate = () => {
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      closeSidebar()
    }
  }

  return (
    <div className="h-screen w-screen overflow-hidden bg-slate-50">
      <aside
        className={clsx(
          'fixed top-0 left-0 z-20 h-full transform bg-brand-900 text-white shadow-xl transition-transform duration-300 ease-in-out',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
        style={{ width: SIDEBAR_WIDTH }}
      >
        <Sidebar
          me={me}
          onLogout={onLogout}
          onNavigate={handleNavigate}
          onNavigateProfile={() => {
            navigate('/profile')
            handleNavigate()
          }}
        />
      </aside>

      {/* Main column */}
      <div
        className="flex h-full flex-col transition-[padding-left] duration-300 ease-in-out"
        style={{ paddingLeft: sidebarOpen ? SIDEBAR_WIDTH : 0 }}
      >
        <header className="relative flex h-20 items-center justify-between border-b border-slate-200 bg-white px-6">
          <button
            type="button"
            className="rounded-md p-2 text-brand-900 outline-none ring-brand-500 transition hover:bg-brand-900/10 focus-visible:ring-2"
            aria-label={t('app.layout.toggle_sidebar')}
            onClick={toggleSidebar}
          >
            <span aria-hidden className="block h-0.5 w-5 bg-current shadow-[0_6px_0_0_currentColor,0_12px_0_0_currentColor]" />
          </button>

          <div className="flex flex-1 items-center justify-center px-4">
            <PublicBrandingLogo showWordmark className="text-brand-900" />
          </div>

          <div className="w-10" /> {/* spacer to balance toggle button */}
        </header>

        <main className="flex-1 overflow-auto p-6">
          <div className="app-surface h-full min-h-full p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

// Left navigation sidebar. Kept in the same file for convenience,
// but exported so it can be reused in Storybook/tests if needed.
export function Sidebar({
  me,
  onLogout,
  onNavigate,
  onNavigateProfile,
}: {
  me: WhoAmI | null
  onLogout: () => void
  onNavigate: () => void
  onNavigateProfile: () => void
}) {
  const { t } = useI18n()
  const { can } = usePermissions()

  return (
    <div className="flex h-full w-full flex-col px-4 py-6">
      <div className="mb-6">
        <PublicBrandingLogo showWordmark white />
      </div>

      <nav className="flex-1 overflow-y-auto space-y-2">
        <Link
          to="/"
          className="block rounded px-3 py-2 text-sm transition hover:bg-white/10"
          onClick={onNavigate}
        >
          {t('app.layout.nav.dashboard')}
        </Link>
        {can('companies.view') && (
          <Link
            to="/companies"
            className="block rounded px-3 py-2 text-sm transition hover:bg-white/10"
            onClick={onNavigate}
          >
            {t('app.layout.nav.companies')}
          </Link>
        )}
        {can('leads.view') && (
          <Link
            to="/leads"
            className="block rounded px-3 py-2 text-sm transition hover:bg-white/10"
            onClick={onNavigate}
          >
            {t('app.layout.nav.leads')}
          </Link>
        )}
        {can('notifications.view') && (
          <Link
            to="/notifications"
            className="block rounded px-3 py-2 text-sm transition hover:bg-white/10"
            onClick={onNavigate}
          >
            {t('app.layout.nav.notifications')}
          </Link>
        )}
        {can('vacancies.view') && (
          <Link
            to="/vacancies"
            className="block rounded px-3 py-2 text-sm transition hover:bg-white/10"
            onClick={onNavigate}
          >
            {t('app.layout.nav.vacancies')}
          </Link>
        )}
        {can('services.view') && (
          <Link
            to="/services"
            className="block rounded px-3 py-2 text-sm transition hover:bg-white/10"
            onClick={onNavigate}
          >
            {t('app.layout.nav.services')}
          </Link>
        )}
        {can('candidates.view') && (
          <Link
            to="/app/candidates"
            className="block rounded px-3 py-2 text-sm transition hover:bg-white/10"
            onClick={onNavigate}
          >
            {t('app.layout.nav.candidates')}
          </Link>
        )}
        {can('candidates.pipeline') && (
          <Link
            to="/pipeline"
            className="block rounded px-3 py-2 text-sm transition hover:bg-white/10"
            onClick={onNavigate}
          >
            {t('app.layout.nav.pipeline')}
          </Link>
        )}
        {can('admin.users') && (
          <Link
            to="/admin/users"
            className="block rounded px-3 py-2 text-sm transition hover:bg-white/10"
            onClick={onNavigate}
          >
            {t('app.layout.nav.users')}
          </Link>
        )}
        {can('admin.companyAcl') && (
          <Link
            to="/app/settings/company-access"
            className="block rounded px-3 py-2 text-sm transition hover:bg-white/10"
            onClick={onNavigate}
          >
            {t('app.layout.nav.company_access')}
          </Link>
        )}
        {can('admin.metaLeads') && (
          <Link
            to="/settings/leads"
            className="block rounded px-3 py-2 text-sm transition hover:bg-white/10"
            onClick={onNavigate}
          >
            {t('app.layout.nav.meta_leads')}
          </Link>
        )}
        {can('admin.deletionQueue') && (
          <Link
            to="/admin/deletion-requests"
            className="block rounded px-3 py-2 text-sm transition hover:bg-white/10"
            onClick={onNavigate}
          >
            {t('app.layout.nav.deletion_requests')}
          </Link>
        )}
      </nav>

      {me && (
        <section className="mt-4 border-t border-white/10 pt-4 text-sm">
          <button
            type="button"
            onClick={onNavigateProfile}
            className="flex w-full items-center justify-between rounded px-2 py-2 text-left text-white/90 transition hover:bg-white/10"
          >
            <span className="flex items-center gap-2">
              <span className="inline-flex h-2.5 w-2.5 rounded-full bg-green-400" aria-hidden />
              <span className="truncate font-medium">
                {resolveDisplayName(me)}
              </span>
            </span>
          </button>
          <div className="mt-1 pl-6 text-xs uppercase tracking-wide text-white/60">
            {me.role}
          </div>
          <button
            type="button"
            onClick={onLogout}
            className="mt-3 w-full rounded px-2 py-2 text-left text-sm text-white/80 transition hover:bg-white/10"
          >
            {t('app.layout.actions.logout')}
          </button>
        </section>
      )}

      <footer className="mt-6 border-t border-white/10 pt-4 text-sm">
        <div className="text-white/70">{t('app.layout.section.settings')}</div>
        {can('admin.ruleset') && (
          <Link
            to="/admin/ruleset"
            className="mt-3 block rounded px-3 py-2 text-sm transition hover:bg-white/10"
            onClick={onNavigate}
          >
            {t('app.layout.nav.ruleset')}
          </Link>
        )}
      </footer>
    </div>
  )
}

function resolveDisplayName(me: WhoAmI) {
  const fullName = (me.full_name || '').trim()
  const composedName = `${me.first_name ?? ''} ${me.last_name ?? ''}`.trim()
  return fullName || composedName || me.email
}
