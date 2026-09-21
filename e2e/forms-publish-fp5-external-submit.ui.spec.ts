import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import { API_BASE, BOOTSTRAP_USERS, DEFAULT_TENANT_ID, authHeaders, login } from './helpers/hostflowApi'

/**
 * FP-5 External Intake Acceptance: operator publishes a live URL, a stranger
 * without auth submits the published form, the resulting entity is visible
 * on the HostFlow candidates surface.
 *
 * Requires PLAYWRIGHT_BASE_URL (CRM origin) and a running API on
 * PLAYWRIGHT_API_BASE_URL. Seed: `backend/scripts/seed_e2e_bootstrap.py`.
 */
const uiBaseUrl = (process.env.PLAYWRIGHT_BASE_URL || '').trim()
test.skip(!uiBaseUrl, 'Set PLAYWRIGHT_BASE_URL to a running CRM (e.g. http://127.0.0.1:5173)')

const ADMIN_EMAIL = (process.env.PLAYWRIGHT_MANAGER_EMAIL || BOOTSTRAP_USERS.manager.email).trim()
const ADMIN_PASSWORD = (process.env.PLAYWRIGHT_MANAGER_PASSWORD || BOOTSTRAP_USERS.manager.password).trim()
const PROFILE_CODE = 'recruitment.candidate.warehouse_worker'

async function acceptCookiesIfPresent(page: Page) {
  const accept = page.getByTestId('public-cookie-accept')
  if (await accept.isVisible().catch(() => false)) {
    await accept.click()
  }
}

async function loginOperator(page: Page) {
  await page.goto('/login')
  await acceptCookiesIfPresent(page)
  await page.locator('input[type="email"]').fill(ADMIN_EMAIL)
  await page.locator('input[type="password"]').fill(ADMIN_PASSWORD)
  await page.locator('form button').first().click()
  await page.waitForURL((u) => !u.pathname.includes('/login'), {
    timeout: 60_000,
    waitUntil: 'commit',
  })
}

async function createUnpublishedForm(request: APIRequestContext, token: string) {
  const slug = `fp5-${Date.now().toString(36)}`
  const headers = authHeaders(token)
  const created = await request.post(`${API_BASE}/settings/intake-forms`, {
    headers,
    data: {
      title: 'FP-5 External Submit',
      public_slug: slug,
      entity_profile_code: PROFILE_CODE,
      fields: [
        { qualified_code: 'recruitment.candidate.first_name', intake_level: 'required' },
        { qualified_code: 'recruitment.candidate.last_name', intake_level: 'required' },
      ],
    },
  })
  expect(created.ok(), await created.text()).toBeTruthy()
  const body = (await created.json()) as { form?: { id?: string } }
  const formId = String(body.form?.id || '')
  expect(formId).toBeTruthy()
  return { formId, slug }
}

test.describe('FP-5 external intake acceptance', () => {
  test('operator publish → stranger submit → candidate visible', async ({ browser, page, request }) => {
    const token = await login(request, ADMIN_EMAIL, ADMIN_PASSWORD)
    const { formId, slug } = await createUnpublishedForm(request, token)

    await loginOperator(page)
    await page.goto(`/app/settings/lead-forms/${formId}/builder`, { waitUntil: 'domcontentloaded' })
    await expect(page.getByTestId('form-operator-state')).toBeVisible({ timeout: 30_000 })
    await page.getByTestId('form-publish').click()
    await expect(page.getByTestId('form-operator-state')).toContainText(/live|эфире|na żywo/i, { timeout: 30_000 })
    const publicUrl = page.getByTestId('form-public-url')
    await expect(publicUrl).toBeVisible()
    const href = await publicUrl.getAttribute('href')
    expect(href || '').toContain(`lead_form_slug=${slug}`)

    const email = `fp5-stranger-${Date.now()}@example.com`
    const stranger = await browser.newContext({ storageState: { cookies: [], origins: [] } })
    const strangerPage = await stranger.newPage()
    await strangerPage.goto(`/public/intake?lead_form_slug=${encodeURIComponent(slug)}`)
    await acceptCookiesIfPresent(strangerPage)
    await strangerPage.getByTestId('public-intake-email').fill(email)
    await strangerPage.getByTestId('public-intake-start-submit').click()
    await strangerPage.getByTestId('public-intake-open-apply').click()
    await strangerPage.getByTestId('public-intake-lang-en').click()
    await expect(strangerPage.getByTestId('presentation-field-recruitment.candidate.first_name')).toBeVisible({
      timeout: 30_000,
    })
    await strangerPage.getByTestId('presentation-field-recruitment.candidate.first_name').fill('Jan')
    await strangerPage.getByTestId('presentation-field-recruitment.candidate.last_name').fill('Kowalski')
    await strangerPage.locator('#presentation-consent-general').check()
    await strangerPage.locator('#presentation-consent-share').check()
    await strangerPage.locator('#presentation-consent-terms').check()
    await strangerPage.getByTestId('public-intake-submit').click()
    await expect(strangerPage.getByText(/dziękujemy|thank you|otrzymaliśmy/i)).toBeVisible({ timeout: 30_000 })
    await stranger.close()

    const headers = authHeaders(token)
    let candidateId = ''
    await expect
      .poll(
        async () => {
          const leads = await request.get(`${API_BASE}/leads?q=${encodeURIComponent(email)}`, { headers })
          expect(leads.ok(), await leads.text()).toBeTruthy()
          const body = (await leads.json()) as { items?: Array<{ candidate_id?: string | null }> }
          candidateId = String(body.items?.find((row) => row.candidate_id)?.candidate_id || '')
          return candidateId
        },
        { timeout: 15_000 },
      )
      .toBeTruthy()
    const workspace = await request.get(`${API_BASE}/candidates/${candidateId}`, { headers })
    expect(workspace.ok(), await workspace.text()).toBeTruthy()
    const shown = (await workspace.json()) as { email?: string }
    expect(String(shown.email || '').toLowerCase()).toBe(email.toLowerCase())

    await page.goto(`/app/candidates/${candidateId}`, { waitUntil: 'domcontentloaded' })
    await expect(page.getByText(email)).toBeVisible({ timeout: 30_000 })
    expect(DEFAULT_TENANT_ID).toMatch(/^[0-9a-f-]{36}$/i)
  })
})
