import { useMemo } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { IconChevronRight, IconHome } from '@tabler/icons-react'

import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useBusinessTerminology } from '../../hooks/useBusinessTerminology'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import { buildBreadcrumbTrail } from '../../nav/breadcrumbRegistry'

export type PageBreadcrumbItem = {
  /** Display label (already translated). */
  label: string
  /** Optional href — when omitted the item renders as plain (current) text. */
  to?: string
}

type PageBreadcrumbProps = {
  className?: string
  /**
   * Override the trail derived from the current pathname. Useful for dynamic
   * detail pages (e.g. candidate card) when you want to inject the entity
   * name as the leaf segment instead of relying on the URL alone.
   */
  items?: PageBreadcrumbItem[]
  /**
   * Override only the **leaf** label while keeping the auto-derived parent
   * trail. Mutually exclusive with `items`.
   */
  currentLabel?: string
  /**
   * Force-hide the home (`/app/overview`) icon link. Defaults to `false`.
   */
  hideHome?: boolean
}

/**
 * Replacement for the legacy `CrmContourWayfindingStrip` chip-row.
 *
 * Renders a compact, hierarchical breadcrumb (`Home › Section › Subsection ›
 * Current`) derived from the current pathname against
 * `BREADCRUMB_REGISTRY`. Permission-gated parent links degrade to plain text
 * when the current user lacks access. Dynamic detail pages can pass
 * `currentLabel` to inject an entity name as the leaf segment, or `items`
 * to take full control of the trail.
 */
export function PageBreadcrumb({
  className = '',
  items,
  currentLabel,
  hideHome = false,
}: PageBreadcrumbProps) {
  const { t } = useI18n()
  const { pathname } = useLocation()
  const { can } = usePermissions()
  const { entityPlural: clientsLabel } = useBusinessTerminology()

  const trail = useMemo<PageBreadcrumbItem[]>(() => {
    if (items && items.length > 0) return items

    const derived = buildBreadcrumbTrail(pathname)
    if (derived.length === 0 && !currentLabel) return []

    const list: PageBreadcrumbItem[] = derived.map((step, idx) => {
      const isLeaf = idx === derived.length - 1
      const labelKey = step.entry.labelKey
      const translated =
        labelKey === 'app.nav.items.clients' && clientsLabel ? clientsLabel : t(labelKey)
      const accessible = !step.entry.permission || can(step.entry.permission)
      return {
        label: translated,
        to: !isLeaf && accessible ? step.path : undefined,
      }
    })

    if (currentLabel) {
      if (list.length > 0) {
        list[list.length - 1] = {
          ...list[list.length - 1],
          to: undefined,
          label: currentLabel,
        }
      } else {
        list.push({ label: currentLabel })
      }
    }
    return list
  }, [items, currentLabel, pathname, can, clientsLabel, t])

  const showHome = !hideHome
  if (trail.length === 0 && !showHome) return null

  const homeLabel = t('app.nav.items.overview')
  const homePath = CRM_APP_PATHS.overview
  const isOnHome = (pathname.replace(/\/+$/, '') || '/') === homePath

  return (
    <nav
      aria-label={t('common.breadcrumb', { defaultValue: 'Breadcrumb' })}
      className={`flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1 text-xs text-slate-500 ${className}`}
    >
      {showHome && (
        <>
          {isOnHome ? (
            <span className="inline-flex items-center gap-1 font-semibold text-slate-700">
              <IconHome size={13} aria-hidden />
              <span>{homeLabel}</span>
            </span>
          ) : (
            <Link
              to={homePath}
              className="inline-flex items-center gap-1 rounded px-1 py-0.5 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
            >
              <IconHome size={13} aria-hidden />
              <span>{homeLabel}</span>
            </Link>
          )}
        </>
      )}
      {trail.map((item, idx) => {
        const isLeaf = idx === trail.length - 1
        const showSeparator = showHome || idx > 0
        return (
          <span key={`${idx}-${item.label}`} className="inline-flex min-w-0 items-center gap-1.5">
            {showSeparator && (
              <IconChevronRight
                size={12}
                aria-hidden
                className="shrink-0 text-slate-300"
              />
            )}
            {item.to && !isLeaf ? (
              <Link
                to={item.to}
                className="truncate rounded px-1 py-0.5 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
              >
                {item.label}
              </Link>
            ) : (
              <span
                className={`truncate ${isLeaf ? 'font-semibold text-slate-700' : 'text-slate-500'}`}
                aria-current={isLeaf ? 'page' : undefined}
              >
                {item.label}
              </span>
            )}
          </span>
        )
      })}
    </nav>
  )
}
