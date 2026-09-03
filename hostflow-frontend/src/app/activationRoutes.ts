import { CRM_APP_PATHS } from './crmAppPaths'

/** Subset of CRM routes used by onboarding / activation / retention helpers (values from **`CRM_APP_PATHS`**). */
export const ACTIVATION_PATHS = {
  overview: CRM_APP_PATHS.overview,
  onboarding: CRM_APP_PATHS.onboarding,
  onboardingCompany: CRM_APP_PATHS.onboardingCompany,
  onboardingWizard: CRM_APP_PATHS.onboardingWizard,
  onboardingGettingStarted: CRM_APP_PATHS.onboardingGettingStarted,
  platformSetup: CRM_APP_PATHS.platformSetup,
  clients: CRM_APP_PATHS.clientsDirectory,
  candidates: CRM_APP_PATHS.candidates,
  vacancies: CRM_APP_PATHS.vacancies,
  leads: CRM_APP_PATHS.leads,
  services: CRM_APP_PATHS.services,
  messages: CRM_APP_PATHS.inboxMessagesScoped,
  invoices: CRM_APP_PATHS.invoices,
  reminders: CRM_APP_PATHS.tasks,
  billing: CRM_APP_PATHS.settingsBilling,
  legal: CRM_APP_PATHS.settingsLegal,
} as const

function pathWithoutTrailingSlash(pathname: string): string {
  const trimmed = pathname.replace(/\/+$/, '')
  return trimmed.length > 0 ? trimmed : '/'
}

/** Company-creation / wizard routes that must not bounce when onboarding is still required. */
export function isActivationOnboardingPath(pathname: string): boolean {
  const path = pathWithoutTrailingSlash(pathname)
  const onboardingRoot = pathWithoutTrailingSlash(ACTIVATION_PATHS.onboarding)
  return (
    path === ACTIVATION_PATHS.platformSetup ||
    path === onboardingRoot ||
    path.startsWith(`${onboardingRoot}/`)
  )
}

export const ACTIVATION_ALLOWED_PREFIXES = [
  ACTIVATION_PATHS.onboarding,
  ACTIVATION_PATHS.clients,
  ACTIVATION_PATHS.vacancies,
  ACTIVATION_PATHS.leads,
  ACTIVATION_PATHS.reminders,
  ACTIVATION_PATHS.billing,
  ACTIVATION_PATHS.legal,
] as const

export type ActivationBusinessType = 'agency' | 'employer' | 'services'

export type ActivationStatusLike = {
  business_type: ActivationBusinessType
  onboarding_required: boolean
  activation_required: boolean
  demo_seeded?: boolean
  steps: {
    company_created: boolean
    first_lead_created?: boolean
    first_client_created: boolean
    first_vacancy_created: boolean
    first_campaign_created?: boolean
    first_service_order_created: boolean
    next_action_created: boolean
  }
}

export function getBusinessHomePath(businessType: ActivationBusinessType): string {
  if (businessType === 'services') return ACTIVATION_PATHS.clients
  if (businessType === 'employer') return ACTIVATION_PATHS.vacancies
  return ACTIVATION_PATHS.candidates
}

export function getBusinessNextActionPath(businessType: ActivationBusinessType): string {
  if (businessType === 'services') return ACTIVATION_PATHS.leads
  if (businessType === 'employer') return ACTIVATION_PATHS.vacancies
  return ACTIVATION_PATHS.clients
}

export function getActivationSetupTarget(status: ActivationStatusLike | null | undefined): string {
  if (!status) return ACTIVATION_PATHS.overview
  if (status.onboarding_required) return ACTIVATION_PATHS.platformSetup
  if (status.activation_required) {
    // New tenants with demo pipeline land on overview; legacy tenants keep guided checklist.
    if (status.demo_seeded) return ACTIVATION_PATHS.overview
    return ACTIVATION_PATHS.onboardingGettingStarted
  }
  return getBusinessHomePath(status.business_type)
}

export function isBusinessPrimaryStepDone(status: ActivationStatusLike | null | undefined): boolean {
  if (!status) return false
  if (status.business_type === 'services') {
    return Boolean(status.steps.first_client_created || status.steps.first_lead_created)
  }
  if (status.business_type === 'employer') return Boolean(status.steps.first_vacancy_created)
  return Boolean(status.steps.first_client_created)
}

export function getRetentionNextPath(status: ActivationStatusLike | null | undefined): string {
  if (!status) return ACTIVATION_PATHS.overview
  if (!status.steps.company_created) return ACTIVATION_PATHS.platformSetup
  if (!isBusinessPrimaryStepDone(status)) return getBusinessNextActionPath(status.business_type)
  if (!status.steps.next_action_created) return ACTIVATION_PATHS.reminders
  return ACTIVATION_PATHS.billing
}

export function getRetentionStepKey(status: ActivationStatusLike | null | undefined): 'client' | 'vacancy' | 'service_order' | 'type_step' {
  if (!status) return 'type_step'
  if (status.business_type === 'services') return 'client'
  if (status.business_type === 'employer') return 'vacancy'
  return 'client'
}

/**
 * First hiring setup entry: client (name) → vacancy → campaign.
 * Employers skip the client company; services start from the client directory.
 */
export function getHiringSetupEntryPath(status: ActivationStatusLike | null | undefined): string {
  const businessType = status?.business_type ?? 'agency'
  const steps = status?.steps
  if (businessType === 'services') return ACTIVATION_PATHS.clients
  if (businessType !== 'employer' && !steps?.first_client_created && !steps?.first_vacancy_created) {
    return CRM_APP_PATHS.setupClient
  }
  if (!steps?.first_vacancy_created) return CRM_APP_PATHS.setupVacancy
  if (!steps?.first_campaign_created) return CRM_APP_PATHS.marketingNew
  return CRM_APP_PATHS.marketing
}

/** Where “create first vacancy” should send the user so the vacancy already has a client (or own company). */
export function getFirstVacancySetupPath(status: ActivationStatusLike | null | undefined): string {
  const businessType = status?.business_type ?? 'agency'
  if (businessType === 'employer') return CRM_APP_PATHS.setupVacancy
  if (status?.steps?.first_client_created) return CRM_APP_PATHS.setupVacancy
  return CRM_APP_PATHS.setupClient
}
