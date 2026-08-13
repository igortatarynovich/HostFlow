import clsx from 'clsx'
import type { HTMLAttributes, ReactNode } from 'react'

import { STATUS_BADGE_SEMANTIC_CLASSES, type StatusBadgeSemantic } from './statusBadgeSemantics'

export type SemanticSurfaceTone = StatusBadgeSemantic

export type SemanticSurfaceProps = {
  tone: SemanticSurfaceTone
  children: ReactNode
  className?: string
} & Omit<HTMLAttributes<HTMLElement>, 'children' | 'className'>

/** Platform-owned emphasis surface. Modules pass tone, not palettes or gradients. */
export function SemanticSurface({ tone, children, className, ...rest }: SemanticSurfaceProps) {
  return (
    <section className={clsx('p-4', STATUS_BADGE_SEMANTIC_CLASSES[tone], className)} {...rest}>
      {children}
    </section>
  )
}
