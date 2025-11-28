import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import type { TenantRecord, WhoAmI } from '../api/types'
import { getCurrentTenant } from '../api/tenants'
import type { NavItem } from './routes'
import { Sidebar } from '../components/nav/Sidebar'
import { Topbar } from '../components/nav/Topbar'

type AppShellProps = {
  me: WhoAmI | null
  navItems: NavItem[]
  onLogout: () => void
}

export function AppShell({ me, navItems, onLogout }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    try {
      const stored = window.localStorage.getItem('hf:ui:sidebar-open')
      if (stored === '1') return true
      if (stored === '0') return false
    } catch {
      // ignore access issues
    }
    return false
  })
  const [tenant, setTenant] = useState<TenantRecord | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      window.localStorage.setItem('hf:ui:sidebar-open', sidebarOpen ? '1' : '0')
    } catch {
      // ignore
    }
  }, [sidebarOpen])

  useEffect(() => {
    let cancelled = false
    if (!me?.tenant_id) {
      setTenant(null)
      return () => {
        cancelled = true
      }
    }
    ;(async () => {
      try {
        const info = await getCurrentTenant()
        if (!cancelled) setTenant(info)
      } catch (err) {
        console.warn('[AppShell] failed to load tenant', err)
        if (!cancelled) setTenant(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [me?.tenant_id])

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900">
      <Sidebar
        tenant={tenant}
        items={navItems}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onLogout={onLogout}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar
          me={me}
          tenant={tenant}
          onLogout={onLogout}
          onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
        />

        <main className="flex-1 overflow-y-auto">
          <div className="w-full px-6 py-6 lg:px-10">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
