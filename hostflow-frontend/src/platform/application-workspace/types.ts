import type { ReactNode } from 'react'
import type { Application, ApplicationModule, ApplicationTab, ApplicationListResponse } from '../../api/types/application'

export type ApplicationDetailRenderProps = {
  application: Application
  onRefresh: () => void
  onClose: () => void
}

export type ApplicationTabDef = {
  id: ApplicationTab
  label: string
}

export type ApplicationListOptions = {
  limit?: number
  offset?: number
  tab?: ApplicationTab
  scope?: 'open' | 'all'
  includeCounts?: boolean
  /** Latest call-outcome activity (not ticket status). */
  callResult?: string
  q?: string
}

export type ApplicationWorkspaceConfig = {
  module: ApplicationModule
  objectNamePlural: string
  homePath: string
  applicationPath: (id: string) => string
  listApplications: (opts?: ApplicationListOptions) => Promise<ApplicationListResponse>
  getApplication: (id: string) => Promise<Application>
  tabs: ApplicationTabDef[]
  /** When true, list is fetched per tab from the server with pagination. */
  serverTabPagination?: boolean
  workSessionSurface: 'sales' | 'recruitment'
  workSessionKind: string
  heroCallTitle: (count: number) => string
  heroCallHint: string
  heroEmptyText: string
  listKindLabel: string
  extensionBadge?: (application: Application) => string | null
  /** Show latest call-outcome activity as a list column + filter. */
  showCallOutcome?: boolean
  /** When set, list title and rail header link to Entity Workspace (e.g. client card). */
  primaryEntityPath?: (application: Application) => string | undefined
  primaryEntityLabel?: string
  renderDetail: (props: ApplicationDetailRenderProps) => ReactNode
}
