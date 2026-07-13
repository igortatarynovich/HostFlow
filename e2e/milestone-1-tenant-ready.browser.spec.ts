import { test, expect, type Page } from '@playwright/test'

/**
 * Milestone 1 — Platform + Launchpad + Recruitment setup (browser acceptance).
 *
 * Slices:
 * - M1-01 (default): signup → platform setup → launchpad
 * - full: agency + employer Human Gate journeys (manual intake → Ready → workspace)
 */

const uiBaseUrl = (process.env.PLAYWRIGHT_BASE_URL || '').trim()
const milestoneEnabled = process.env.MILESTONE_1_E2E === '1'
const slice = (process.env.MILESTONE_1_SLICE || 'm1-01').trim().toLowerCase()

test.skip(
  !uiBaseUrl || !milestoneEnabled,
  'Set PLAYWRIGHT_BASE_URL and MILESTONE_1_E2E=1 to run Milestone 1 browser acceptance',
)

const PASSWORD = 'Milestone1TestPass!'

type PlatformIdentityId = 'recruitment_agency' | 'transport_company'

function uniqueSignupEmail(prefix: string): string {
  return `${prefix}-${Date.now()}@milestone-e2e.local`
}

async function fillSignupForm(page: Page, opts: { name: string; email: string }) {
  await page.goto('/signup')
  await page.getByTestId('m1-signup-name').fill(opts.name)
  await page.getByTestId('m1-signup-email').fill(opts.email)
  await page.getByTestId('m1-signup-password').fill(PASSWORD)
  await page.getByTestId('m1-signup-password-confirm').fill(PASSWORD)
  await page.getByTestId('m1-signup-accept-terms').check()
  await page.getByTestId('m1-signup-accept-privacy').check()
  await page.getByTestId('m1-signup-submit').click()
}

async function completePlatformSetup(
  page: Page,
  opts: { companyName: string; identityId: PlatformIdentityId },
) {
  await expect(page.getByTestId('m1-platform-setup')).toBeVisible({ timeout: 60_000 })
  await page.getByTestId(`m1-platform-identity-${opts.identityId}`).click()
  await page.getByRole('button', { name: /продолжить|continue/i }).click()
  await page.getByTestId('m1-platform-module-recruitment').click()
  await page.getByRole('button', { name: /продолжить|continue/i }).click()
  await expect(page.getByTestId('m1-company-setup-step')).toBeVisible()
  await page.getByTestId('m1-company-name').fill(opts.companyName)
  await page.getByTestId('m1-company-industry-select').selectOption('transport_logistics')
  await page.getByTestId('m1-company-team-size-2_10').click()
  await page.getByTestId('m1-company-country').selectOption('PL')
  await page.getByTestId('m1-company-save').click()
}

async function completeSetupFirstClient(page: Page, clientName: string) {
  await expect(page.getByTestId('m1-setup-client-flow')).toBeVisible({ timeout: 60_000 })
  await page.getByTestId('m1-setup-hiring-client').click()
  await page.getByTestId('m1-setup-client-continue').click()
  await page.getByTestId('m1-client-name').fill(clientName)
  await page.getByTestId('m1-client-save').click()
  await page.waitForURL((u) => u.pathname.includes('/app/setup/vacancy'), { timeout: 60_000 })
}

async function completeSetupFirstVacancy(page: Page, title: string) {
  await expect(page.getByTestId('m1-setup-vacancy-flow')).toBeVisible({ timeout: 60_000 })
  await page.getByTestId('m1-vacancy-title').fill(title)
  await page.getByTestId('m1-vacancy-save').click()
  await page.waitForURL((u) => u.pathname.includes('/app/setup/process'), { timeout: 60_000 })
}

async function completeSetupProcessDefaults(page: Page) {
  await expect(page.getByTestId('m1-setup-process-flow')).toBeVisible({ timeout: 60_000 })
  await page.getByTestId('m1-funnel-save').click()
  await page.waitForURL((u) => u.pathname.includes('/app/setup/intake'), {
    timeout: 60_000,
  })
}

async function completeSetupCandidateIntakeManual(page: Page) {
  await expect(page.getByTestId('m1-setup-intake-flow')).toBeVisible({ timeout: 60_000 })
  await page.getByTestId('m1-setup-intake-manual').click()
  await page.waitForURL((u) => u.pathname.includes('/app/launchpad'), {
    timeout: 60_000,
  })
}

async function assertRecruitmentReadyOnLaunchpad(page: Page) {
  await expect(page.getByTestId('m1-launchpad-module-recruitment')).toHaveAttribute(
    'data-module-status',
    'ready',
    { timeout: 60_000 },
  )
}

async function assertSetupHubReady(page: Page, opts: { expectClientGate: boolean }) {
  await expect(page.getByTestId('m1-readiness-ready')).toBeVisible({ timeout: 60_000 })
  if (opts.expectClientGate) {
    await expect(page.getByTestId('m1-gate-g2')).toHaveAttribute('data-status', 'pass')
  } else {
    await expect(page.getByTestId('m1-gate-g2')).toHaveAttribute('data-status', 'na')
  }
  await expect(page.getByTestId('m1-gate-g3')).toHaveAttribute('data-status', 'pass')
  await expect(page.getByTestId('m1-gate-g4')).toHaveAttribute('data-status', 'pass')
  await expect(page.getByTestId('m1-gate-g5')).toHaveAttribute('data-status', 'pass')
  await expect(page.getByTestId('m1-gate-g6')).toHaveAttribute('data-status', 'pass')
  await expect(page.getByTestId('m1-gate-g7')).toHaveAttribute('data-status', 'pass')
  await expect(page.getByTestId('m1-gate-g8')).toHaveAttribute('data-status', 'pass')
}

async function openRecruitmentWorkspaceFromLaunchpad(page: Page, workspacePath: string) {
  await page.getByTestId('m1-launchpad-open-recruitment').click()
  await page.waitForURL((u) => u.pathname.includes(workspacePath), { timeout: 60_000 })
  await expect(page).not.toHaveURL(/\/app\/setup/)
}

test.describe('M1-01.2 — Launchpad slice', () => {
  test('signup → platform setup → launchpad with recruitment configure', async ({ page }) => {
    test.skip(slice === 'full-only', 'Signup slice only unless MILESTONE_1_SLICE=full')

    const email = uniqueSignupEmail('m1-tenant')
    const userName = `M1 User ${Date.now()}`

    await fillSignupForm(page, { name: userName, email })
    await page.waitForURL((u) => u.pathname.includes('/app/platform/setup'), {
      timeout: 60_000,
      waitUntil: 'commit',
    })

    await completePlatformSetup(page, {
      companyName: `M1 Agency ${Date.now()} Sp. z o.o.`,
      identityId: 'recruitment_agency',
    })

    await page.waitForURL((u) => u.pathname.includes('/app/launchpad'), {
      timeout: 60_000,
      waitUntil: 'commit',
    })
    await expect(page.getByTestId('m1-launchpad')).toBeVisible({ timeout: 30_000 })
    await expect(page.getByTestId('m1-launchpad-module-recruitment')).toHaveAttribute(
      'data-module-status',
      'configure',
    )
    await page.getByTestId('m1-launchpad-open-recruitment').click()
    await page.waitForURL((u) => u.pathname.includes('/app/setup'), { timeout: 30_000 })
    await expect(page.getByTestId('m1-setup-hub')).toBeVisible()
  })
})

test.describe('Milestone 1 — Agency Human Gate', () => {
  test('agency reaches READY and opens candidates workspace', async ({ page }) => {
    test.skip(slice !== 'full' && slice !== 'agency', 'Set MILESTONE_1_SLICE=full or agency')

    const email = uniqueSignupEmail('m1-agency')
    const userName = `M1 Agency User ${Date.now()}`

    await fillSignupForm(page, { name: userName, email })
    await page.waitForURL((u) => u.pathname.includes('/app/platform/setup'), { timeout: 60_000 })
    await completePlatformSetup(page, {
      companyName: `M1 Agency ${Date.now()} Sp. z o.o.`,
      identityId: 'recruitment_agency',
    })
    await expect(page.getByTestId('m1-launchpad')).toBeVisible({ timeout: 60_000 })

    await page.getByTestId('m1-launchpad-open-recruitment').click()
    await expect(page.getByTestId('m1-setup-hub')).toBeVisible({ timeout: 60_000 })

    await page.getByTestId('m1-action-add-client').click()
    await completeSetupFirstClient(page, 'M1 Test Client')
    await page.getByTestId('m1-setup-back-launchpad').click()
    await expect(page.getByTestId('m1-launchpad')).toBeVisible({ timeout: 30_000 })

    await page.getByTestId('m1-launchpad-open-recruitment').click()
    await page.getByTestId('m1-action-add-vacancy').click()
    await completeSetupFirstVacancy(page, 'Driver CE')
    await completeSetupProcessDefaults(page)
    await completeSetupCandidateIntakeManual(page)

    await assertRecruitmentReadyOnLaunchpad(page)
    await openRecruitmentWorkspaceFromLaunchpad(page, '/app/candidates')

    await page.goto('/app/setup')
    await assertSetupHubReady(page, { expectClientGate: true })
  })
})

test.describe('Milestone 1 — Employer Human Gate', () => {
  test('transport employer reaches READY without client step', async ({ page }) => {
    test.skip(slice !== 'full' && slice !== 'employer', 'Set MILESTONE_1_SLICE=full or employer')

    const email = uniqueSignupEmail('m1-employer')
    const userName = `M1 Transport User ${Date.now()}`

    await fillSignupForm(page, { name: userName, email })
    await page.waitForURL((u) => u.pathname.includes('/app/platform/setup'), { timeout: 60_000 })
    await completePlatformSetup(page, {
      companyName: `M1 Transport ${Date.now()} Sp. z o.o.`,
      identityId: 'transport_company',
    })
    await expect(page.getByTestId('m1-launchpad')).toBeVisible({ timeout: 60_000 })

    await page.getByTestId('m1-launchpad-open-recruitment').click()
    await expect(page.getByTestId('m1-setup-hub')).toBeVisible({ timeout: 60_000 })
    await expect(page.getByTestId('m1-gate-g2')).toHaveAttribute('data-status', 'na')

    await page.getByTestId('m1-action-add-vacancy').click()
    await completeSetupFirstVacancy(page, 'Driver CE')
    await completeSetupProcessDefaults(page)
    await completeSetupCandidateIntakeManual(page)

    await assertRecruitmentReadyOnLaunchpad(page)
    await openRecruitmentWorkspaceFromLaunchpad(page, '/app/vacancies')

    await page.goto('/app/setup')
    await assertSetupHubReady(page, { expectClientGate: false })
  })
})
