import { test, expect } from '@playwright/test'
import type { APIRequestContext } from '@playwright/test'
import {
  API_BASE,
  BOOTSTRAP_USERS,
  apiOrigin,
  authHeaders,
  ensureTenantLinkInternalHr,
  login,
  seedDocumentsForReadyForHandoff,
} from './helpers/hostflowApi'

/**
 * End-to-end API: recruitment candidate → internal HR handoff → accept → employee verification surface.
 *
 * Uses bootstrap tenant users (same as pytest conftest). Override via PLAYWRIGHT_* env vars.
 */
test.describe.configure({ mode: 'serial' })

test.describe('HR handoff full flow (API)', () => {
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

  test('recruitment → handoff → accept → employee with PR17 enrichment', async ({ request }) => {
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

    const tag = `e2e-${Date.now().toString(36)}`
    const create = await request.post(`${API_BASE}/candidates`, {
      headers: managerH,
      data: {
        first_name: 'E2E',
        last_name: `Handoff ${tag}`,
        company_id: companyId,
        email: `e2e.handoff.${tag}@example.com`,
        phone: '+48111222333',
      },
    })
    expect(create.ok(), await create.text()).toBeTruthy()
    const candidateId = String((await create.json() as { id: string }).id)

    const enrich = await request.patch(`${API_BASE}/candidates/${candidateId}`, {
      headers: recruiterH,
      data: {
        personal_data: {
          citizenship: 'UA',
          work_country: 'PL',
          passport_number: 'PP-E2E-001',
          address: 'E2E Street 1, Warsaw',
        },
        extra: {
          citizenship: 'UA',
          work_country: 'PL',
          position_category: 'driver',
          legal_status: 'temporary_residence',
          license_number: 'DL-E2E-99',
          handoff_notes: 'e2e docs complete',
        },
      },
    })
    expect(enrich.ok(), await enrich.text()).toBeTruthy()

    await seedDocumentsForReadyForHandoff(request, managerToken!, candidateId)

    const pkg = await request.get(`${API_BASE}/candidates/${candidateId}/recruitment-package`, {
      headers: recruiterH,
    })
    expect(pkg.ok(), await pkg.text()).toBeTruthy()
    const pkgBody = await pkg.json() as { ready?: boolean; transfer_allowed?: boolean }
    expect(pkgBody.ready ?? pkgBody.transfer_allowed).toBeTruthy()

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

    const candAfter = await request.get(`${API_BASE}/candidates/${candidateId}`, { headers: recruiterH })
    expect(candAfter.ok()).toBeTruthy()
    expect(String((await candAfter.json() as { stage?: string }).stage || '').toLowerCase()).toBe('processing_by_hr')

    const byCand = await request.get(`${API_BASE}/workforce/employees/by-candidate/${candidateId}`, { headers: hrH })
    expect(byCand.ok(), await byCand.text()).toBeTruthy()
    const empId = String((await byCand.json() as { id: string }).id)

    const op = await request.get(`${API_BASE}/workforce/employees/${empId}/operational-profile`, { headers: hrH })
    expect(op.ok(), await op.text()).toBeTruthy()
    const rs = ((await op.json() as { recruiter_summary?: Record<string, unknown> }).recruiter_summary) || {}
    expect(rs.citizenship).toBe('UA')
    expect(rs.work_country).toBe('PL')
    expect(rs.position_category).toBe('driver')

    const empRes = await request.get(`${API_BASE}/workforce/employees/${empId}`, { headers: hrH })
    expect(empRes.ok(), await empRes.text()).toBeTruthy()
    const employee = (await empRes.json()) as {
      meta?: Record<string, unknown>
      candidate_snapshot?: Record<string, unknown>
    }
    const transfer = employee.meta?.recruitment_transfer as Record<string, unknown> | undefined
    expect(transfer).toBeTruthy()
    expect(transfer!.candidate_id).toBe(candidateId)
    const snap = employee.candidate_snapshot as Record<string, unknown> | undefined
    expect(snap).toBeTruthy()
    expect(snap!.personal_data).toBeTruthy()

    const hrDocs = await request.get(`${API_BASE}/workforce/employees/${empId}/documents`, { headers: hrH })
    expect(hrDocs.ok(), await hrDocs.text()).toBeTruthy()
    expect(((await hrDocs.json()) as unknown[]).length).toBeGreaterThan(0)

    const bundle = await request.get(`${API_BASE}/workforce/employees/${empId}/hr-bundle`, { headers: hrH })
    expect(bundle.ok(), await bundle.text()).toBeTruthy()
    const wel = ((await bundle.json()) as { work_eligibility_profile?: Record<string, unknown> })
      .work_eligibility_profile
    expect(wel?.citizenship).toBe('UA')
    expect(wel?.work_country).toBe('PL')

    const review = await request.get(`${API_BASE}/workforce/employees/${empId}/hr-review`, { headers: hrH })
    expect(review.ok(), await review.text()).toBeTruthy()
    const panel = await review.json() as { verification_plan?: unknown; documents_for_approval?: unknown[] }
    expect(panel.verification_plan || panel.documents_for_approval).toBeTruthy()

    const directory = await request.get(`${API_BASE}/workforce/employees/directory`, {
      headers: hrH,
      params: { limit: 100, offset: 0 },
    })
    expect(directory.ok(), await directory.text()).toBeTruthy()
    const dirRow = ((await directory.json() as { items?: Array<Record<string, unknown>> }).items || []).find(
      (r) => r.employee_id === empId,
    )
    expect(dirRow).toBeTruthy()
    expect(dirRow).toHaveProperty('hr_review_status')

    const inboxRow = await request.get(`${API_BASE}/hr/handoffs/${handoffId}`, { headers: hrH })
    expect(inboxRow.ok(), await inboxRow.text()).toBeTruthy()
    const inbox = await inboxRow.json() as {
      workforce_employee_id?: string
      transfer_summary?: Record<string, unknown> | null
    }
    expect(inbox.workforce_employee_id).toBe(empId)
    const transferSummary = inbox.transfer_summary as Record<string, unknown> | null | undefined
    expect(transferSummary).toBeTruthy()
    expect(transferSummary!.citizenship || transferSummary!.work_country).toBeTruthy()
  })
})
