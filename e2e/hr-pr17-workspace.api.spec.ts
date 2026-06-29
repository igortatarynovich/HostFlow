import { test, expect } from '@playwright/test'
import type { APIRequestContext } from '@playwright/test'

/**
 * PR17 HR workspace API smoke — inbox enrichment, directory read-model, by-candidate lookup.
 *
 * Prerequisite: recruitment team scenario seed (same as recruit-flow-scenario.api.spec.ts).
 */
const API_BASE = (process.env.PLAYWRIGHT_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/+$/, '')
const TENANT_ID = (
  process.env.RECRUIT_FLOW_SCENARIO_TENANT_ID || '22222222-2222-2222-2222-222222222222'
).trim()
const SCENARIO_PASSWORD = (process.env.RECRUIT_FLOW_SCENARIO_PASSWORD || 'RecruitFlow123!').trim()

const EMAILS = {
  hr: 'scenario.hr@recruit-flow.local',
} as const

const IDS = {
  candidateHrReadonly: 'ccde37f1-618d-5a97-9fa7-aafa562e6fc2',
  workforceHrReadonly: 'de6bd134-5f58-555f-9264-2292c3bb9662',
} as const

function apiOrigin(): string {
  return API_BASE.replace(/\/api\/v1\/?$/i, '') || 'http://127.0.0.1:8000'
}

function authHeaders(accessToken: string) {
  return {
    Authorization: `Bearer ${accessToken}`,
    'X-Tenant-Id': TENANT_ID,
    'Content-Type': 'application/json',
  }
}

async function login(request: APIRequestContext, email: string): Promise<string> {
  const res = await request.post(`${API_BASE}/auth/login`, {
    data: { email, password: SCENARIO_PASSWORD },
    headers: { 'X-Tenant-Id': TENANT_ID, 'Content-Type': 'application/json' },
  })
  expect(res.ok(), `login failed for ${email}: HTTP ${res.status()}`).toBeTruthy()
  const body = (await res.json()) as { access_token?: string }
  expect(body.access_token).toBeTruthy()
  return body.access_token as string
}

test.describe.configure({ mode: 'serial' })

test.describe('HR PR17 workspace (API smoke)', () => {
  let apiUp = false
  let hrToken: string | undefined

  test.beforeAll(async ({ request }) => {
    const hz = await request.get(`${apiOrigin()}/healthz`)
    if (!hz.ok()) {
      apiUp = false
      return
    }
    try {
      hrToken = await login(request, EMAILS.hr)
      apiUp = true
    } catch {
      apiUp = false
    }
  })

  test('workforce employees directory exposes PR17 verification fields', async ({ request }) => {
    test.skip(!apiUp || !hrToken, `API at ${apiOrigin()} not healthy or HR login failed`)
    const res = await request.get(`${API_BASE}/workforce/employees/directory`, {
      headers: authHeaders(hrToken as string),
      params: { limit: 50, offset: 0 },
    })
    expect(res.ok(), await res.text()).toBeTruthy()
    const body = (await res.json()) as { items?: Array<Record<string, unknown>> }
    expect(Array.isArray(body.items)).toBeTruthy()
    const row = (body.items || []).find((r) => r.employee_id === IDS.workforceHrReadonly)
    expect(row, 'scenario workforce row missing from directory').toBeTruthy()
    expect(row).toHaveProperty('hr_review_status')
    expect(row).toHaveProperty('documents_verified_count')
    expect(row).toHaveProperty('documents_total_count')
    expect(row).toHaveProperty('candidate_id', IDS.candidateHrReadonly)
  })

  test('by-candidate lookup resolves workforce employee', async ({ request }) => {
    test.skip(!apiUp || !hrToken, `API at ${apiOrigin()} not healthy or HR login failed`)
    const res = await request.get(
      `${API_BASE}/workforce/employees/by-candidate/${IDS.candidateHrReadonly}`,
      { headers: authHeaders(hrToken as string) },
    )
    expect(res.ok(), await res.text()).toBeTruthy()
    const body = (await res.json()) as { id?: string; candidate_id?: string }
    expect(body.id).toBe(IDS.workforceHrReadonly)
    expect(body.candidate_id).toBe(IDS.candidateHrReadonly)
  })

  test('HR inbox pending list includes PR17 enrichment keys', async ({ request }) => {
    test.skip(!apiUp || !hrToken, `API at ${apiOrigin()} not healthy or HR login failed`)
    const res = await request.get(`${API_BASE}/hr/handoffs/pending`, {
      headers: authHeaders(hrToken as string),
      params: { limit: 20, offset: 0 },
    })
    expect(res.ok(), await res.text()).toBeTruthy()
    const body = (await res.json()) as { items?: Array<Record<string, unknown>>; total?: number }
    expect(typeof body.total).toBe('number')
    if ((body.items || []).length > 0) {
      const item = body.items![0]
      expect(item).toHaveProperty('operational_queue')
      expect(item).toHaveProperty('transfer_summary')
      expect(item).toHaveProperty('documents_verified_count')
      expect(item).toHaveProperty('documents_total_count')
    }
  })

  test('HR dashboard summary and high-risk expose drill-down fields', async ({ request }) => {
    test.skip(!apiUp || !hrToken, `API at ${apiOrigin()} not healthy or HR login failed`)
    const summary = await request.get(`${API_BASE}/hr/dashboard/summary`, {
      headers: authHeaders(hrToken as string),
      params: { assignee_scope: 'team' },
    })
    expect(summary.ok(), await summary.text()).toBeTruthy()
    const sBody = (await summary.json()) as { counts?: Record<string, number>; previews?: Record<string, unknown> }
    expect(sBody.counts).toBeTruthy()
    expect(sBody.previews).toBeTruthy()

    const highRisk = await request.get(`${API_BASE}/hr/dashboard/high-risk`, {
      headers: authHeaders(hrToken as string),
      params: { assignee_scope: 'team', horizon_days: 30, limit: 10, offset: 0 },
    })
    expect(highRisk.ok(), await highRisk.text()).toBeTruthy()
    const hBody = (await highRisk.json()) as { items?: Array<Record<string, unknown>> }
    if ((hBody.items || []).length > 0) {
      expect(hBody.items![0]).toHaveProperty('workforce_employee_id')
      expect(hBody.items![0]).toHaveProperty('handoff_id')
      expect(hBody.items![0]).toHaveProperty('reason')
    }
  })

  test('handoff employee meta includes recruitment_transfer after materialization', async ({ request }) => {
    test.skip(!apiUp || !hrToken, `API at ${apiOrigin()} not healthy or HR login failed`)
    const res = await request.get(`${API_BASE}/workforce/employees/${IDS.workforceHrReadonly}`, {
      headers: authHeaders(hrToken as string),
    })
    expect(res.ok(), await res.text()).toBeTruthy()
    const body = (await res.json()) as {
      candidate_snapshot?: Record<string, unknown>
      meta?: Record<string, unknown>
    }
    const snap = body.candidate_snapshot
    if (snap) {
      expect(snap).toHaveProperty('personal_data')
    }
    const transfer = (body.meta?.recruitment_transfer || null) as Record<string, unknown> | null
    if (transfer) {
      expect(transfer.candidate_id).toBe(IDS.candidateHrReadonly)
    }
  })
})
