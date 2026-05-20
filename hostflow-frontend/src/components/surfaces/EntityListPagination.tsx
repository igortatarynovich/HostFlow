import clsx from 'clsx'
import type { EntityListPaginationState } from './entityListTypes'

export type EntityListPaginationProps = EntityListPaginationState & {
  className?: string
  previousLabel?: string
  nextLabel?: string
  pageLabel?: (page: number, totalPages: number) => string
}

export default function EntityListPagination({
  page,
  pageSize,
  total,
  onPageChange,
  className,
  previousLabel = 'Previous',
  nextLabel = 'Next',
  pageLabel = (p, totalPages) => `Page ${p} of ${totalPages}`,
}: EntityListPaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const safePage = Math.min(Math.max(1, page), totalPages)

  return (
    <nav
      className={clsx('entity-list-pagination flex items-center justify-between gap-3 text-xs text-slate-600', className)}
      aria-label="Pagination"
    >
      <button
        type="button"
        className="btn-secondary btn-xs"
        disabled={safePage <= 1}
        onClick={() => onPageChange(safePage - 1)}
      >
        {previousLabel}
      </button>
      <span>{pageLabel(safePage, totalPages)}</span>
      <button
        type="button"
        className="btn-secondary btn-xs"
        disabled={safePage >= totalPages}
        onClick={() => onPageChange(safePage + 1)}
      >
        {nextLabel}
      </button>
    </nav>
  )
}
