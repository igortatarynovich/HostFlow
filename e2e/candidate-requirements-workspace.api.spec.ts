import { test, expect } from '@playwright/test'
import type { APIRequestContext } from '@playwright/test'
import {
  API_BASE,
  BOOTSTRAP_USERS,
  apiOrigin,
  authHeaders,
  ensureTenantLinkInternalHr,
  login,
} from './helpers/hostflowApi'

const DRIVER_CE_FLOWS = [
  ['identity_document', 'identity_any', 'passport'],
  ['legal_stay_confirmation', 'legal_stay_any', 'karta_pobytu'],
  ['driver_license_with_code95', 'combined_eu_license', 'driver_license_code95'],
  ['tachograph_card', 'tacho_any', 'tacho_card'],
  ['medical_fitness', 'medical_any', 'medical_certificate'],
  ['psychological_tests', 'psychological_any', 'psychotest'],
  ['voivodeship_decision', 'decision_any', 'decision'],
] as const

async function createDriverCeCandidate(
  request: APIRequestContext,
  managerToken: string,
  companyId: string,
): Promise<string> {
  const headers = authHeaders(managerToken)

  const profilesRes = await request.get(`${API_BASE}/candidate-profiles`, { headers })
  expect(profilesRes.ok(), await profilesRes.text()).toBeTruthy()
  const profiles = (await profilesRes.json()) as Array<{ id?: string; code?: string }>
  const driverProfile = profiles.find((row) => row.code === 'driver_ce_default')
  expect(driverProfile?.id, 'driver_ce_default profile must exist (run DB seed)').toBeTruthy()

  const tag = Date.now().toString(36)
  const vacRes = await request.post(`${API_BASE}/vacancies`, {
    headers,
    data: {
      company_id: companyId,
      title: `E2E Driver CE ${tag}`,
      candidate_profile_id: driverProfile!.id,
    },
  })
  expect(vacRes.ok(), await vacRes.text()).toBeTruthy()
  const vacancyId = String((await vacRes.json() as { id: string }).id)

  const create = await request.post(`${API_BASE}/candidates`, {
    headers,
    data: {
      first_name: 'E2E',
      last_name: `Workspace ${tag}`,
      company_id: companyId,
      vacancy_id: vacancyId,
      phone: '+48111222333',
      email: `e2e.workspace.${tag}@example.com`,
    },
  })
  expect(create.ok(), await create.text()).toBeTruthy()
  return String((await create.json() as { id: string }).id)
}

async function closeDriverCeRequirements(
  request: APIRequestContext,
  managerToken: string,
  candidateId: string,
): Promise<void> {
  const headers = authHeaders(managerToken)

  const patch = await request.patch(`${API_BASE}/candidates/${candidateId}`, {
    headers,
    data: {
      extra: {
        citizenship: 'UA',
        experience_eu_years: 5,
        address: 'Warsaw, Test Street 1',
        recruitment_dossier_confirmed_blocks: [
          'Contacts & address',
          'Passport / ID',
          'Legal stay',
          'Red paper',
          'Work permit',
          'Driver license',
          'Code95',
          'Tacho card',
          'Medical',
          'Psychological',
          'Work experience',
        ],
      },
      personal_data: {
        address: 'Warsaw, Test Street 1',
        citizenship: 'UA',
      },
    },
  })
  expect(patch.ok(), await patch.text()).toBeTruthy()

  for (const [requirementCode, variantCode, docType] of DRIVER_CE_FLOWS) {
    const docRes = await request.post(`${API_BASE}/documents/`, {
      headers,
      data: {
        candidate_id: candidateId,
        type: docType,
        status: 'approved',
        extra: { title: docType },
      },
    })
    expect(docRes.ok(), await docRes.text()).toBeTruthy()
    const documentId = String((await docRes.json() as { id: string }).id)

    const selectRes = await request.post(
      `${API_BASE}/candidates/${candidateId}/requirements/${requirementCode}/select-evidence`,
      {
        headers,
        data: { evidence_variant_code: variantCode },
      },
    )
    expect(selectRes.ok(), await selectRes.text()).toBeTruthy()
    const evidenceId = String((await selectRes.json() as { evidence_id: string }).evidence_id)

    const linkRes = await request.post(
      `${API_BASE}/candidates/${candidateId}/requirements/evidence/${evidenceId}/documents`,
      { headers, data: { document_id: documentId } },
    )
    expect(linkRes.ok(), await linkRes.text()).toBeTruthy()

    const approveRes = await request.post(
      `${API_BASE}/candidates/${candidateId}/requirements/evidence/${evidenceId}/approve`,
      { headers },
    )
    expect(approveRes.ok(), await approveRes.text()).toBeTruthy()
  }
}

test.describe.configure({ mode: 'serial' })

test.describe('Candidate requirements workspace (API)', () => {
  let apiUp = false
  let managerToken: string | undefined
  let recruiterToken: string | undefined
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

  test('driver_ce workspace closure → transfer-readiness → handoff snapshot', async ({ request }) => {
    test.skip(!apiUp || !managerToken || !recruiterToken || !companyId, 'API or bootstrap logins unavailable')

    const managerH = authHeaders(managerToken!)
    const recruiterH = authHeaders(recruiterToken!)

    await ensureTenantLinkInternalHr(request, managerToken!, companyId!)

    const candidateId = await createDriverCeCandidate(request, managerToken!, companyId!)

    const workspaceBefore = await request.get(`${API_BASE}/candidates/${candidateId}/requirements/workspace`, {
      headers: recruiterH,
    })
    expect(workspaceBefore.ok(), await workspaceBefore.text()).toBeTruthy()
    const wsBefore = (await workspaceBefore.json()) as {
      entity_profile_code?: string
      summary?: { all_fulfilled?: boolean }
      checklist?: { requirements?: Array<{ fulfilled?: boolean }> }
    }
    expect(wsBefore.entity_profile_code).toBe('recruitment.candidate.driver_ce')
    expect(wsBefore.summary?.all_fulfilled).toBeFalsy()
    expect((wsBefore.checklist?.requirements || []).some((row) => !row.fulfilled)).toBeTruthy()

    await closeDriverCeRequirements(request, managerToken!, candidateId)

    const workspaceAfter = await request.get(`${API_BASE}/candidates/${candidateId}/requirements/workspace`, {
      headers: recruiterH,
    })
    expect(workspaceAfter.ok(), await workspaceAfter.text()).toBeTruthy()
    const wsAfter = (await workspaceAfter.json()) as {
      summary?: { all_fulfilled?: boolean }
      transfer_readiness?: { requirement_gate?: { satisfied?: boolean }; transfer_allowed?: boolean }
    }
    expect(wsAfter.summary?.all_fulfilled).toBeTruthy()
    expect(wsAfter.transfer_readiness?.requirement_gate?.satisfied).toBeTruthy()

    const readiness = await request.get(`${API_BASE}/candidates/${candidateId}/transfer-readiness`, {
      headers: recruiterH,
      params: { target_stage: 'ready_for_handoff' },
    })
    expect(readiness.ok(), await readiness.text()).toBeTruthy()
    const readinessBody = (await readiness.json()) as {
      transfer_allowed?: boolean
      requirement_gate?: { applied?: boolean; satisfied?: boolean }
    }
    expect(readinessBody.requirement_gate?.applied).toBeTruthy()
    expect(readinessBody.requirement_gate?.satisfied).toBeTruthy()

    const handoff = await request.post(`${API_BASE}/handoffs/candidates/${candidateId}`, {
      headers: recruiterH,
      data: { client_company_id: companyId, destination: 'internal_hr' },
    })
    expect(handoff.status(), await handoff.text()).toBe(201)
    const handoffId = String((await handoff.json() as { id: string }).id)

    const snapshot = await request.get(`${API_BASE}/handoffs/${handoffId}/snapshot`, { headers: recruiterH })
    expect(snapshot.ok(), await snapshot.text()).toBeTruthy()
    const snapshotBody = (await snapshot.json()) as {
      payload?: { requirement_fulfillments?: Array<{ requirement_code?: string; evidence_id?: string }> }
    }
    const fulfillments = snapshotBody.payload?.requirement_fulfillments || []
    expect(fulfillments.length).toBeGreaterThan(0)
    expect(fulfillments.some((row) => row.requirement_code === 'identity_document' && row.evidence_id)).toBeTruthy()
  })
})
