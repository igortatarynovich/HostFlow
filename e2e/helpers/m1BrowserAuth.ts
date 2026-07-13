import { expect, type Page } from '@playwright/test'

export const M1_E2E_PASSWORD = 'Milestone1TestPass!'
const E2E_HEADER = { 'X-HostFlow-E2E': 'm1-money-path' }

export function uniqueM1Email(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`
}

export async function dismissCookieBanner(page: Page) {
  const accept = page.getByRole('button', { name: /accept|принимаю|akceptuj/i })
  if (await accept.isVisible().catch(() => false)) {
    await accept.click()
  }
}

type RegisterResponse = {
  tenant?: { id?: string; trial_ends_at?: string | null }
  meta?: { welcome_email_sent?: boolean }
}

type LoginResponse = {
  access_token: string
  tenant_id?: string
  user?: { tenant_id?: string }
}

export async function bootstrapEmployerViaApi(
  page: Page,
  opts: { name: string; email: string; password?: string },
) {
  const password = opts.password ?? M1_E2E_PASSWORD
  const register = await page.request.post('/api/v1/auth/register', {
    headers: E2E_HEADER,
    data: {
      email: opts.email,
      password,
      full_name: opts.name,
      accept_terms: true,
      accept_privacy: true,
    },
  })
  expect(register.ok(), `register failed: ${register.status()} ${await register.text()}`).toBeTruthy()
  const registration = (await register.json()) as RegisterResponse

  const login = await page.request.post('/api/v1/auth/login', {
    headers: E2E_HEADER,
    data: { email: opts.email, password },
  })
  expect(login.ok(), `login failed: ${login.status()} ${await login.text()}`).toBeTruthy()
  const session = (await login.json()) as LoginResponse

  const tenantId =
    session.tenant_id || session.user?.tenant_id || registration.tenant?.id || ''
  expect(tenantId, 'tenant id missing after bootstrap login').toBeTruthy()

  const signupContext = {
    signup: 'success',
    welcome_email: registration.meta?.welcome_email_sent === false ? 'not_sent' : 'sent',
    ...(registration.tenant?.trial_ends_at
      ? { trial_ends_at: registration.tenant.trial_ends_at }
      : {}),
  }

  const params = new URLSearchParams()
  params.set('signup', signupContext.signup)
  params.set('welcome_email', signupContext.welcome_email)
  if (signupContext.trial_ends_at) params.set('trial_ends_at', signupContext.trial_ends_at)

  await page.addInitScript(
    ({ token, tenant, context }) => {
      localStorage.setItem('access_token', token)
      localStorage.setItem('token', token)
      localStorage.setItem('tenant_id', tenant)
      localStorage.setItem('X-Tenant-Id', tenant)
      sessionStorage.setItem('hf:signup-success-context', JSON.stringify(context))
    },
    {
      token: session.access_token,
      tenant: tenantId,
      context: signupContext,
    },
  )

  await page.goto(`/app/platform/setup?${params.toString()}`, { waitUntil: 'domcontentloaded' })
  await dismissCookieBanner(page)
  await expect(page.getByTestId('m1-platform-setup')).toBeVisible({ timeout: 60_000 })
}
