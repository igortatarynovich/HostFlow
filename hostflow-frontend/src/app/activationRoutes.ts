export const ACTIVATION_PATHS = {
  overview: '/app/overview',
  onboarding: '/app/onboarding/',
  clients: '/app/clients',
  vacancies: '/app/vacancies',
  leads: '/app/leads',
  reminders: '/app/reminders',
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
