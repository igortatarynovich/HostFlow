export type SearchRole = 'driver' | 'warehouse' | 'office' | 'other'

export type LaunchSearchRoleDefaults = {
  entityProfileCode: string
  candidateProfileCode: string
  funnelName: string
  maxIntakeFields: number
}

export const LAUNCH_SEARCH_ROLE_DEFAULTS: Record<SearchRole, LaunchSearchRoleDefaults> = {
  driver: {
    entityProfileCode: 'recruitment.candidate.driver_ce',
    candidateProfileCode: 'driver_ce_default',
    funnelName: 'Driver CE (default)',
    maxIntakeFields: 14,
  },
  warehouse: {
    entityProfileCode: 'recruitment.candidate.warehouse_worker',
    candidateProfileCode: 'warehouse_worker_default',
    funnelName: 'Warehouse (default)',
    maxIntakeFields: 10,
  },
  office: {
    entityProfileCode: 'recruitment.candidate.office_worker',
    candidateProfileCode: 'office_worker_default',
    funnelName: 'Office (default)',
    maxIntakeFields: 10,
  },
  other: {
    entityProfileCode: 'recruitment.candidate.general',
    candidateProfileCode: 'general_candidate_default',
    funnelName: 'General hiring (default)',
    maxIntakeFields: 10,
  },
}

export function launchSearchRoleDefaults(role: SearchRole): LaunchSearchRoleDefaults {
  return LAUNCH_SEARCH_ROLE_DEFAULTS[role] ?? LAUNCH_SEARCH_ROLE_DEFAULTS.driver
}
