import { test, expect } from '@playwright/test'

/**
 * Single UI smoke: unassigned queue URL → context menu → Claim → row leaves server-filtered list.
 *
 * Requires:
 * - `PLAYWRIGHT_BASE_URL` — CRM origin. **Recommended:** `http://127.0.0.1:8000` when the API serves
 *   `hostflow-frontend/dist` (docker `backend` + mounted `dist`) so `/api/v1` matches production `VITE_API_BASE=/api/v1`.
 *   Plain `vite preview` on :5173 uses relative `/api/v1` → rebuild with an absolute `VITE_API_BASE` or use `vite dev` + proxy.
 * - Same API/DB as `seed_recruitment_team_scenario.py` (tenant 2222…, scenario.recruiter-a@…).
 * - Seed **inbox** unassigned lead must still be unassigned (API smoke uses a disposable lead, not this id).
 *   After this test once, re-seed or reset that candidate before the next UI run.
 *
 * `npm run e2e:recruit-flow-all` defaults `PLAYWRIGHT_BASE_URL` to `http://127.0.0.1:8000` (override if needed).
 */
const SEED_UNASSIGNED_CANDIDATE_ID = 'c7755dec-a678-52c0-aa02-4785aac1e524'

const LOGIN_EMAIL =
  (process.env.RECRUIT_FLOW_UI_EMAIL || 'scenario.recruiter-a@recruit-flow.local').trim()
const LOGIN_PASSWORD = (process.env.RECRUIT_FLOW_SCENARIO_PASSWORD || 'RecruitFlow123!').trim()

const uiBaseUrl = (process.env.PLAYWRIGHT_BASE_URL || '').trim()
test.skip(
  !uiBaseUrl,
  'Set PLAYWRIGHT_BASE_URL to a running CRM (e.g. http://127.0.0.1:5173)',
)

test.describe('Recruitment scenario — unassigned queue (UI smoke)', () => {
  test('claim from context menu removes lead from unassigned list after reload', async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[type="email"]').fill(LOGIN_EMAIL)
    await page.locator('input[type="password"]').fill(LOGIN_PASSWORD)
    await page.locator('form button.btn-primary').click()
    // Client-side navigate after login does not fire a full document `load`; `commit` matches SPA history updates.
    await page.waitForURL((u) => !u.pathname.includes('/login'), {
      timeout: 60_000,
      waitUntil: 'commit',
    })

    await page.goto('/app/candidates?assignment_state=unassigned', { waitUntil: 'domcontentloaded' })

    const row = page.locator(`tr[data-candidate-id="${SEED_UNASSIGNED_CANDIDATE_ID}"]`)
    await expect(row).toBeVisible({ timeout: 60_000 })

    // Open row context menu away from name/mailto/action controls (they can steal the gesture).
    const box = await row.boundingBox()
    expect(box, 'candidate row should have layout').toBeTruthy()
    await page.mouse.click(box!.x + box!.width - 24, box!.y + 12, { button: 'right' })
    const claimBtn = page.getByRole('button', {
      name: /claim lead|забрать лид/i,
    })
    await expect(claimBtn).toBeVisible({ timeout: 15_000 })
    await claimBtn.click()

    // Cold reload: list is refetched with `assignment_state=unassigned` — claimed lead must drop off.
    await page.reload({ waitUntil: 'domcontentloaded' })
    await expect(row).toHaveCount(0, { timeout: 60_000 })
  })
})
