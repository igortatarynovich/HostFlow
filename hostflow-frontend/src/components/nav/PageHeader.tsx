import type { ReactNode } from 'react'
import clsx from 'clsx'

import { PageBreadcrumb, type PageBreadcrumbItem } from './PageBreadcrumb'

export type PageHeaderProps = {
  /**
   * Optional page title rendered as `<h1>`. When omitted, the breadcrumb leaf
   * already serves as the page label and an explicit title would duplicate it.
   */
  title?: ReactNode
  /**
   * Optional one-line subtitle shown directly under the title (or breadcrumb
   * if no title is provided). Use sparingly — most pages do not need this.
   */
  subtitle?: ReactNode
  /**
   * The single **primary** call-to-action for the page (e.g. "+ New vacancy").
   * Render as a `<button>` or `<Link>` with `className="btn-primary"`. Per
   * IA v2 spec, every operational page must have either a primary action OR
   * be explicitly marked as a `kind="browse"` page (no CTA).
   */
  primaryAction?: ReactNode
  /**
   * Optional secondary actions (filter toggle, view switch, refresh button).
   * Rendered to the left of `primaryAction`. Keep ≤ 3 buttons total here.
   */
  secondaryActions?: ReactNode
  /**
   * Override the trail derived from the current pathname. Useful for dynamic
   * detail pages — passed through to `PageBreadcrumb`.
   */
  breadcrumbItems?: PageBreadcrumbItem[]
  /**
   * Override only the leaf label of the auto-derived breadcrumb (e.g. inject
   * the candidate name on the candidate card).
   */
  breadcrumbCurrentLabel?: string
  /** Force-hide the home icon link in the breadcrumb. Defaults to `false`. */
  hideHome?: boolean
  /**
   * Declare the page intent. `action` (default) means the page **must**
   * carry a `primaryAction`; `browse` opts out (used for read-only / list
   * landing pages where the primary CTA lives on individual rows). The
   * value is informational — used by tests and lint rules.
   */
  kind?: 'action' | 'browse'
  className?: string
}

/**
 * IA v2 page header — single source of truth for the **breadcrumb + 1 CTA**
 * pattern that replaces the legacy `CrmContourWayfindingStrip`.
 *
 * Layout (mobile-first):
 * ```
 * [home › Section › Current]                      [secondary] [primary]
 * Title                                                                 ◀ optional
 * Subtitle                                                              ◀ optional
 * ```
 *
 * Contract:
 * - Every operational page renders **exactly one** `PageHeader` near the top
 *   of its main content area.
 * - Either `primaryAction` is set, or `kind="browse"` is passed explicitly.
 * - Primary action label uses the verb-noun pattern ("Add vacancy", "Send
 *   message"), never just an icon.
 *
 * See `docs/specs/frontend/page_header.md` for the full spec.
 */
export function PageHeader({
  title,
  subtitle,
  primaryAction,
  secondaryActions,
  breadcrumbItems,
  breadcrumbCurrentLabel,
  hideHome = false,
  className,
}: PageHeaderProps) {
  const hasActions = Boolean(primaryAction) || Boolean(secondaryActions)

  return (
    <header className={clsx('flex flex-col gap-1', className)}>
      <div className="flex flex-wrap items-center justify-between gap-1.5">
        <PageBreadcrumb
          items={breadcrumbItems}
          currentLabel={breadcrumbCurrentLabel}
          hideHome={hideHome}
          className="min-w-0 flex-1"
        />
        {hasActions ? (
          <div className="flex shrink-0 flex-wrap items-center gap-1.5">
            {secondaryActions}
            {primaryAction}
          </div>
        ) : null}
      </div>
      {title ? (
        <h1 className="truncate text-lg font-semibold text-slate-900">
          {title}
        </h1>
      ) : null}
      {subtitle ? (
        <div className="text-sm text-slate-500">{subtitle}</div>
      ) : null}
    </header>
  )
}
