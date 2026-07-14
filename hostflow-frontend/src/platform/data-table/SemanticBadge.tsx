import clsx from 'clsx'
import { StatusBadge } from '../../components/ui/StatusBadge'
import type { StatusBadgeSize } from '../../components/ui/statusBadgeSemantics'
import type { SemanticRole } from './types'
import { semanticRoleToBadgeSemantic } from './semanticRoles'

export type SemanticBadgeProps = {
  label: string
  semanticRole: SemanticRole
  size?: StatusBadgeSize
  title?: string
  shape?: 'default' | 'pill'
  className?: string
}

/** Platform badge — modules pass semantic role, never Tailwind color classes. */
export function SemanticBadge({
  label,
  semanticRole,
  size = 'md',
  title,
  shape = 'default',
  className,
}: SemanticBadgeProps) {
  return (
    <StatusBadge
      label={label}
      semantic={semanticRoleToBadgeSemantic(semanticRole)}
      size={size}
      title={title ?? label}
      shape={shape}
      className={className}
    />
  )
}
