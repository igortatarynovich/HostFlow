import { test, expect } from '@playwright/test'

/**
 * Optional smoke: set PLAYWRIGHT_BASE_URL to a running CRM (e.g. Vite preview) and authenticate
 * in the browser session (storage state) before enabling assertions.
 */
test.describe('Meta Leads self-serve', () => {
  test('Meta Leads admin shell loads when base URL is set', async ({ page }) => {
    test.skip(!process.env.PLAYWRIGHT_BASE_URL, 'Set PLAYWRIGHT_BASE_URL to run this e2e')
    await page.goto('/app/settings/integrations/meta')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 30_000 })
  })
})
