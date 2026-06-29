import { CRM_APP_PATHS } from '../app/crmAppPaths'

export function hrEmployeeProfilePath(employeeId: string): string {
  return `${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(employeeId)}`
}

export function hrEmployeeVerificationPath(employeeId: string): string {
  return `${hrEmployeeProfilePath(employeeId)}#hr-verification`
}

export function hrEmployeeDocumentsPath(employeeId: string): string {
  return `${hrEmployeeProfilePath(employeeId)}#hr-employee-linked-documents`
}

export function hrEmployeePostApprovePath(employeeId: string): string {
  return `${hrEmployeeProfilePath(employeeId)}#hr-post-approve`
}

export function hrHandoffPath(handoffId: string): string {
  return `${CRM_APP_PATHS.hrHandoffs}/${encodeURIComponent(handoffId)}`
}

export function hrRiskRowPrimaryHref(row: {
  workforce_employee_id?: string | null
  handoff_id?: string | null
}): string | null {
  const empId = String(row.workforce_employee_id || '').trim()
  if (empId) return hrEmployeeVerificationPath(empId)
  const handoffId = String(row.handoff_id || '').trim()
  if (handoffId) return hrHandoffPath(handoffId)
  return null
}
