import { test, expect } from '@playwright/test'
import {
  API_BASE,
  BOOTSTRAP_USERS,
  apiOrigin,
  authHeaders,
  blockingPlanDocuments,
  confirmAllBlockingEmployeeDocuments,
  ensureTenantLinkInternalHr,
  fetchEmployeeHrReview,
  login,
  seedDocumentsForReadyForHandoff,
} from './helpers/hostflowApi'

/**
 * PR14 API smoke: verification_plan → confirm blocking docs → can_approve ready gate.
 */
test.describe.configure({ mode: 'serial' })

test.describe('HR verification PR14 (API)', () => {
  let apiUp = false
  let managerToken: string | undefined
  let recruiterToken: string | undefined
  let hrToken: string | undefined
  let companyId: string | undefined

  test.beforeAll(async ({ request }) => {
    const hz = await request.get(`${apiOrigin()}/healthz`)
    if (!hz.ok()) {
      apiUp = false
      return
    }
    try {
      managerToken = await login(request, BOOTSTRAP_USERS.manager.email, BOOTSTRAP_USERS.manager.password)
      recruiterToken = await login(request, BOOTSTRAP_USERS.recruiter.email, BOOTSTRAP_USERS.recruiter.password)
      hrToken = await login(request, BOOTSTRAP_USERS.hr.email, BOOTSTRAP_USERS.hr.password)
      const me = await request.get(`${API_BASE}/auth/me`, { headers: authHeaders(managerToken) })
      expect(me.ok()).toBeTruthy()
      const meBody = (await me.json()) as { company_id?: string }
      companyId = String(meBody.company_id || process.env.PLAYWRIGHT_COMPANY_ID || '').trim() || undefined
      if (!companyId) {
        const companies = await request.get(`${API_BASE}/companies`, { headers: authHeaders(managerToken) })
        if (companies.ok()) {
          const list = (await companies.json()) as Array<{ id?: string }>
          companyId = list[0]?.id
        }
      }
      apiUp = Boolean(companyId)
    } catch {
      apiUp = false
    }
  })

  test('EU non-driver: verification_order → confirm docs → plan ready', async ({ request }) => {
    test.skip(!apiUp || !managerToken || !recruiterToken || !hrToken || !companyId, 'API or bootstrap logins unavailable')

    const managerH = authHeaders(managerToken!)
    const recruiterH = authHeaders(recruiterToken!)
    const hrH = authHeaders(hrToken!)

    const mod = await request.patch(`${API_BASE}/settings/team/modules`, {
      headers: managerH,
      data: { hr: true },
    })
    expect(mod.ok(), await mod.text()).toBeTruthy()

    await ensureTenantLinkInternalHr(request, managerToken!, companyId!)

    const tag = `pr14-${Date.now().toString(36)}`
    const create = await request.post(`${API_BASE}/candidates`, {
      headers: managerH,
      data: {
        first_name: 'PR14',
        last_name: `Verify ${tag}`,
        company_id: companyId,
        email: `pr14.verify.${tag}@example.com`,
        phone: '+48111999888',
      },
    })
    expect(create.ok(), await create.text()).toBeTruthy()
    const candidateId = String((await create.json() as { id: string }).id)

    const enrich = await request.patch(`${API_BASE}/candidates/${candidateId}`, {
      headers: recruiterH,
      data: {
        personal_data: {
          citizenship: 'PL',
          work_country: 'PL',
          pesel: '44051401359',
          address: 'PR14 Street 1, Warsaw',
        },
        extra: {
          citizenship: 'PL',
          work_country: 'PL',
          position_category: 'warehouse',
          handoff_notes: 'pr14 e2e',
        },
      },
    })
    expect(enrich.ok(), await enrich.text()).toBeTruthy()

    await seedDocumentsForReadyForHandoff(request, managerToken!, candidateId)

    const stage = await request.patch(`${API_BASE}/candidates/${candidateId}`, {
      headers: recruiterH,
      data: { stage: 'ready_for_handoff' },
    })
    expect(stage.ok(), await stage.text()).toBeTruthy()

    const handoff = await request.post(`${API_BASE}/handoffs/candidates/${candidateId}`, {
      headers: recruiterH,
      data: { client_company_id: companyId, destination: 'internal_hr' },
    })
    expect(handoff.status(), await handoff.text()).toBe(201)
    const handoffId = String((await handoff.json() as { id: string }).id)

    const accept = await request.post(`${API_BASE}/handoffs/${handoffId}/accept`, { headers: hrH })
    expect(accept.ok(), await accept.text()).toBeTruthy()

    const byCand = await request.get(`${API_BASE}/workforce/employees/by-candidate/${candidateId}`, { headers: hrH })
    expect(byCand.ok(), await byCand.text()).toBeTruthy()
    const empId = String((await byCand.json() as { id: string }).id)

    let panel = await fetchEmployeeHrReview(request, hrToken!, empId)
    const plan = panel.verification_plan
    expect(plan).toBeTruthy()
    expect((plan?.verification_order || []).length).toBeGreaterThan(0)
    expect(plan?.can_approve).not.toBe(true)

    const blocking = blockingPlanDocuments(panel)
    expect(blocking.length).toBeGreaterThan(0)

    panel = await confirmAllBlockingEmployeeDocuments(request, hrToken!, empId, panel)
    expect(panel.verification_plan?.can_approve).toBe(true)
  })
})
