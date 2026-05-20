import clsx from 'clsx'
import type { ReactNode } from 'react'
import type { EntityListShellProps } from './entityListTypes'

function Zone({ children, className }: { children: ReactNode; className?: string }) {
  if (children == null || children === false) return null
  return <div className={className}>{children}</div>
}

/**
 * ADR-010 list shell: fixed zone order, composition-only API (no boolean prop explosion).
 * Business cells and column definitions stay in the owning module.
 */
export default function EntityListShell({
  zones,
  selection,
  resourceLabel = 'entity list',
  className,
}: EntityListShellProps) {
  const showBulk =
    zones.bulkBar != null && selection != null && selection.selectedCount > 0

  return (
    <section
      className={clsx('entity-list-shell crm-page-stack min-h-0 flex-1', className)}
      aria-label={resourceLabel}
      data-entity-list-shell
    >
      <Zone className="entity-list-zone entity-list-zone-header">{zones.header}</Zone>
      <Zone className="entity-list-zone entity-list-zone-insights">{zones.insights}</Zone>
      <Zone className="entity-list-zone entity-list-zone-toolbar">{zones.toolbar}</Zone>
      <Zone className="entity-list-zone entity-list-zone-active-filters">{zones.activeFilters}</Zone>

      <div className="entity-list-body flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="entity-list-zone entity-list-zone-table entity-list-table-scroll min-h-0 min-w-0 flex-1">
          {zones.table}
        </div>
        {showBulk ? (
          <div
            className="entity-list-zone entity-list-zone-bulk shrink-0"
            data-entity-list-bulk
            role="region"
            aria-label="Bulk actions"
          >
            {zones.bulkBar}
          </div>
        ) : null}
      </div>

      <Zone className="entity-list-zone entity-list-zone-pagination shrink-0">{zones.pagination}</Zone>
    </section>
  )
}
