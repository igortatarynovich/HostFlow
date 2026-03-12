import { useMemo } from 'react'
import { Link, useLocation } from 'react-router-dom'
import type { NavItem, NavGroup } from '../../app/routes'
import { NAV_GROUP_MAP } from '../../app/routes'
import { useI18n } from '../../i18n'

type BreadcrumbsProps = {
  navItems: NavItem[]
}

export function Breadcrumbs({ navItems }: BreadcrumbsProps) {
  const location = useLocation()
  const { t } = useI18n()

  const data = useMemo(() => {
    const cleanPath = location.pathname.replace(/\/+$/, '') || '/'
    const matched = navItems
      .filter((item) => item.path && cleanPath.startsWith(item.path))
      .sort((a, b) => (b.path!.length ?? 0) - (a.path!.length ?? 0))[0]

    const crumbs: Array<{ label?: string; labelKey?: string; path?: string }> = []
    if (matched?.path) {
      crumbs.push({ labelKey: matched.labelKey, path: matched.path })
      const remainder = cleanPath.slice(matched.path.length)
      const segments = remainder.split('/').filter(Boolean)
      let acc = matched.path
      segments.forEach((segment) => {
        acc = `${acc}/${segment}`
        crumbs.push({ label: humanizeSegment(segment), path: acc })
      })
    } else if (cleanPath !== '/') {
      crumbs.push({ label: humanizeSegment(cleanPath.split('/').pop() || ''), path: cleanPath })
    }

    const lastCrumb = crumbs.length > 0 ? crumbs[crumbs.length - 1] : undefined
    const titleKey = lastCrumb?.labelKey
    const titleLabel = lastCrumb?.label
    const groupLabelKey = matched
      ? NAV_GROUP_MAP[matched.group as NavGroup]?.labelKey
      : NAV_GROUP_MAP.overview.labelKey

    return { crumbs, titleKey, titleLabel, groupLabelKey }
  }, [location.pathname, navItems])

  return (
    <div className="border-b border-slate-200 pb-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        {t(data.groupLabelKey ?? 'app.nav.groups.overview')}
      </div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">
        {data.titleKey ? t(data.titleKey) : data.titleLabel ?? t('app.nav.items.overview')}
      </div>
      {data.crumbs.length > 1 && (
        <nav className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-500">
          {data.crumbs.map((crumb, index) => {
            const isLast = index === data.crumbs.length - 1
            const crumbKey = crumb.label ?? crumb.labelKey ?? String(index)
            return (
              <span key={`${crumbKey}-${index}`} className="inline-flex items-center gap-2">
                {crumb.path && !isLast ? (
                  <Link to={crumb.path} className="transition hover:text-brand-800">
                    {crumb.labelKey ? t(crumb.labelKey) : crumb.label}
                  </Link>
                ) : (
                  <span>{crumb.labelKey ? t(crumb.labelKey) : crumb.label}</span>
                )}
                {!isLast && <span className="text-slate-300">/</span>}
              </span>
            )
          })}
        </nav>
      )}
    </div>
  )
}

function humanizeSegment(value: string) {
  if (!value) return ''
  const decoded = decodeURIComponent(value)
  if (/^[0-9a-f-]{8,}$/i.test(decoded)) {
    return `#${decoded.slice(0, 8)}`
  }
  return decoded.replace(/[-_]/g, ' ')
}
