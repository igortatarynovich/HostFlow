import { test, expect, type Page, type BrowserContext } from '@playwright/test'
import {
  bootstrapEmployerViaApi,
  dismissCookieBanner,
  uniqueM1Email,
} from './helpers/m1BrowserAuth'

/**
 * M1 Money Path — «Создать подбор» → ссылка → public intake → отклик на Search Home.
 *
 * Run:
 *   PLAYWRIGHT_BASE_URL=https://hostflow.cc MILESTONE_1_E2E=1 npm run e2e:m1-money-path
 */

const uiBaseUrl = (process.env.PLAYWRIGHT_BASE_URL || '').trim()
const milestoneEnabled = process.env.MILESTONE_1_E2E === '1'

test.skip(
  !uiBaseUrl || !milestoneEnabled,
  'Set PLAYWRIGHT_BASE_URL and MILESTONE_1_E2E=1 to run M1 money path E2E',
)

test.use({ ignoreHTTPSErrors: true })

async function completePlatformSetup(page: Page, companyName: string) {
  await expect(page.getByTestId('m1-platform-setup')).toBeVisible({ timeout: 60_000 })
  await page.getByTestId('m1-platform-identity-transport_company').click()
  await page.getByRole('button', { name: /продолжить|continue/i }).click()
  await page.getByTestId('m1-platform-module-recruitment').click()
  await page.getByRole('button', { name: /продолжить|continue/i }).click()
  await expect(page.getByTestId('m1-company-setup-step')).toBeVisible()
  await page.getByTestId('m1-company-name').fill(companyName)
  await page.getByTestId('m1-company-industry-select').selectOption('transport_logistics')
  await page.getByTestId('m1-company-country').selectOption('PL')
  await page.locator('label').filter({ has: page.getByTestId('m1-company-team-size-2_10') }).click()
  await page.getByTestId('m1-company-save').click()
  await page.waitForURL((u) => u.pathname.includes('/app/launchpad'), {
    timeout: 60_000,
    waitUntil: 'commit',
  })
}

async function completeCreateSearchWizard(page: Page, clientName?: string) {
  await expect(page.getByTestId('m1-launchpad')).toBeVisible({ timeout: 30_000 })
  await page.goto('/app/recruitment/searches/new', { waitUntil: 'domcontentloaded' })
  await expect(page.getByTestId('m1-create-search-role-driver')).toBeVisible({ timeout: 30_000 })

  await page.getByTestId('m1-create-search-role-driver').click()
  await page.getByTestId('m1-create-search-continue').click()

  if (clientName) {
    await page.getByTestId('m1-create-search-for-client').click()
    await page.getByTestId('m1-create-search-client-name').fill(clientName)
  } else {
    await page.getByTestId('m1-create-search-for-own').click()
  }

  await page.getByTestId('m1-create-search-submit').click()
  await expect(page.getByTestId('m1-search-ready')).toBeVisible({ timeout: 120_000 })
}

async function readPublicUrlFromSession(page: Page): Promise<string | null> {
  return page.evaluate(() => {
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i)
      if (!key?.startsWith('hostflow:launch-search:')) continue
      try {
        const raw = sessionStorage.getItem(key)
        if (!raw) continue
        const parsed = JSON.parse(raw) as { publicUrl?: string }
        if (parsed.publicUrl) return parsed.publicUrl
      } catch {
        continue
      }
    }
    return null
  })
}

async function submitMinimalPublicIntake(context: BrowserContext, publicUrl: string) {
  const page = await context.newPage()
  await page.goto(publicUrl)
  await dismissCookieBanner(page)
  await expect(page.locator('body')).toBeVisible({ timeout: 30_000 })

  const phone = page.locator('input[type="tel"], input[name="phone"], input[autocomplete="tel"]').first()
  const email = page.locator('input[type="email"], input[name="email"]').first()

  if (await phone.isVisible().catch(() => false)) {
    await phone.fill('512345678')
  }
  if (await email.isVisible().catch(() => false)) {
    await email.fill(`intake-${Date.now()}@example.com`)
  }

  const submit = page
    .getByRole('button', { name: /отправ|submit|continue|далее|start|начать/i })
    .first()
  if (await submit.isVisible().catch(() => false)) {
    await submit.click()
  }

  await page.waitForTimeout(3000)
  await page.close()
}

test.describe('M1 Money Path', () => {
  test.setTimeout(240_000)

  test('employer creates search, gets link, public intake loads', async ({ page, context }) => {
    const email = uniqueM1Email('m1-money')
    await bootstrapEmployerViaApi(page, { name: `M1 Money ${Date.now()}`, email })
    await completePlatformSetup(page, `M1 Transport ${Date.now()} Sp. z o.o.`)

    await completeCreateSearchWizard(page)

    await page.getByTestId('m1-search-copy-link').click()

    const publicUrl = await readPublicUrlFromSession(page)
    expect(publicUrl).toBeTruthy()
    expect(publicUrl).toMatch(/\/public\/intake\?/)

    await submitMinimalPublicIntake(context, publicUrl!)

    await page.getByTestId('m1-search-open').click()
    await expect(page.getByTestId('m1-search-home')).toBeVisible({ timeout: 30_000 })
    await expect(page.getByText(/активен/i)).toBeVisible()
  })
})
