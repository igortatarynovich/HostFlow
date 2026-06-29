import { expect } from '@playwright/test'
import type { APIRequestContext } from '@playwright/test'

export const API_BASE = (process.env.PLAYWRIGHT_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(
  /\/+$/,
  '',
)

export const DEFAULT_TENANT_ID = (
  process.env.PLAYWRIGHT_TENANT_ID || '11111111-1111-1111-1111-111111111111'
).trim()

export const BOOTSTRAP_USERS = {
  manager: {
    email: process.env.PLAYWRIGHT_MANAGER_EMAIL || 'biuro@work-host.com',
    password: process.env.PLAYWRIGHT_MANAGER_PASSWORD || 'Host123!',
  },
  recruiter: {
    email: process.env.PLAYWRIGHT_RECRUITER_EMAIL || 'recruiter@work-host.com',
    password: process.env.PLAYWRIGHT_RECRUITER_PASSWORD || 'Recruiter123!',
  },
  hr: {
    email: process.env.PLAYWRIGHT_HR_EMAIL || 'hr.officer@work-host.com',
    password: process.env.PLAYWRIGHT_HR_PASSWORD || 'HrOfficer123!',
  },
} as const

export function apiOrigin(): string {
  return API_BASE.replace(/\/api\/v1\/?$/i, '') || 'http://127.0.0.1:8000'
}

export function authHeaders(accessToken: string): Record<string, string> {
  return {
    Authorization: `Bearer ${accessToken}`,
    'X-Tenant-Id': DEFAULT_TENANT_ID,
    'Content-Type': 'application/json',
  }
}

export async function login(request: APIRequestContext, email: string, password: string): Promise<string> {
  const res = await request.post(`${API_BASE}/auth/login`, {
    data: { email, password },
    headers: { 'X-Tenant-Id': DEFAULT_TENANT_ID, 'Content-Type': 'application/json' },
  })
  expect(res.ok(), `login failed for ${email}: HTTP ${res.status()}`).toBeTruthy()
  const body = (await res.json()) as { access_token?: string }
  expect(body.access_token).toBeTruthy()
  return body.access_token as string
}

export const HANDOFF_GATE_DOC_TYPES = [
  'driver_license',
  'code95',
  'tacho_card',
  'national_id',
  'passport',
] as const

export async function seedDocumentsForReadyForHandoff(
  request: APIRequestContext,
  managerToken: string,
  candidateId: string,
): Promise<void> {
  const headers = authHeaders(managerToken)
  const detail = await request.get(`${API_BASE}/candidates/${candidateId}`, { headers })
  expect(detail.ok(), await detail.text()).toBeTruthy()
  const cand = (await detail.json()) as Record<string, unknown>
  const contacts = (cand.contacts || {}) as Record<string, unknown>
  const personal = (cand.personal_data || {}) as Record<string, unknown>
  const patch: Record<string, unknown> = {}
  if (!String(cand.phone || contacts.phone || '').trim()) patch.phone = '+48123456789'
  if (!String(cand.email || contacts.email || '').trim()) patch.email = 'handoff-gate@example.com'
  const addressRaw = personal.address ?? cand.address
  let hasAddress = false
  if (typeof addressRaw === 'string') hasAddress = Boolean(addressRaw.trim())
  else if (addressRaw && typeof addressRaw === 'object') {
    const a = addressRaw as Record<string, unknown>
    hasAddress = Boolean(String(a.line1 || a.address || '').trim())
  }
  if (!hasAddress) patch.personal_data = { ...personal, address: 'Handoff Gate Street 1, Warsaw' }
  if (Object.keys(patch).length) {
    const contactPatch = await request.patch(`${API_BASE}/candidates/${candidateId}`, {
      headers,
      data: patch,
    })
    expect(contactPatch.ok(), await contactPatch.text()).toBeTruthy()
  }
  for (const docType of HANDOFF_GATE_DOC_TYPES) {
    const resp = await request.post(`${API_BASE}/documents/`, {
      headers,
      data: {
        candidate_id: candidateId,
        type: docType,
        status: 'approved',
        extra: { title: docType },
      },
    })
    expect(resp.ok(), await resp.text()).toBeTruthy()
  }
}

export async function ensureTenantLinkInternalHr(
  request: APIRequestContext,
  managerToken: string,
  companyId: string,
): Promise<void> {
  const headers = authHeaders(managerToken)
  const lst = await request.get(`${API_BASE}/tenants/${DEFAULT_TENANT_ID}/links`, { headers })
  expect(lst.ok(), await lst.text()).toBeTruthy()
  const rows = (await lst.json()) as Array<Record<string, unknown>>
  const existing = rows.find((row) => String(row.client_company_id || '') === companyId)
  if (existing?.id) {
    const patch = await request.patch(`${API_BASE}/tenants/${DEFAULT_TENANT_ID}/links/${existing.id}`, {
      headers,
      data: {
        handoff_enabled: true,
        handoff_to_client: true,
        handoff_to_internal_hr: true,
      },
    })
    expect(patch.ok(), await patch.text()).toBeTruthy()
    return
  }
  const create = await request.post(`${API_BASE}/tenants/${DEFAULT_TENANT_ID}/links`, {
    headers,
    data: {
      client_company_id: companyId,
      handoff_enabled: true,
      handoff_to_client: true,
      handoff_to_internal_hr: true,
    },
  })
  expect(create.ok(), await create.text()).toBeTruthy()
}

const BLOCKING_TIERS = new Set(['hard_blocker', 'required', 'hr_requested'])

export type HrReviewPanelJson = {
  verification_plan?: {
    can_approve?: boolean
    verification_order?: Array<{ step_order?: number; label?: string; document_keys?: string[] }>
    documents?: Array<Record<string, unknown>>
  }
  documents_for_approval?: Array<Record<string, unknown>>
}

export async function fetchEmployeeHrReview(
  request: APIRequestContext,
  hrToken: string,
  employeeId: string,
): Promise<HrReviewPanelJson> {
  const res = await request.get(`${API_BASE}/workforce/employees/${employeeId}/hr-review`, {
    headers: authHeaders(hrToken),
  })
  expect(res.ok(), await res.text()).toBeTruthy()
  return (await res.json()) as HrReviewPanelJson
}

function reviewedFieldsPayload(doc: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  const fields = (doc.fields_to_review || []) as Array<Record<string, unknown>>
  for (const f of fields) {
    const code = String(f.field_code || '').trim()
    if (!code) continue
    let value = ''
    const profileVals = f.current_profile_values as Record<string, unknown> | undefined
    if (profileVals) {
      for (const v of Object.values(profileVals)) {
        if (v != null && String(v).trim()) {
          value = String(v).trim()
          break
        }
      }
    }
    if (!value) value = 'E2E-CONFIRMED'
    out[code] = { value, comment: '', confirmed: true }
  }
  return out
}

export async function verifyEmployeeDocument(
  request: APIRequestContext,
  hrToken: string,
  employeeId: string,
  documentKey: string,
  doc: Record<string, unknown>,
): Promise<HrReviewPanelJson> {
  const headers = authHeaders(hrToken)
  const res = await request.post(
    `${API_BASE}/workforce/employees/${employeeId}/hr-review/document-verifications/${encodeURIComponent(documentKey)}/verify`,
    { headers, data: { reviewed_fields: reviewedFieldsPayload(doc) } },
  )
  expect(res.ok(), await res.text()).toBeTruthy()
  return fetchEmployeeHrReview(request, hrToken, employeeId)
}

export function blockingPlanDocuments(panel: HrReviewPanelJson): Array<Record<string, unknown>> {
  const planDocs = panel.verification_plan?.documents || []
  const legacy = panel.documents_for_approval || []
  const docs = planDocs.length > 0 ? planDocs : legacy
  return docs.filter((d) => BLOCKING_TIERS.has(String(d.requirement_tier || '')))
}

export async function confirmAllBlockingEmployeeDocuments(
  request: APIRequestContext,
  hrToken: string,
  employeeId: string,
  panel?: HrReviewPanelJson,
): Promise<HrReviewPanelJson> {
  let current = panel || (await fetchEmployeeHrReview(request, hrToken, employeeId))
  for (const doc of blockingPlanDocuments(current)) {
    const key = String(doc.document_key || '')
    if (!key || !doc.document_id) continue
    const status = String(doc.verification_status || '').toLowerCase()
    if (status === 'verified' || status === 'not_required') continue
    current = await verifyEmployeeDocument(request, hrToken, employeeId, key, doc)
  }
  return current
}
