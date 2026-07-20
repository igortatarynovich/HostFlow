import clsx from 'clsx'
import type { ReactNode } from 'react'

/**
 * Shared inbox workspace grids (gap + xl column templates).
 * Canon: Thread chronology dominates (~60–70%); left = navigation; right = context rail.
 */
export type CommunicationsInboxWorkspaceGridVariant =
  | 'messages_with_rail'
  | 'email_with_rail'
  | 'inbox_center'

const GRID_TEMPLATE: Record<CommunicationsInboxWorkspaceGridVariant | 'email_with_rail_collapsed', string> = {
  /** list | thread | context — thread gets the flexible majority */
  messages_with_rail: 'xl:grid-cols-[minmax(220px,16rem)_minmax(0,1fr)_minmax(220px,16rem)]',
  /** folders | list | thread | context */
  email_with_rail: 'xl:grid-cols-[minmax(140px,11rem)_minmax(200px,15rem)_minmax(0,1fr)_minmax(220px,16rem)]',
  /** Folders column collapsed to a narrow strip on xl+ */
  email_with_rail_collapsed: 'xl:grid-cols-[52px_minmax(200px,15rem)_minmax(0,1fr)_minmax(220px,16rem)]',
  /** Unified thread list | Thread workspace | Context rail */
  inbox_center: 'xl:grid-cols-[minmax(220px,16rem)_minmax(0,1fr)_minmax(220px,16rem)]',
}

export function communicationsInboxWorkspaceGridClass(
  variant: CommunicationsInboxWorkspaceGridVariant,
  options?: { isMobile?: boolean; className?: string; emailFoldersCollapsed?: boolean },
): string {
  const key: keyof typeof GRID_TEMPLATE =
    variant === 'email_with_rail' && options?.emailFoldersCollapsed ? 'email_with_rail_collapsed' : variant
  const fillViewport =
    variant === 'messages_with_rail' || variant === 'email_with_rail' || variant === 'inbox_center'
  return clsx(
    'grid gap-3',
    GRID_TEMPLATE[key],
    fillViewport && 'min-h-0 max-h-[calc(100dvh-6.5rem)] flex-1 overflow-hidden xl:grid-rows-1',
    !fillViewport && options?.isMobile && 'min-h-0 flex-1',
    options?.className,
  )
}

export default function CommunicationsInboxWorkspaceGrid({
  variant,
  isMobile,
  className,
  emailFoldersCollapsed,
  children,
}: {
  variant: CommunicationsInboxWorkspaceGridVariant
  isMobile?: boolean
  className?: string
  /** When `variant` is `email_with_rail`, narrows the first column to a strip. */
  emailFoldersCollapsed?: boolean
  children: ReactNode
}) {
  return (
    <div className={communicationsInboxWorkspaceGridClass(variant, { isMobile, className, emailFoldersCollapsed })}>
      {children}
    </div>
  )
}
