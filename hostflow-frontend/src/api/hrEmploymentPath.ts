import { api } from './client'

export type EmploymentPath = {
  employment: {
    id: string
    state: string
    employee_id: string
    handoff_id: string | null
  } | null
  legal?: {
    outcome: string
    citizenship_class: string | null
    stay_basis: string | null
    work_authorization_basis: string | null
    valid_for_this_employment: string | null
  } | null
  terms?: { complete: boolean; position: string | null } | null
  requirements?: { definition_key: string; applicability: string; resolution: string | null }[]
  requirements_ready?: boolean
  ready_to_start?: { outcome: string; blocked_reasons: string; employee_data_result: string } | null
}

export type LegalReading = {
  citizenship_class: string
  stay_basis: string
  work_authorization_basis: string
  valid_for_this_employment: string
}

export type EmploymentTermsBody = {
  position: string
  contract_basis: string
  work_time_value: string
  work_time_unit: string
  workplace: string
  compensation_amount: string
  compensation_currency: string
  compensation_unit: string
  duration: string
  probation_status: string
}

const base = (employmentId: string) => `/hr/employments/${encodeURIComponent(employmentId)}`

export async function fetchEmploymentPath(employeeId: string): Promise<EmploymentPath> {
  const { data } = await api.get<EmploymentPath>(`/hr/employees/${encodeURIComponent(employeeId)}/employment-path`)
  return data
}

export async function recordEmploymentLegal(employmentId: string, body: LegalReading) {
  const { data } = await api.post(`${base(employmentId)}/legal`, body)
  return data
}

export async function confirmEmploymentTerms(employmentId: string, body: EmploymentTermsBody) {
  const { data } = await api.post(`${base(employmentId)}/terms`, body)
  return data
}

export async function materializeEmploymentRequirements(
  employmentId: string,
  definitionKey: string,
) {
  const { data } = await api.post(`${base(employmentId)}/requirements`, {
    items: [{ definition_key: definitionKey, applicability: 'applicable' }],
  })
  return data
}

export async function waiveEmploymentRequirement(employmentId: string, definitionKey: string, reason: string) {
  const { data } = await api.post(`${base(employmentId)}/requirements/waive`, {
    definition_key: definitionKey,
    reason,
  })
  return data
}

export async function recordReadyToStart(
  employmentId: string,
  legal: LegalReading,
  employeeDataComplete: boolean,
) {
  const { data } = await api.post(`${base(employmentId)}/ready-to-start`, {
    legal,
    employee_data_complete: employeeDataComplete,
    facts: {},
  })
  return data as { outcome: string | null; blocked_reasons: string | null }
}

export async function activateEmployment(
  employmentId: string,
  legal: LegalReading,
  employeeDataComplete: boolean,
) {
  const { data } = await api.post(`${base(employmentId)}/activate`, {
    legal,
    employee_data_complete: employeeDataComplete,
    facts: {},
  })
  return data as { state: string }
}
