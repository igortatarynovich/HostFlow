import { test, expect } from '@playwright/test'
import type { APIRequestContext } from '@playwright/test'

/**
 * API smoke tests for the recruitment team flow scenario tenant.
 *
 * Prerequisite: seed the scenario (stable UUIDs):
 *   PYTHONPATH=. python3 backend/scripts/seed_recruitment_team_scenario.py
 *
 * API must be up (default http://127.0.0.1:8000). Override base with PLAYWRIGHT_API_BASE_URL
 * (include /api/v1 suffix, same as the CRM client).
 */
const API_BASE = (process.env.PLAYWRIGHT_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(
  /\/+$/,
  '',
)
const TENANT_ID = (
  process.env.RECRUIT_FLOW_SCENARIO_TENANT_ID || '22222222-2222-2222-2222-222222222222'
).trim()
const SCENARIO_PASSWORD = (process.env.RECRUIT_FLOW_SCENARIO_PASSWORD || 'RecruitFlow123!').trim()

const EMAILS = {
  admin: 'scenario.admin@recruit-flow.local',
  supervisor: 'scenario.supervisor@recruit-flow.local',
  recruiterA: 'scenario.recruiter-a@recruit-flow.local',
  hr: 'scenario.hr@recruit-flow.local',
} as const

/** Deterministic ids (uuid5) — must match backend.app.db.seeds.recruitment_team_flow_scenario. */
const IDS = {
  recruiterA: '44916a45-1c14-55fb-94c4-cff9de6f2b11',
  company: 'c6599b33-c59a-515c-8d99-9049c3bfaafe',
  vacancy: '05ae35a6-2dbe-5c7a-8103-9f861167ac41',
  /** Seed inbox row — reserved for UI smoke (`recruit-flow-unassigned-claim.ui.spec.ts`). */
  candidateUnassigned: 'c7755dec-a678-52c0-aa02-4785aac1e524',
  candidateHrReadonly: 'ccde37f1-618d-5a97-9fa7-aafa562e6fc2',
  workforceHrReadonly: 'de6bd134-5f58-555f-9264-2292c3bb9662',
} as const

function apiOrigin(): string {
  const stripped = API_BASE.replace(/\/api\/v1\/?$/i, '')
  return stripped || 'http://127.0.0.1:8000'
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
  expect(body.access_token, 'access_token missing').toBeTruthy()
  return body.access_token as string
}

test.describe.configure({ mode: 'serial' })

test.describe('Recruitment team flow scenario (API smoke)', () => {
  let apiUp = false
  let supervisorToken: string | undefined
  let adminToken: string | undefined
  let recruiterToken: string | undefined
  let hrToken: string | undefined

  test.beforeAll(async ({ request }) => {
    const hz = await request.get(`${apiOrigin()}/healthz`)
    if (!hz.ok()) {
      apiUp = false
      return
    }
    try {
      supervisorToken = await login(request, EMAILS.supervisor)
      adminToken = await login(request, EMAILS.admin)
      recruiterToken = await login(request, EMAILS.recruiterA)
      hrToken = await login(request, EMAILS.hr)
      apiUp = true
    } catch {
      apiUp = false
    }
  })

  test.afterAll(async ({ request }) => {
    if (!apiUp || !supervisorToken) {
      return
    }
    await request.patch(`${API_BASE}/recruiters/users/${IDS.recruiterA}/availability`, {
      data: { state: 'available' },
      headers: authHeaders(supervisorToken),
    })
  })

  test('recruiter availability: no auto-assign when pool has no eligible recruiters', async ({
    request,
  }) => {
    test.skip(
      !apiUp,
      `API at ${apiOrigin()} not healthy, or scenario logins failed (same DB as ASYNC_DATABASE_URL + seed_recruitment_team_scenario.py + RECRUIT_FLOW_SCENARIO_PASSWORD)`,
    )
    expect(supervisorToken && adminToken).toBeTruthy()

    const patchA = await request.patch(`${API_BASE}/recruiters/users/${IDS.recruiterA}/availability`, {
      data: { state: 'offline' },
      headers: authHeaders(supervisorToken as string),
    })
    expect(patchA.ok(), `patch A offline: ${patchA.status()}`).toBeTruthy()

    const email = `e2e-autoassign-${Date.now()}@scenario-lead.local`
    const create = await request.post(`${API_BASE}/candidates`, {
      data: {
        first_name: 'E2E',
        last_name: 'AutoAssign',
        email,
        company_id: IDS.company,
        vacancy_id: IDS.vacancy,
      },
      headers: authHeaders(adminToken as string),
    })
    expect(create.ok(), `create candidate: ${create.status()} ${await create.text()}`).toBeTruthy()
    const row = (await create.json()) as {
      assignment_state?: string
      recruiter_id?: string | null
      manager_id?: string | null
    }
    expect(row.assignment_state).toBe('unassigned')
    expect(row.recruiter_id ?? null).toBeNull()
    expect(row.manager_id ?? null).toBeNull()
  })

  test('claim flow: unassigned queue → claimed by current recruiter', async ({ request }) => {
    test.skip(
      !apiUp,
      `API at ${apiOrigin()} not healthy, or scenario logins failed — align API DB with seed`,
    )
    expect(supervisorToken && recruiterToken && adminToken).toBeTruthy()

    const patchA = await request.patch(`${API_BASE}/recruiters/users/${IDS.recruiterA}/availability`, {
      data: { state: 'offline' },
      headers: authHeaders(supervisorToken as string),
    })
    expect(patchA.ok(), `patch A offline for claim test: ${patchA.status()}`).toBeTruthy()

    const email = `e2e-claim-api-${Date.now()}@scenario-lead.local`
    const create = await request.post(`${API_BASE}/candidates`, {
      data: {
        first_name: 'E2E',
        last_name: 'ClaimAPI',
        email,
        company_id: IDS.company,
        vacancy_id: IDS.vacancy,
      },
      headers: authHeaders(adminToken as string),
    })
    expect(create.ok(), `create claim target: ${create.status()} ${await create.text()}`).toBeTruthy()
    const created = (await create.json()) as { id?: string; assignment_state?: string }
    expect(created.assignment_state).toBe('unassigned')
    const claimId = String(created.id || '').trim()
    expect(claimId).toBeTruthy()

    const claim = await request.post(`${API_BASE}/candidates/${claimId}/claim`, {
      headers: authHeaders(recruiterToken as string),
    })
    expect(claim.ok(), `claim: ${claim.status()} ${await claim.text()}`).toBeTruthy()
    const after = (await claim.json()) as {
      assignment_state?: string
      recruiter_id?: string | null
    }
    expect(after.assignment_state).toBe('claimed')
    expect(after.recruiter_id).toBe(IDS.recruiterA)
  })

  test('HR workforce ownership: recruiter readonly, PATCH blocked; HR can patch employee', async ({
    request,
  }) => {
    test.skip(
      !apiUp,
      `API at ${apiOrigin()} not healthy, or scenario logins failed — align API DB with seed`,
    )
    expect(recruiterToken && hrToken).toBeTruthy()

    const getCand = await request.get(`${API_BASE}/candidates/${IDS.candidateHrReadonly}`, {
      headers: authHeaders(recruiterToken as string),
    })
    expect(getCand.ok()).toBeTruthy()
    const cand = (await getCand.json()) as {
      can_edit?: boolean
      permissions?: { readonly_reason?: string; operational_owner?: string }
    }
    expect(cand.can_edit).toBe(false)
    expect(cand.permissions?.readonly_reason).toBe('workforce_hr_ownership')
    expect(cand.permissions?.operational_owner).toBe('hr')

    const patchCand = await request.patch(`${API_BASE}/candidates/${IDS.candidateHrReadonly}`, {
      data: { first_name: 'ShouldNotApply' },
      headers: authHeaders(recruiterToken as string),
    })
    expect(patchCand.status()).toBe(403)

    const patchEmp = await request.patch(`${API_BASE}/workforce/employees/${IDS.workforceHrReadonly}`, {
      data: { notes: `e2e smoke ${Date.now()}` },
      headers: authHeaders(hrToken as string),
    })
    expect(patchEmp.ok(), `HR patch employee: ${patchEmp.status()} ${await patchEmp.text()}`).toBeTruthy()
  })
})
