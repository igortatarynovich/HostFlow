export const ACTIVATION_PATHS = {
  overview: '/app/overview',
  onboarding: '/app/onboarding/',
  onboardingCompany: '/app/onboarding/company',
  onboardingGettingStarted: '/app/onboarding/getting-started',
  clients: '/app/clients',
  candidates: '/app/candidates',
  vacancies: '/app/vacancies',
  leads: '/app/leads',
  services: '/app/services',
  messages: '/app/messages',
  invoices: '/app/invoices',
  reminders: '/app/tasks',
  billing: '/app/settings/billing',
  legal: '/app/settings/legal',
} as const

export const ACTIVATION_ALLOWED_PREFIXES = [
  ACTIVATION_PATHS.onboarding,
  ACTIVATION_PATHS.clients,
  ACTIVATION_PATHS.vacancies,
  ACTIVATION_PATHS.leads,
  ACTIVATION_PATHS.reminders,
  ACTIVATION_PATHS.billing,
  ACTIVATION_PATHS.legal,
] as const

export function isActivationRoute(pathname: string): boolean {
  return ACTIVATION_ALLOWED_PREFIXES.some((prefix) => pathname.startsWith(prefix))
}

export type ActivationBusinessType = 'agency' | 'employer' | 'services'

export type ActivationStatusLike = {
  business_type: ActivationBusinessType
  onboarding_required: boolean
  activation_required: boolean
  steps: {
    company_created: boolean
    first_lead_created?: boolean
    first_client_created: boolean
    first_vacancy_created: boolean
    first_service_order_created: boolean
    next_action_created: boolean
  }
}

export function getBusinessHomePath(businessType: ActivationBusinessType): string {
  if (businessType === 'services') return ACTIVATION_PATHS.clients
  if (businessType === 'employer') return ACTIVATION_PATHS.vacancies
  return ACTIVATION_PATHS.candidates
}

export function getBusinessPrimaryEntityPath(businessType: ActivationBusinessType): string {
  if (businessType === 'services') return ACTIVATION_PATHS.clients
  if (businessType === 'employer') return ACTIVATION_PATHS.vacancies
  return ACTIVATION_PATHS.clients
}

export function getBusinessNextActionPath(businessType: ActivationBusinessType): string {
  if (businessType === 'services') return ACTIVATION_PATHS.leads
  if (businessType === 'employer') return ACTIVATION_PATHS.vacancies
  return ACTIVATION_PATHS.clients
}

export function getActivationSetupTarget(status: ActivationStatusLike | null | undefined): string {
  if (!status) return ACTIVATION_PATHS.overview
  if (status.onboarding_required) return ACTIVATION_PATHS.onboardingCompany
  if (status.activation_required) return ACTIVATION_PATHS.onboardingGettingStarted
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
  if (!status.steps.company_created) return ACTIVATION_PATHS.onboardingCompany
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
