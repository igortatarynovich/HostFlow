export const SIGNUP_SUCCESS_CONTEXT_KEY = 'hf:signup-success-context'

export type SignupSuccessContext = {
  signup: 'success'
  welcome_email: 'sent' | 'not_sent'
  trial_ends_at?: string
}

export function buildSignupSuccessContext(
  welcomeEmailSent: boolean,
  trialEndsAt?: string | null,
): SignupSuccessContext {
  return {
    signup: 'success',
    welcome_email: welcomeEmailSent ? 'sent' : 'not_sent',
    ...(trialEndsAt ? { trial_ends_at: trialEndsAt } : {}),
  }
}

export function signupContextToSearchParams(context: SignupSuccessContext): URLSearchParams {
  const params = new URLSearchParams()
  params.set('signup', context.signup)
  params.set('welcome_email', context.welcome_email)
  if (context.trial_ends_at) params.set('trial_ends_at', context.trial_ends_at)
  return params
}

export function readSignupSuccessContextFromSearch(searchParams: URLSearchParams): SignupSuccessContext | null {
  const signup = (searchParams.get('signup') || '').trim().toLowerCase()
  if (signup !== 'success') return null
  const welcome = (searchParams.get('welcome_email') || '').trim().toLowerCase()
  const welcome_email = welcome === 'not_sent' ? 'not_sent' : 'sent'
  const trial_ends_at = (searchParams.get('trial_ends_at') || '').trim()
  return {
    signup: 'success',
    welcome_email,
    ...(trial_ends_at ? { trial_ends_at } : {}),
  }
}

export function readSignupSuccessContextFromSessionStorage(): SignupSuccessContext | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.sessionStorage.getItem(SIGNUP_SUCCESS_CONTEXT_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<SignupSuccessContext> | null
    const signup = String(parsed?.signup || '').trim().toLowerCase()
    if (signup !== 'success') return null
    const welcome = String(parsed?.welcome_email || '').trim().toLowerCase()
    const welcome_email = welcome === 'not_sent' ? 'not_sent' : 'sent'
    const trial_ends_at = String(parsed?.trial_ends_at || '').trim()
    return {
      signup: 'success',
      welcome_email,
      ...(trial_ends_at ? { trial_ends_at } : {}),
    }
  } catch {
    return null
  }
}
