import { CRM_APP_PATHS as P } from './crmAppPaths'

function pathOnly(pathname: string): string {
  const cut = pathname.split(/[?#]/)[0] || pathname
  return cut.endsWith('/') && cut.length > 1 ? cut.slice(0, -1) : cut
}

function isExact(path: string, base: string): boolean {
  return path === base
}

function isPathOrChild(path: string, base: string): boolean {
  return path === base || path.startsWith(`${base}/`)
}

/**
 * Native list / split-table workspaces. These pages bleed to the main edges
 * (Candidates table is the reference). Header chrome uses `PageShellHeader`
 * / `mx-4`; the table itself has no outer inset.
 */
export function isEdgeToEdgeTablePath(pathname: string): boolean {
  const path = pathOnly(pathname)
  return (
    isExact(path, P.candidates) ||
    isExact(path, P.clientsDirectory) ||
    isExact(path, P.vacancies) ||
    isExact(path, P.leads) ||
    isExact(path, P.services) ||
    isExact(path, P.invoices) ||
    isExact(path, P.tasks) ||
    isExact(path, P.documents) ||
    isExact(path, P.pipeline) ||
    isPathOrChild(path, P.recruitmentInbox) ||
    isPathOrChild(path, P.sales)
  )
}

/**
 * Pages that own vertical scroll via `PageShell` / an inner table.
 * `main` stays `overflow-hidden` so we do not stack an outer scrollbar.
 * Independent of edge-to-edge vs inset padding.
 */
export function ownsCrmWorkspaceScroll(pathname: string): boolean {
  const path = pathOnly(pathname)
  if (isEdgeToEdgeTablePath(path)) return true
  return (
    isPathOrChild(path, P.vacancies) ||
    isPathOrChild(path, P.hr) ||
    isExact(path, P.overview) ||
    isExact(path, P.work) ||
    path.startsWith(`${P.work}/`) ||
    isExact(path, P.profile) ||
    isPathOrChild(path, P.myCompany) ||
    isExact(path, P.organization) ||
    isExact(path, P.automations) ||
    isExact(path, P.automationRules) ||
    isExact(path, P.automationLog) ||
    isExact(path, P.acquisitionActivity) ||
    path.startsWith(`${P.automationAreaPrefix}/`) ||
    isExact(path, P.calendar) ||
    isPathOrChild(path, P.setup) ||
    isPathOrChild(path, P.settings) ||
    isPathOrChild(path, P.recruitmentSearches) ||
    isPathOrChild(path, P.sales) ||
    isPathOrChild(path, P.inbox)
  )
}
