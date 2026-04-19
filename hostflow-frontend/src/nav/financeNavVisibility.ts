import type { TeamOverviewResponse } from '../api/types'

export type NavPlanTier = 'starter' | 'team' | 'pro' | null

export type BusinessTypeNav = 'agency' | 'employer' | 'services'

export function resolveNavPlanFromTeamOverview(
  canLoadTeamOverview: boolean,
  teamOverview: TeamOverviewResponse | null,
): NavPlanTier {
  if (!canLoadTeamOverview || teamOverview == null) return null
  const lic = teamOverview.license
  if (!lic) return null
  const p = String(lic.plan || '').trim().toLowerCase()
  if (p === 'team') return 'team'
  if (p === 'pro') return 'pro'
  return 'starter'
}

/**
 * Separate **Finance** block in nav when plan is team/pro, or workspace is services (incl. starter).
 * Starter agency/employer with known license: single **Work** list. Unknown plan: consolidated (no split).
 */
export function shouldShowFinanceNavSection(params: {
  isClientTenant: boolean
  businessType: BusinessTypeNav
  resolvedNavPlan: NavPlanTier
}): boolean {
  const { isClientTenant, businessType, resolvedNavPlan } = params
  if (isClientTenant) return false
  if (businessType === 'services') return true
  if (resolvedNavPlan === null) return false
  return resolvedNavPlan === 'team' || resolvedNavPlan === 'pro'
}
