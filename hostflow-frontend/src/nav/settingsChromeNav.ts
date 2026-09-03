import { CRM_APP_PATHS } from '../app/crmAppPaths'

/** Tabs in `SettingsChrome` — aligned with `SettingsLandingPage` sections (ADR-023). */
export type SettingsChromeTabKey =
  | 'overview'
  | 'workspace'
  | 'recruitment_setup'
  | 'sales_setup'
  | 'team'
  | 'automations'
  | 'integrations'
  | 'billing'
  | 'security'
  | 'personal'

/** Longest-prefix wins: path must start with `prefix` (use full path constants). */
const SETTINGS_PATH_PREFIX_TAB: { prefix: string; tab: SettingsChromeTabKey }[] = [
  { prefix: CRM_APP_PATHS.settingsBilling, tab: 'billing' },
  { prefix: CRM_APP_PATHS.settingsAudit, tab: 'security' },
  { prefix: CRM_APP_PATHS.settingsUsers, tab: 'team' },
  { prefix: CRM_APP_PATHS.settingsTeam, tab: 'team' },
  { prefix: CRM_APP_PATHS.settingsCompanyAccess, tab: 'team' },
  { prefix: CRM_APP_PATHS.settingsTenants, tab: 'workspace' },
  { prefix: CRM_APP_PATHS.settingsLegal, tab: 'workspace' },
  { prefix: CRM_APP_PATHS.settingsTenantLinks, tab: 'workspace' },
  { prefix: CRM_APP_PATHS.settingsTtvReport, tab: 'recruitment_setup' },
  { prefix: CRM_APP_PATHS.settingsCustomFields, tab: 'recruitment_setup' },
  { prefix: CRM_APP_PATHS.settingsCandidateProfiles, tab: 'recruitment_setup' },
  { prefix: CRM_APP_PATHS.settingsDocs, tab: 'recruitment_setup' },
  { prefix: CRM_APP_PATHS.settingsMergeTemplates, tab: 'recruitment_setup' },
  { prefix: CRM_APP_PATHS.settingsRiskIntel, tab: 'recruitment_setup' },
  { prefix: CRM_APP_PATHS.settingsHiringPipelineGates, tab: 'recruitment_setup' },
  { prefix: CRM_APP_PATHS.settingsTransferPolicy, tab: 'recruitment_setup' },
  { prefix: CRM_APP_PATHS.settingsRequirementPolicy, tab: 'recruitment_setup' },
  { prefix: CRM_APP_PATHS.settingsFunnels, tab: 'recruitment_setup' },
  { prefix: CRM_APP_PATHS.settingsMessageTemplates, tab: 'sales_setup' },
  { prefix: CRM_APP_PATHS.settingsLeadForms, tab: 'sales_setup' },
  { prefix: CRM_APP_PATHS.settingsRuleset, tab: 'automations' },
  { prefix: CRM_APP_PATHS.settingsCommunicationsMessengers, tab: 'integrations' },
  { prefix: CRM_APP_PATHS.settingsCommunicationsQueue, tab: 'automations' },
  { prefix: CRM_APP_PATHS.settingsCommunicationsSla, tab: 'automations' },
  { prefix: CRM_APP_PATHS.settingsCommunicationsTemplates, tab: 'integrations' },
  { prefix: CRM_APP_PATHS.settingsCommunicationsAutomation, tab: 'automations' },
  { prefix: CRM_APP_PATHS.settingsCommunicationsCampaigns, tab: 'automations' },
  { prefix: CRM_APP_PATHS.settingsCommunications, tab: 'integrations' },
  { prefix: CRM_APP_PATHS.settingsIntegrationsMeta, tab: 'integrations' },
  { prefix: CRM_APP_PATHS.settingsIntegrationsGoogle, tab: 'integrations' },
  { prefix: CRM_APP_PATHS.settingsIntegrationsWebhook, tab: 'integrations' },
  { prefix: CRM_APP_PATHS.settingsIntegrations, tab: 'integrations' },
  { prefix: CRM_APP_PATHS.settingsEmail, tab: 'integrations' },
]

const sortedPrefixes = [...SETTINGS_PATH_PREFIX_TAB].sort((a, b) => b.prefix.length - a.prefix.length)

/**
 * Which Settings chrome tab should appear active for this location.
 * Only meaningful under `/app/settings`; profile/billing still map for consistency if reused.
 */
export function settingsChromeActiveTab(pathname: string, search: string): SettingsChromeTabKey {
  if (pathname === CRM_APP_PATHS.profile) return 'personal'
  if (pathname === CRM_APP_PATHS.settingsBilling || pathname.startsWith(`${CRM_APP_PATHS.settingsBilling}/`)) {
    return 'billing'
  }

  if (pathname === CRM_APP_PATHS.settings || pathname === `${CRM_APP_PATHS.settings}/`) {
    return 'overview'
  }

  if (pathname.startsWith(`${CRM_APP_PATHS.settings}/`)) {
    for (const { prefix, tab } of sortedPrefixes) {
      if (pathname === prefix || pathname.startsWith(`${prefix}/`)) return tab
    }
  }

  void search
  return 'overview'
}

export function settingsChromeTabHref(tab: SettingsChromeTabKey): string {
  switch (tab) {
    case 'overview':
      return CRM_APP_PATHS.settings
    case 'workspace':
      return CRM_APP_PATHS.myCompany
    case 'recruitment_setup':
      return CRM_APP_PATHS.settingsFunnels
    case 'sales_setup':
      return CRM_APP_PATHS.settingsLeadForms
    case 'team':
      return CRM_APP_PATHS.settingsUsers
    case 'automations':
      return CRM_APP_PATHS.settingsRuleset
    case 'integrations':
      return CRM_APP_PATHS.settingsIntegrations
    case 'billing':
      return CRM_APP_PATHS.settingsBilling
    case 'security':
      return CRM_APP_PATHS.settingsAudit
    case 'personal':
      return CRM_APP_PATHS.profile
    default:
      return CRM_APP_PATHS.settings
  }
}

export function isSettingsChromeTabActive(
  tab: SettingsChromeTabKey,
  pathname: string,
  search: string,
): boolean {
  return settingsChromeActiveTab(pathname, search) === tab
}
