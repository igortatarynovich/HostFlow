import { chromium } from 'playwright'
import fs from 'node:fs'
import path from 'node:path'

const BASE_URL = process.env.BASE_URL || 'http://localhost:8000'
const OUT_DIR = process.env.OUT_DIR || path.resolve('docs/manual-checklist/_artifacts/f7-local')

function ts() {
  return new Date().toISOString().replace(/[:.]/g, '-')
}

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true })
}

function randEmail(tag) {
  const id = Math.random().toString(16).slice(2, 10)
  return `e2e+${tag}-${Date.now()}-${id}@example.com`
}

async function screenshot(page, name) {
  const file = path.join(OUT_DIR, `${ts()}-${name}.png`)
  await page.screenshot({ path: file, fullPage: true })
  return file
}

async function tryClickByText(page, text) {
  const loc = page.getByRole('button', { name: text }).first()
  if (await loc.count()) {
    await loc.click()
    return true
  }
  const any = page.getByText(text, { exact: false }).first()
  if (await any.count()) {
    await any.click()
    return true
  }
  return false
}

async function signupAndOnboard({ page, scenario, businessType }) {
  const email = randEmail(scenario)
  const password = 'TestPassw0rd!234'
  const startedAt = Date.now()
  const btLabel =
    businessType === 'agency'
      ? 'Агентство'
      : businessType === 'employer'
        ? 'Прямой работодатель'
        : 'Услуги'

  await page.goto(`${BASE_URL}/?e2e=1`, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(500)
  await screenshot(page, `${scenario}-landing`)

  // Go to signup
  await page.goto(`${BASE_URL}/signup?plan=starter&e2e=1`, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(500)
  await screenshot(page, `${scenario}-signup-page`)

  // Fill basic form heuristically
  const workspaceInput = page.locator('input[type="text"]').first()
  if (await workspaceInput.count()) await workspaceInput.fill(`E2E ${scenario} Workspace ${Date.now()}`)
  const emailInput = page.locator('input[type="email"], input[name*="email" i]').first()
  const passInputs = page.locator('input[type="password"]').all()
  if (await emailInput.count()) await emailInput.fill(email)

  const passLoc = page.locator('input[type="password"]').nth(0)
  if (await passLoc.count()) await passLoc.fill(password)
  const pass2Loc = page.locator('input[type="password"]').nth(1)
  if (await pass2Loc.count()) await pass2Loc.fill(password)

  // Accept legal checkboxes if present
  const checkboxes = page.locator('input[type="checkbox"]')
  const cbCount = await checkboxes.count()
  for (let i = 0; i < cbCount; i++) {
    const cb = checkboxes.nth(i)
    if (!(await cb.isChecked())) {
      try {
        await cb.check({ force: true })
      } catch {
        // ignore non-interactable
      }
    }
  }

  await screenshot(page, `${scenario}-signup-filled`)
  // submit
  const submit = page
    .locator('button[type="submit"], button:has-text("Create account"), button:has-text("Sign up"), button:has-text("Register")')
    .first()
  await submit.click({ force: true })

  // Wait for onboarding/company step (SignupPage logs in then navigates)
  await page.waitForURL(/\/app\/onboarding\/company/, { timeout: 60_000 })
  await screenshot(page, `${scenario}-after-signup`)

  // Ensure we are on onboarding company page
  if (!page.url().includes('/app/onboarding')) {
    await page.goto(`${BASE_URL}/app/onboarding/company`, { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(500)
  }
  await screenshot(page, `${scenario}-onboarding-company`)

  // Choose business type card by text
  await tryClickByText(page, btLabel)
  await page.waitForTimeout(400)
  await screenshot(page, `${scenario}-business-type-selected`)

  // Fill company name if present
  const nameInput = page.locator('input[type="text"]').first()
  if (await nameInput.count()) await nameInput.fill(`E2E ${scenario} ${businessType} ${Date.now()}`)

  await screenshot(page, `${scenario}-company-form-filled`)
  // submit company creation
  const createBtn = page.locator('button[type="submit"]').first()
  await createBtn.click({ force: true, timeout: 30_000 })
  await page.waitForTimeout(1500)
  await screenshot(page, `${scenario}-after-company-create`)

  return {
    email,
    password,
    businessType,
    startedAt,
    endedAt: Date.now(),
    endUrl: page.url(),
  }
}

async function run() {
  ensureDir(OUT_DIR)
  const browser = await chromium.launch({ headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1365, height: 900 } })
  const page = await ctx.newPage()

  const results = []
  for (const s of [
    { scenario: 'b', businessType: 'agency' },
    { scenario: 'c', businessType: 'employer' },
    { scenario: 'a', businessType: 'services' },
  ]) {
    try {
      const r = await signupAndOnboard({ page, scenario: s.scenario, businessType: s.businessType })
      results.push({ ...s, ok: true, ...r })
    } catch (err) {
      results.push({ ...s, ok: false, error: String(err?.message || err) })
      try {
        await screenshot(page, `${s.scenario}-error`)
      } catch {}
    }
  }

  const outJson = path.join(OUT_DIR, `results-${ts()}.json`)
  fs.writeFileSync(outJson, JSON.stringify({ baseUrl: BASE_URL, results }, null, 2))
  await browser.close()
  console.log(outJson)
}

run().catch((e) => {
  console.error(e)
  process.exit(1)
})

