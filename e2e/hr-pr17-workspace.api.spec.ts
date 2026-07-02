import { test, expect } from '@playwright/test'
import { API_BASE, apiOrigin } from './helpers/hostflowApi'

/**
 * PR17 HR workspace API smoke — inbox enrichment, directory read-model, by-candidate lookup.
 *
 * Scenario tenant (recruitment team flow seed). Override via RECRUIT_FLOW_* env vars.
 */
const TENANT_ID = (
  process.env.RECRUIT_FLOW_SCENARIO_TENANT_ID || '22222222-2222-2222-2222-222222222222'
).trim()
const SCENARIO_PASSWORD = (process.env.RECRUIT_FLOW_SCENARIO_PASSWORD || 'RecruitFlow123!').trim()

const IDS = {
  candidateHrReadonly: 'ccde37f1-618d-5a97-9fa7-aafa562e6fc2',
  workforceHrReadonly: 'de6bd134-5f58-555f-9264-2292c3bb9662',
} as const

function scenarioHeaders(accessToken: string): Record<string, string> {
  return {
    Authorization: `Bearer ${accessToken}`,
    'X-Tenant-Id': TENANT_ID,
    'Content-Type': 'application/json',
  }
}

async function loginScenario(request: Parameters<typeof login>[0], email: string): Promise<string> {
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
      hrToken = await loginScenario(request, 'scenario.hr@recruit-flow.local')
      apiUp = true
    } catch {
      apiUp = false
    }
  })

  test('workforce employees directory exposes PR17 verification fields', async ({ request }) => {
    test.skip(!apiUp || !hrToken, `API at ${apiOrigin()} not healthy or HR login failed`)
    const res = await request.get(`${API_BASE}/workforce/employees/directory`, {
      headers: scenarioHeaders(hrToken as string),
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
      { headers: scenarioHeaders(hrToken as string) },
    )
    expect(res.ok(), await res.text()).toBeTruthy()
    const body = (await res.json()) as { id?: string; candidate_id?: string }
    expect(body.id).toBe(IDS.workforceHrReadonly)
    expect(body.candidate_id).toBe(IDS.candidateHrReadonly)
  })

  test('HR inbox pending list includes PR17 enrichment keys', async ({ request }) => {
    test.skip(!apiUp || !hrToken, `API at ${apiOrigin()} not healthy or HR login failed`)
    const res = await request.get(`${API_BASE}/hr/handoffs/pending`, {
      headers: scenarioHeaders(hrToken as string),
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
      headers: scenarioHeaders(hrToken as string),
      params: { assignee_scope: 'team' },
    })
    expect(summary.ok(), await summary.text()).toBeTruthy()
    const sBody = (await summary.json()) as { counts?: Record<string, number>; previews?: Record<string, unknown> }
    expect(sBody.counts).toBeTruthy()
    expect(sBody.previews).toBeTruthy()

    const highRisk = await request.get(`${API_BASE}/hr/dashboard/high-risk`, {
      headers: scenarioHeaders(hrToken as string),
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
      headers: scenarioHeaders(hrToken as string),
    })
    expect(res.ok(), await res.text()).toBeTruthy()
    const body = (await res.json()) as {
      candidate_snapshot?: Record<string, unknown>
      meta?: Record<string, unknown>
    }
    const snap = body.candidate_snapshot
    expect(snap).toBeTruthy()
    expect(snap).toHaveProperty('personal_data')
    const transfer = (body.meta?.recruitment_transfer || null) as Record<string, unknown> | null
    expect(transfer).toBeTruthy()
    expect(transfer!.candidate_id).toBe(IDS.candidateHrReadonly)
  })
})
