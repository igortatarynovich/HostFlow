import clsx from 'clsx'
import type { ReactNode } from 'react'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { PageHeader } from '../nav/PageHeader'
import { useI18n } from '../../i18n'
import type { PageBreadcrumbItem } from '../nav/PageBreadcrumb'

export type SettingsSubpageHeaderProps = {
  backHref?: string
  backLabel: string
  kicker?: string
  title: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  className?: string
  children?: ReactNode
  contentClassName?: string
}

function stripBackArrow(label: string): string {
  return label.replace(/^[←\s]+/, '').trim() || label
}

function buildSettingsBreadcrumbItems(
  backHref: string,
  backLabel: string,
  titleLabel: string | null,
  settingsLabel: string,
): PageBreadcrumbItem[] {
  const parentLabel =
    backHref === CRM_APP_PATHS.settings ? settingsLabel : stripBackArrow(backLabel)

  const items: PageBreadcrumbItem[] =
    backHref === CRM_APP_PATHS.settings
      ? [{ label: settingsLabel, to: backHref }]
      : [
          { label: settingsLabel, to: CRM_APP_PATHS.settings },
          { label: parentLabel, to: backHref },
        ]

  if (titleLabel) {
    items.push({ label: titleLabel })
  }

  return items
}

function mergeSubtitle(kicker: string | undefined, subtitle: ReactNode | undefined): ReactNode {
  if (kicker && subtitle) {
    return (
      <>
        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">{kicker}</p>
        <div className="max-w-3xl text-xs leading-relaxed text-slate-600 sm:text-sm sm:leading-relaxed">{subtitle}</div>
      </>
    )
  }
  if (kicker) {
    return (
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">{kicker}</p>
    )
  }
  if (subtitle) {
    return <div className="max-w-3xl text-xs leading-relaxed text-slate-600 sm:text-sm sm:leading-relaxed">{subtitle}</div>
  }
  return undefined
}

/**
 * Shared chrome for settings drill-down pages. Renders IA v2 `PageHeader` with
 * settings-aware breadcrumbs. When `children` are passed, stacks header + body
 * in document flow so `main` can scroll — never clip content with fixed block height.
 */
export function SettingsSubpageHeader({
  backHref = CRM_APP_PATHS.settings,
  backLabel,
  kicker,
  title,
  subtitle,
  actions,
  className,
  children,
  contentClassName,
}: SettingsSubpageHeaderProps) {
  const { t } = useI18n()
  const settingsLabel = t('app.nav.items.settings', { defaultValue: 'Settings' })
  const titleLabel = typeof title === 'string' ? title : null
  const header = (
    <PageHeader
      className={className}
      breadcrumbItems={buildSettingsBreadcrumbItems(backHref, backLabel, titleLabel, settingsLabel)}
      title={titleLabel ? undefined : title}
      subtitle={mergeSubtitle(kicker, subtitle)}
      secondaryActions={actions}
      kind="browse"
    />
  )

  if (children === undefined) {
    return header
  }

  return (
    <div className="w-full">
      <div className="px-0 pt-2 pb-2">{header}</div>
      <div className={clsx('flex w-full flex-col gap-6 px-0 pb-10', contentClassName)}>
        {children}
      </div>
    </div>
  )
}
