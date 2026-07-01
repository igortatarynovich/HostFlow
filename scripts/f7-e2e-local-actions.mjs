/**
 * Staging/local F7 scenarios (Playwright + API).
 * Env:
 *   BASE_URL — API + SPA origin (default http://localhost:8000)
 *   OUT_DIR — screenshot + JSON output directory
 *   E2E_SCENARIOS — optional comma list: a, b, c (default: all). **Scenario A** = `a` + business type **services** (R0.1 rehearsal).
 */
import { chromium } from 'playwright'
import fs from 'node:fs'
import path from 'node:path'

const BASE_URL = process.env.BASE_URL || 'http://localhost:8000'
const OUT_DIR = process.env.OUT_DIR || path.resolve('docs/manual-checklist/_artifacts/f7-local-actions')

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

async function apiJson(url, { method = 'GET', token, tenantId, body } = {}) {
  const headers = { Accept: 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  if (tenantId) headers['X-Tenant-Id'] = tenantId
  if (body) headers['Content-Type'] = 'application/json'
  const res = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined })
  const text = await res.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = { raw: text }
  }
  if (!res.ok) {
    const msg = typeof data?.detail === 'string' ? data.detail : `HTTP ${res.status}`
    const err = new Error(`${method} ${url} failed: ${msg}`)
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

async function signupAndCreateOperatingCompany({ page, scenario, businessType }) {
  const email = randEmail(scenario)
  const password = 'TestPassw0rd!234'
  const btLabel =
    businessType === 'agency'
      ? 'Агентство'
      : businessType === 'employer'
        ? 'Прямой работодатель'
        : 'Услуги'

  await page.goto(`${BASE_URL}/signup?plan=starter&e2e=1`, { waitUntil: 'domcontentloaded' })
  await page.locator('input[type="text"]').first().fill(`E2E ${scenario} Workspace ${Date.now()}`)
  await page.locator('input[type="email"]').first().fill(email)
  await page.locator('input[type="password"]').nth(0).fill(password)
  await page.locator('input[type="password"]').nth(1).fill(password)
  const checkboxes = page.locator('input[type="checkbox"]')
  for (let i = 0, n = await checkboxes.count(); i < n; i++) {
    const cb = checkboxes.nth(i)
    if (!(await cb.isChecked())) await cb.check({ force: true })
  }
  await screenshot(page, `${scenario}-signup-filled`)
  await page.locator('button[type="submit"]').click({ force: true })
  await page.waitForURL(/\/app\/onboarding\/company/, { timeout: 60_000 })
  await screenshot(page, `${scenario}-onboarding-company`)

  await page.getByText(btLabel, { exact: false }).first().click({ force: true })
  await page.locator('input[type="text"]').first().fill(`E2E ${scenario} Operating ${Date.now()}`)
  await screenshot(page, `${scenario}-company-create-filled`)
  await page.locator('button[type="submit"]').click({ force: true })
  await page.waitForURL(/\/app\/onboarding\/getting-started/, { timeout: 60_000 })
  await screenshot(page, `${scenario}-getting-started`)

  const token = await page.evaluate(() => window.localStorage.getItem('access_token') || window.localStorage.getItem('token'))
  if (!token) throw new Error('Missing access token after signup/login')

  const whoami = await apiJson(`${BASE_URL}/api/v1/auth/whoami-verify`, { token })
  const tenantId = String(whoami?.tenant_id || '').trim()
  if (!tenantId) throw new Error('Missing tenant_id in whoami')

  const tenant = await apiJson(`${BASE_URL}/api/v1/tenants/me`, { token, tenantId })
  const tenantSlug = String(tenant?.slug || '').trim()

  return { email, password, token, tenantId, tenantSlug, businessType }
}

async function runScenario({ page, scenario, businessType }) {
  const start = Date.now()
  const shots = []

  const ctx = await signupAndCreateOperatingCompany({ page, scenario, businessType })
  shots.push(await screenshot(page, `${scenario}-post-operating-ready`))

  // Simulate billing checkout (mock) to satisfy payment step in staging.
  const checkout = await apiJson(`${BASE_URL}/api/v1/settings/billing/checkout-session`, {
    method: 'POST',
    token: ctx.token,
    tenantId: ctx.tenantId,
    body: { plan_code: 'starter', success_url: `${BASE_URL}/app/settings/billing?checkout=success`, cancel_url: `${BASE_URL}/app/settings/billing?checkout=cancel` },
  })
  await apiJson(`${BASE_URL}/api/v1/settings/billing/checkout-session/${checkout.session_id}/simulate`, {
    method: 'POST',
    token: ctx.token,
    tenantId: ctx.tenantId,
    body: { outcome: 'success' },
  })
  await page.goto(`${BASE_URL}/app/settings/billing?checkout=success`, { waitUntil: 'domcontentloaded' })
  shots.push(await screenshot(page, `${scenario}-billing-active`))

  // Configure tenant SMTP settings (EMAIL_DELIVERY_MODE=mock makes it safe).
  await apiJson(`${BASE_URL}/api/v1/settings/email`, {
    method: 'PUT',
    token: ctx.token,
    tenantId: ctx.tenantId,
    body: {
      smtp_host: 'mock',
      smtp_port: 587,
      smtp_user: ctx.email,
      smtp_password: 'mock-password',
      from_email: ctx.email,
      from_name: 'E2E',
      use_tls: true,
      is_active: true,
    },
  })

  // Enable baseline communications channels + configure reply templates (auto-reply proxy).
  await apiJson(`${BASE_URL}/api/v1/settings/communications`, {
    method: 'PATCH',
    token: ctx.token,
    tenantId: ctx.tenantId,
    body: {
      channels: {
        timezone: 'Europe/Warsaw',
        channels: [
          { key: 'email', enabled: true, inboundEnabled: true, outboundEnabled: true, routingMode: 'manual', responseSlaMinutes: 30 },
          { key: 'telegram', enabled: true, inboundEnabled: true, outboundEnabled: true, routingMode: 'manual', responseSlaMinutes: 30 },
        ],
        candidateReplyTemplate: 'Auto-reply: we received your message and will respond shortly.',
        clientReplyTemplate: 'Auto-reply: thank you, we will follow up shortly.',
        consentRequired: false,
      },
      email: { incomingEnabled: true, autoThreading: true, syncIntervalMinutes: 5 },
    },
  })

  // Create a second user (manager) for scenarios that require manager assignment/team setup.
  const managerUser = await apiJson(`${BASE_URL}/api/v1/admin/users`, {
    method: 'POST',
    token: ctx.token,
    tenantId: ctx.tenantId,
    body: {
      email: randEmail(`${scenario}-mgr`),
      role: 'supervisor',
      full_name: `E2E Manager ${scenario}`,
      password: 'TestPassw0rd!234',
    },
  })

  // Create a client company via API (common step for A/B; also useful for C to attach vacancy)
  const clientCompany = await apiJson(`${BASE_URL}/api/v1/companies`, {
    method: 'POST',
    token: ctx.token,
    tenantId: ctx.tenantId,
    body: { name: `E2E ${scenario} Client ${Date.now()}`, company_role: 'client' },
  })

  // Create a vacancy so lead routing can resolve vacancy_id in all scenarios.
  const vacancyForLead = await apiJson(`${BASE_URL}/api/v1/vacancies/`, {
    method: 'POST',
    token: ctx.token,
    tenantId: ctx.tenantId,
    body: { company_id: clientCompany.id, title: `E2E ${scenario} Lead Vacancy ${Date.now()}`, status: 'open' },
  }).catch(() => null)

  // Create a lead via Meta webhook ingestion (source -> lead -> assignment -> action).
  const leadGenId = `e2e-${scenario}-${Date.now()}`
  const leadPayload = {
    object: 'page',
    entry: [
      {
        id: 'e2e-page',
        changes: [
          {
            field: 'leadgen',
            value: {
              leadgen_id: leadGenId,
              page_id: 'e2e-page',
              form_id: `e2e-form-${scenario}`,
              ad_id: `e2e-ad-${scenario}`,
              field_data: [
                { name: 'full_name', values: [`E2E Lead ${scenario}`] },
                { name: 'email', values: [`lead-${scenario}-${Date.now()}@example.com`] },
                { name: 'phone_number', values: ['+10000000000'] },
                { name: 'company_name', values: [`E2E LeadCo ${scenario}`] },
                ...(vacancyForLead?.id ? [{ name: 'vacancy_id', values: [String(vacancyForLead.id)] }] : []),
              ],
            },
          },
        ],
      },
    ],
  }
  const lead = await apiJson(`${BASE_URL}/api/v1/leads/meta`, {
    method: 'POST',
    token: ctx.token,
    tenantId: ctx.tenantId,
    body: leadPayload,
  })
  const leadReminders = await apiJson(
    `${BASE_URL}/api/v1/reminders?entity_type=lead&entity_id=${encodeURIComponent(String(lead.lead_id || ''))}`,
    {
      method: 'GET',
      token: ctx.token,
      tenantId: ctx.tenantId,
    },
  ).catch(() => ({ items: [] }))

  // E5 communications depth checks (scheduler/OAuth/workers/audit consistency).
  const e5 = {}
  try {
    e5.schedulerStatus = await apiJson(`${BASE_URL}/api/v1/communications/scheduler/status`, {
      method: 'GET',
      token: ctx.token,
      tenantId: ctx.tenantId,
    })
  } catch (err) {
    e5.schedulerStatus = { ok: false, error: String(err?.message || err) }
  }
  try {
    e5.schedulerRunNow = await apiJson(`${BASE_URL}/api/v1/communications/scheduler/run-now`, {
      method: 'POST',
      token: ctx.token,
      tenantId: ctx.tenantId,
      body: {},
    })
  } catch (err) {
    e5.schedulerRunNow = { ok: false, error: String(err?.message || err) }
  }
  try {
    e5.emailPollWorker = await apiJson(`${BASE_URL}/api/v1/communications/email/worker/poll`, {
      method: 'POST',
      token: ctx.token,
      tenantId: ctx.tenantId,
      body: { limit_per_account: 1 },
    })
  } catch (err) {
    e5.emailPollWorker = { ok: false, error: String(err?.message || err) }
  }
  try {
    e5.emailDispatchWorker = await apiJson(`${BASE_URL}/api/v1/communications/email/worker/dispatch`, {
      method: 'POST',
      token: ctx.token,
      tenantId: ctx.tenantId,
      body: { limit: 5, mark_delivered: true },
    })
  } catch (err) {
    e5.emailDispatchWorker = { ok: false, error: String(err?.message || err) }
  }
  try {
    const emailAccount = await apiJson(`${BASE_URL}/api/v1/communications/accounts`, {
      method: 'POST',
      token: ctx.token,
      tenantId: ctx.tenantId,
      body: {
        channel: 'email',
        account_label: `E2E OAuth ${scenario}`,
        inbox_address: ctx.email,
        is_active: true,
        settings_json: {
          provider: 'gmail',
          oauth: {
            client_id: 'e2e-client-id',
            redirect_uri: `${BASE_URL}/app/email`,
          },
        },
      },
    })
    const oauthStart = await apiJson(`${BASE_URL}/api/v1/communications/accounts/${emailAccount.id}/oauth/start`, {
      method: 'POST',
      token: ctx.token,
      tenantId: ctx.tenantId,
      body: { force_consent: false },
    })
    const oauthComplete = await apiJson(`${BASE_URL}/api/v1/communications/accounts/${emailAccount.id}/oauth/complete`, {
      method: 'POST',
      token: ctx.token,
      tenantId: ctx.tenantId,
      body: { state: oauthStart.state, code: 'e2e-code', simulate_exchange: true },
    })
    e5.oauth = { ok: true, accountId: emailAccount.id, oauthStart, oauthComplete }
  } catch (err) {
    e5.oauth = { ok: false, error: String(err?.message || err) }
  }

  // Create a vacancy for employer scenario
  let vacancy = null
  if (businessType === 'employer') {
    vacancy = await apiJson(`${BASE_URL}/api/v1/vacancies/`, {
      method: 'POST',
      token: ctx.token,
      tenantId: ctx.tenantId,
      body: { company_id: clientCompany.id, title: `E2E ${scenario} Vacancy ${Date.now()}`, status: 'open' },
    })
  }

  // Create a candidate (attach to vacancy when available)
  const candidateBody = { first_name: 'E2E', last_name: `Candidate-${scenario}-${Date.now()}` }
  if (businessType === 'employer') {
    // Employer onboarding creates tenant.type=company (client tenant) where agency-only stages are forbidden.
    candidateBody.stage = 'processing_by_client'
  }
  if (vacancy?.id) candidateBody.vacancy_id = vacancy.id
  if (clientCompany?.id) candidateBody.company_id = clientCompany.id
  candidateBody.manager_id = managerUser.id
  const candidate = await apiJson(`${BASE_URL}/api/v1/candidates`, {
    method: 'POST',
    token: ctx.token,
    tenantId: ctx.tenantId,
    body: candidateBody,
  })

  // Create a reminder/task
  const dueAt = new Date(Date.now() + 60 * 60 * 1000).toISOString()
  const reminder = await apiJson(`${BASE_URL}/api/v1/reminders`, {
    method: 'POST',
    token: ctx.token,
    tenantId: ctx.tenantId,
    body: { title: `E2E ${scenario} follow-up`, due_at: dueAt, entity_type: 'custom', type: 'custom', priority: 'normal' },
  })

  // Email evidence: ingest inbound email + send outbound reply via dispatch (SMTP is mocked).
  const inbound = await apiJson(`${BASE_URL}/api/v1/communications/ingest/email`, {
    method: 'POST',
    token: ctx.token,
    tenantId: ctx.tenantId,
    body: {
      subject: `E2E inbound ${scenario}`,
      from_address: `sender-${scenario}@example.com`,
      to_address: ctx.email,
      text: `Hello from inbound ${scenario}`,
      external_message_ref: `e2e-${scenario}-${Date.now()}`,
      linked_company_id: clientCompany.id,
      linked_candidate_id: candidate.id,
    },
  })
  const outboundMsg = await apiJson(`${BASE_URL}/api/v1/communications/threads/${inbound.thread.id}/messages`, {
    method: 'POST',
    token: ctx.token,
    tenantId: ctx.tenantId,
    body: {
      message_type: 'text',
      direction: 'outbound',
      subject: `Re: E2E inbound ${scenario}`,
      body_text: `Reply from E2E ${scenario}`,
      delivery_status: 'sent',
    },
  })
  const dispatchOut = await apiJson(`${BASE_URL}/api/v1/communications/messages/${outboundMsg.id}/dispatch`, {
    method: 'POST',
    token: ctx.token,
    tenantId: ctx.tenantId,
    body: { mark_delivered: true, simulate_failure: false },
  })

  try {
    e5.commandAuditBatch = await apiJson(`${BASE_URL}/api/v1/communications/commands/audit/batch`, {
      method: 'POST',
      token: ctx.token,
      tenantId: ctx.tenantId,
      body: {
        channel: 'email',
        thread_id: String(inbound.thread.id),
        command_id: 'e2e_cmd',
        command_label: 'E2E audit',
        actions_json: [{ type: 'mark_read' }],
        payload: { scenario, businessType },
      },
    })
    e5.commandAuditList = await apiJson(`${BASE_URL}/api/v1/communications/commands/audit?limit=5`, {
      method: 'GET',
      token: ctx.token,
      tenantId: ctx.tenantId,
    })
  } catch (err) {
    e5.commandAudit = { ok: false, error: String(err?.message || err) }
  }

  // UI evidence: open created records
  await page.goto(`${BASE_URL}/app/clients/${clientCompany.id}`, { waitUntil: 'domcontentloaded' })
  shots.push(await screenshot(page, `${scenario}-client-company-detail`))

  if (vacancy?.id) {
    await page.goto(`${BASE_URL}/app/vacancies/${vacancy.id}`, { waitUntil: 'domcontentloaded' })
    shots.push(await screenshot(page, `${scenario}-vacancy-detail`))
  }

  await page.goto(`${BASE_URL}/app/candidates/${candidate.id}`, { waitUntil: 'domcontentloaded' })
  shots.push(await screenshot(page, `${scenario}-candidate-detail`))

  await page.goto(`${BASE_URL}/app/reminders`, { waitUntil: 'domcontentloaded' })
  shots.push(await screenshot(page, `${scenario}-reminders`))

  await page.goto(`${BASE_URL}/app/leads`, { waitUntil: 'domcontentloaded' })
  shots.push(await screenshot(page, `${scenario}-leads`))

  await page.goto(`${BASE_URL}/app/email`, { waitUntil: 'domcontentloaded' })
  shots.push(await screenshot(page, `${scenario}-email-inbox`))

  await page.goto(`${BASE_URL}/app/settings/users`, { waitUntil: 'domcontentloaded' })
  shots.push(await screenshot(page, `${scenario}-team-users`))

  // F11.6 mobile re-pass evidence (chat-first/thread-first layouts).
  try {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto(`${BASE_URL}/app/inbox?channel=messages`, { waitUntil: 'domcontentloaded' })
    shots.push(await screenshot(page, `${scenario}-mobile-messages`))
    await page.goto(`${BASE_URL}/app/email`, { waitUntil: 'domcontentloaded' })
    shots.push(await screenshot(page, `${scenario}-mobile-email`))
  } catch {
    // best-effort screenshots; do not fail scenario
  }

  const end = Date.now()
  return {
    scenario,
    businessType,
    tenantId: ctx.tenantId,
    tenantSlug: ctx.tenantSlug || ctx.tenantId,
    email: ctx.email,
    durationMs: end - start,
    created: {
      clientCompany,
      vacancy,
      candidate,
      reminder,
      managerUser,
      checkout,
      lead,
      leadReminders,
      inboundThread: inbound.thread,
      outboundMsg: dispatchOut.message,
      e5,
    },
    screenshots: shots,
  }
}

const ALL_SCENARIOS = [
  { scenario: 'b', businessType: 'agency' },
  { scenario: 'c', businessType: 'employer' },
  { scenario: 'a', businessType: 'services' },
]

function scenariosToRun() {
  const raw = process.env.E2E_SCENARIOS?.trim()
  if (!raw) return ALL_SCENARIOS
  const want = new Set(
    raw
      .split(',')
      .map((x) => x.trim().toLowerCase())
      .filter(Boolean),
  )
  return ALL_SCENARIOS.filter((s) => want.has(s.scenario.toLowerCase()))
}

async function main() {
  ensureDir(OUT_DIR)
  const browser = await chromium.launch({ headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1365, height: 900 } })
  const page = await ctx.newPage()

  const plan = scenariosToRun()
  if (plan.length === 0) {
    console.error('E2E_SCENARIOS matched no scenarios; use a, b, c (comma-separated) or omit for all.')
    process.exit(1)
  }

  const runs = []
  for (const s of plan) {
    try {
      runs.push(await runScenario({ page, ...s }))
    } catch (err) {
      runs.push({ ...s, error: String(err?.message || err) })
      try {
        await screenshot(page, `${s.scenario}-error`)
      } catch {}
    }
  }

  const out = path.join(OUT_DIR, `runs-${ts()}.json`)
  fs.writeFileSync(out, JSON.stringify({ baseUrl: BASE_URL, runs }, null, 2))
  await browser.close()
  console.log(out)
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
