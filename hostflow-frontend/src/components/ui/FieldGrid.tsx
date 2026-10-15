import type { ReactNode } from 'react'
import clsx from 'clsx'

type Props = {
  cols?: 1 | 2 | 3
  /** Entity workspace density: flowing pairs, empty cell only after the last field. */
  dense?: boolean
  /** Participate in a parent FieldGrid. The section does not start another grid. */
  flow?: boolean
  className?: string
  testId?: string
  children: ReactNode
}

export function FieldGrid({ cols = 2, dense = false, flow = false, className, testId, children }: Props) {
  if (flow) return <div className={clsx('contents', className)} data-testid={testId}>{children}</div>
  const columns = cols === 1
    ? 'grid-cols-1'
    : cols === 3
      ? 'grid-cols-1 md:grid-cols-3'
      : 'grid-cols-1 md:grid-cols-2'
  return (
    <div
      className={clsx('grid items-start', dense ? 'gap-x-8 gap-y-0' : 'gap-4', columns, className)}
      data-testid={testId}
    >
      {children}
    </div>
  )
}
