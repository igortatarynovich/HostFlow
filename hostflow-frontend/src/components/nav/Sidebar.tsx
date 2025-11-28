import clsx from 'clsx'
import { useEffect, useMemo, useState } from 'react'
import { NavLink } from 'react-router-dom'
import type { TenantSummary } from '../../api/types'
import type { NavItem } from '../../app/routes'
import { NAV_GROUPS } from '../../app/routes'
import { useI18n } from '../../i18n'

type SidebarProps = {
  items: NavItem[]
  tenant: TenantSummary | null
  open: boolean
  onClose: () => void
  onLogout: () => void
}

const GROUP_STORAGE_KEY = 'hf:ui:sidebar-groups'

export function Sidebar({ items, tenant, open, onClose, onLogout }: SidebarProps) {
  const { t } = useI18n()

  const sections = useMemo(
    () =>
      NAV_GROUPS.filter((section) => section.key !== 'account')
        .map((section) => ({
          ...section,
          label: t(section.labelKey),
          items: items.filter((item) => item.group === section.key && item.path),
        }))
        .filter((section) => section.items.length > 0),
    [items, t]
  )

  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>(() => {
    if (typeof window === 'undefined') {
      return Object.fromEntries(sections.map((section) => [section.key, true]))
    }
    try {
      const raw = window.localStorage.getItem(GROUP_STORAGE_KEY)
      if (!raw) throw new Error('no-cache')
      const parsed = JSON.parse(raw)
      return { ...Object.fromEntries(sections.map((section) => [section.key, true])), ...parsed }
    } catch {
      return Object.fromEntries(sections.map((section) => [section.key, true]))
    }
  })

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(GROUP_STORAGE_KEY, JSON.stringify(expandedGroups))
  }, [expandedGroups])

  useEffect(() => {
    setExpandedGroups((prev) => {
      const next = { ...prev }
      sections.forEach((section) => {
        if (!(section.key in next)) {
          next[section.key] = true
        }
      })
      return next
    })
  }, [sections])

  const handleNavigate = () => {
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      onClose()
    }
  }

  const tenantLabel = tenant?.workspace_label?.trim() || tenant?.name || 'HostFlow'

  return (
    <>
      <div
        className={clsx(
          'relative z-40 bg-brand-900 transition-[width] duration-300',
          open ? 'w-screen max-w-sm lg:w-72 lg:max-w-none' : 'w-0'
        )}
        aria-hidden={!open}
      >
        <div
          className={clsx(
            'fixed inset-y-0 left-0 flex h-full flex-col bg-brand-900 text-white transition-transform duration-300',
            open ? 'translate-x-0' : '-translate-x-full',
            'w-screen max-w-sm lg:max-w-none lg:w-72'
          )}
        >
          <div className="px-4 py-4">
            <div className="text-xs uppercase tracking-[0.3em] text-white/60">
              {t('app.shell.sidebar.workspace')}
            </div>
            <div className="text-lg font-semibold">{tenantLabel}</div>
          </div>

          <nav className="flex-1 overflow-y-auto px-3 pb-6">
            {sections.map((section, index) => {
              const expanded = expandedGroups[section.key] ?? true
              return (
                <div key={section.key} className="space-y-2">
                  <div>
                    <button
                      type="button"
                      className="flex w-full items-center justify-between rounded-md px-3 py-2 text-xs font-semibold uppercase tracking-widest text-white/60 hover:bg-white/5"
                      onClick={() =>
                        setExpandedGroups((prev) => ({ ...prev, [section.key]: !expanded }))
                      }
                    >
                      <span>{section.label}</span>
                      <span
                        className={clsx(
                          'text-lg leading-none transition-transform',
                          expanded ? 'rotate-0' : '-rotate-90'
                        )}
                      >
                        ‹
                      </span>
                    </button>

                    <div className={clsx('mt-2 space-y-1', !expanded && 'hidden')}>
                      {section.items.map((item) => (
                        <NavLink
                          key={item.key}
                          to={item.path!}
                          title={t(item.labelKey)}
                          onClick={handleNavigate}
                          className={({ isActive }) =>
                            clsx(
                              'block rounded-md px-3 py-2 text-sm transition',
                              isActive ? 'bg-white text-brand-900' : 'text-white/90 hover:bg-white/10'
                            )
                          }
                        >
                          {t(item.labelKey)}
                        </NavLink>
                      ))}
                    </div>
                  </div>
                  {index < sections.length - 1 && (
                    <div className="mx-4 my-3 border-t border-white/15" />
                  )}
                </div>
              )
            })}
          </nav>

          <div className="border-t border-white/10 px-3 py-3 text-sm">
            <button
              type="button"
              className="flex w-full items-center justify-center gap-2 rounded-md border border-white/20 px-3 py-2 text-white/90 transition hover:bg-white/10"
              onClick={onLogout}
            >
              {t('app.shell.actions.logout')}
            </button>
          </div>
        </div>
      </div>
      {open && (
        <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={onClose} role="presentation" />
      )}
    </>
  )
}
