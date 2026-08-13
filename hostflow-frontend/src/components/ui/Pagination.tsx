import clsx from 'clsx'

import { Button } from './Button'

export type PaginationProps = {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  className?: string
  previousLabel?: string
  nextLabel?: string
  pageLabel?: (page: number, totalPages: number) => string
}

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  className,
  previousLabel = 'Previous',
  nextLabel = 'Next',
  pageLabel = (p, totalPages) => `Page ${p} of ${totalPages}`,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const safePage = Math.min(Math.max(1, page), totalPages)

  return (
    <nav
      className={clsx('entity-list-pagination flex items-center justify-between gap-3 text-xs text-slate-600', className)}
      aria-label="Pagination"
    >
      <Button
        variant="secondary"
        size="xs"
        disabled={safePage <= 1}
        onClick={() => onPageChange(safePage - 1)}
      >
        {previousLabel}
      </Button>
      <span>{pageLabel(safePage, totalPages)}</span>
      <Button
        variant="secondary"
        size="xs"
        disabled={safePage >= totalPages}
        onClick={() => onPageChange(safePage + 1)}
      >
        {nextLabel}
      </Button>
    </nav>
  )
}
