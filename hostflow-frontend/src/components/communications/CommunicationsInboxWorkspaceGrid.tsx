import clsx from 'clsx'
import type { ReactNode } from 'react'

/**
 * Shared inbox workspace grids (gap + xl column templates).
 * - Channel pages: Messages / Email.
 * - Communication Center: unified list + work + control rail (same rail width family as Messages).
 */
export type CommunicationsInboxWorkspaceGridVariant =
  | 'messages_with_rail'
  | 'email_with_rail'
  | 'inbox_center'

const GRID_TEMPLATE: Record<CommunicationsInboxWorkspaceGridVariant | 'email_with_rail_collapsed', string> = {
  messages_with_rail: 'xl:grid-cols-[340px_minmax(400px,1fr)_minmax(260px,20rem)]',
  email_with_rail: 'xl:grid-cols-[230px_minmax(280px,340px)_minmax(280px,1fr)_minmax(260px,19rem)]',
  /** Folders column collapsed to a narrow strip on xl+ */
  email_with_rail_collapsed: 'xl:grid-cols-[52px_minmax(280px,340px)_minmax(280px,1fr)_minmax(260px,19rem)]',
  /** Unified thread list | timeline/compose | control panel — matches Messages rail column (`20rem`). */
  inbox_center: 'xl:grid-cols-[minmax(280px,20rem)_minmax(320px,1fr)_minmax(260px,20rem)]',
}

export function communicationsInboxWorkspaceGridClass(
  variant: CommunicationsInboxWorkspaceGridVariant,
  options?: { isMobile?: boolean; className?: string; emailFoldersCollapsed?: boolean },
): string {
  const key: keyof typeof GRID_TEMPLATE =
    variant === 'email_with_rail' && options?.emailFoldersCollapsed ? 'email_with_rail_collapsed' : variant
  const isMessages = variant === 'messages_with_rail'
  return clsx(
    'grid gap-4',
    GRID_TEMPLATE[key],
    isMessages && 'min-h-0 max-h-[calc(100dvh-7rem)] flex-1 overflow-hidden xl:grid-rows-1',
    !isMessages && options?.isMobile && 'min-h-0 flex-1',
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
