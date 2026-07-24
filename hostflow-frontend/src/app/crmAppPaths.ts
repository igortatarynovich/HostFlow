/**
 * Canonical SPA paths under **`/app/*`** (no activation rules).
 *
 * **Path tables** (`CRM_APP_PATHS`, `CRM_APP_DRILLDOWN_HREFS`) are generated from
 * **`shared/crm_app_paths.json`** — edit the manifest and run **`npm run codegen:crm-app-paths`**
 * (repo root) or **`make codegen-crm-app-paths`**. **`ACTIVATION_PATHS`** and feature modules
 * compose from here to avoid drift.
 */
import {
  CRM_APP_DRILLDOWN_HREFS as Q,
  CRM_APP_PATHS as P,
} from './crmAppPaths.generated'

export { CRM_APP_DRILLDOWN_HREFS, CRM_APP_PATHS } from './crmAppPaths.generated'

/** Invoice widget on dashboard: overdue queue vs plain invoices list. */
export function dashboardInvoiceOpsDrilldownPath(overdueUnpaidCount: number): string {
  return overdueUnpaidCount > 0 ? Q.invoicesOverdueUnpaid : P.invoices
}

/** Legacy / parallel inbox center: deep link under **`CRM_APP_PATHS.communicationsThreadsBase`**. */
export function communicationsThreadPath(threadId: string): string {
  return `${P.communicationsThreadsBase}/${encodeURIComponent(threadId)}`
}

export function settingsLeadFormDetailPath(formId: string): string {
  return `${P.settingsLeadForms}/${encodeURIComponent(formId)}`
}

export function marketingCampaignPath(campaignId: string): string {
  return `${P.marketing}/${encodeURIComponent(campaignId)}`
}

/** Connect Source wizard for an existing Campaign (Flight association). */
export function marketingConnectSourcePath(campaignId: string): string {
  return `${marketingCampaignPath(campaignId)}/sources/new`
}

export function settingsLeadFormBuilderPath(formId: string): string {
  return `${settingsLeadFormDetailPath(formId)}/builder`
}

export function recruitmentSearchPath(searchId: string): string {
  return `${P.recruitmentSearches}/${encodeURIComponent(searchId)}`
}

export function recruitmentSearchAcquisitionPath(searchId: string): string {
  return `${recruitmentSearchPath(searchId)}/acquisition`
}

export function recruitmentSearchAcquisitionActivitiesPath(searchId: string): string {
  return `${recruitmentSearchAcquisitionPath(searchId)}/activities`
}

export function recruitmentSearchAcquisitionNewPath(searchId: string): string {
  return `${recruitmentSearchPath(searchId)}/acquisition/new`
}

/** C-2: canonical create path — Marketing setup with vacancy target prefilled. */
export function marketingSetupWithVacancyTargetPath(
  vacancyId: string,
  opts?: { name?: string },
): string {
  const params = new URLSearchParams({
    target_type: 'vacancy',
    target_id: vacancyId,
    flow: 'candidates',
  })
  if (opts?.name?.trim()) params.set('name', opts.name.trim().slice(0, 160))
  return `${P.marketingNew}?${params.toString()}`
}

export function recruitmentSearchMetaSourcePath(searchId: string): string {
  return `${recruitmentSearchPath(searchId)}/acquisition/meta`
}

export function fleetOperatingLineSeasonalityPath(lineId: string): string {
  return `${P.fleetOperatingLinesSeasonality}/${encodeURIComponent(lineId)}`
}

/**
 * React Router `path` when routes are mounted under **`CRM_APP_PATHS.appShellPrefix`** (no leading slash).
 * Only path-only URLs — rejects `?` and `#`.
 */
export function crmAppRouteSegment(canonicalPath: string): string {
  const base = `${P.appShellPrefix}/`
  if (!canonicalPath.startsWith(base)) {
    throw new Error(`crmAppRouteSegment: expected path starting with ${base}, got ${canonicalPath}`)
  }
  const rest = canonicalPath.slice(base.length)
  if (rest.includes('?') || rest.includes('#')) {
    throw new Error(`crmAppRouteSegment: path must not include query or hash: ${canonicalPath}`)
  }
  return rest
}
