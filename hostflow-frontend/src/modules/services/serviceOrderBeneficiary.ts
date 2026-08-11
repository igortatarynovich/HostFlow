/** Service order beneficiary + catalog execution helpers.
 *
 * Params use structural shapes on purpose so both `api/types` and
 * `api/types/service` order/service variants are accepted without casts.
 */

export type ServiceBeneficiaryKind = 'client' | 'candidate' | 'employee'

export type ServiceExecutionMode = 'inline' | 'handoff'

type OrderRoleShape = {
  beneficiary_kind?: ServiceBeneficiaryKind | string | null
  company_id?: string | null
  client_id?: string | null
  candidate_id?: string | null
  employee_id?: string | null
  customer_kind?: ServiceBeneficiaryKind | string | null
  customer_id?: string | null
}

type CatalogMetaShape = { meta?: Record<string, unknown> | null } | null | undefined

type LineExecutionShape = {
  execution_mode?: string | null
  handoff_action?: string | null
  meta?: Record<string, unknown> | null
  service?: { meta?: Record<string, unknown> | null } | null
}

function normalizeKind(value: unknown): ServiceBeneficiaryKind | null {
  const kind = String(value || '').trim().toLowerCase()
  return kind === 'client' || kind === 'candidate' || kind === 'employee' ? kind : null
}

export function orderBeneficiaryKind(order: OrderRoleShape): ServiceBeneficiaryKind | null {
  const explicit = normalizeKind(order.beneficiary_kind)
  if (explicit) return explicit
  if (order.company_id || order.client_id) return 'client'
  if (order.candidate_id) return 'candidate'
  if (order.employee_id) return 'employee'
  return null
}

export function orderBeneficiaryId(order: OrderRoleShape): string | null {
  const kind = orderBeneficiaryKind(order)
  if (kind === 'client') return String(order.company_id || order.client_id || '').trim() || null
  if (kind === 'candidate') return String(order.candidate_id || '').trim() || null
  if (kind === 'employee') return String(order.employee_id || '').trim() || null
  return null
}

/** Bill-To / who pays. Canonical customer_*, else falls back to the typed owner. */
export function orderCustomerKind(order: OrderRoleShape): ServiceBeneficiaryKind | null {
  const explicit = normalizeKind(order.customer_kind)
  if (explicit) return explicit
  return orderBeneficiaryKind(order)
}

export function orderCustomerId(order: OrderRoleShape): string | null {
  if (order.customer_id) return String(order.customer_id).trim() || null
  return orderBeneficiaryId(order)
}

/** Who receives a given line. Item beneficiary, else the order customer. */
export function itemBeneficiaryKind(
  item: { beneficiary_kind?: ServiceBeneficiaryKind | string | null },
  order?: OrderRoleShape | null,
): ServiceBeneficiaryKind | null {
  const explicit = normalizeKind(item.beneficiary_kind)
  if (explicit) return explicit
  return order ? orderCustomerKind(order) : null
}

export function itemBeneficiaryId(
  item: { beneficiary_kind?: ServiceBeneficiaryKind | string | null; beneficiary_id?: string | null },
  order?: OrderRoleShape | null,
): string | null {
  if (item.beneficiary_id) return String(item.beneficiary_id).trim() || null
  if (normalizeKind(item.beneficiary_kind)) return null
  return order ? orderCustomerId(order) : null
}

export function catalogExecutionMode(service: CatalogMetaShape): ServiceExecutionMode {
  const meta = service?.meta
  if (!meta || typeof meta !== 'object') return 'inline'
  const block = (meta as Record<string, unknown>).execution
  if (block && typeof block === 'object') {
    const mode = String((block as Record<string, unknown>).mode || '').trim().toLowerCase()
    return mode === 'handoff' ? 'handoff' : 'inline'
  }
  const mode = String((meta as Record<string, unknown>).execution_mode || '').trim().toLowerCase()
  return mode === 'handoff' ? 'handoff' : 'inline'
}

export function catalogHandoffAction(service: CatalogMetaShape): string | null {
  const meta = service?.meta
  if (!meta || typeof meta !== 'object') return null
  const block = (meta as Record<string, unknown>).execution
  if (block && typeof block === 'object') {
    const action = String((block as Record<string, unknown>).handoff_action || '').trim()
    if (action) return action
  }
  const action = String((meta as Record<string, unknown>).handoff_action || '').trim()
  return action || null
}

export function itemExecutionMode(item: LineExecutionShape): ServiceExecutionMode {
  const fromApi = String(item.execution_mode || '').trim().toLowerCase()
  if (fromApi === 'handoff' || fromApi === 'inline') return fromApi
  const meta = item.meta
  if (meta && typeof meta === 'object' && meta.execution && typeof meta.execution === 'object') {
    const mode = String((meta.execution as Record<string, unknown>).mode || '').trim().toLowerCase()
    if (mode === 'handoff') return 'handoff'
  }
  return catalogExecutionMode(item.service ?? null)
}

export function itemHandoffAction(item: LineExecutionShape): string | null {
  const fromApi = String(item.handoff_action || '').trim()
  if (fromApi) return fromApi
  const meta = item.meta
  if (meta && typeof meta === 'object' && meta.execution && typeof meta.execution === 'object') {
    const action = String((meta.execution as Record<string, unknown>).handoff_action || '').trim()
    if (action) return action
  }
  return catalogHandoffAction(item.service ?? null)
}

export function beneficiaryKindLabel(
  kind: ServiceBeneficiaryKind | null | undefined,
  t: (key: string, options?: { defaultValue?: string }) => string,
): string {
  if (!kind) return t('app.services.beneficiary.unknown', { defaultValue: 'Not specified' })
  return t(`app.services.beneficiary.${kind}`, {
    defaultValue: kind === 'client' ? 'Client' : kind === 'candidate' ? 'Candidate' : 'Employee',
  })
}
