import { api, withTenant } from './client'

export type OrgUnitTreeNode = {
  id: string
  tenant_id: string
  parent_id: string | null
  name: string
  unit_type: string
  code: string | null
  leader_user_id: string | null
  sort_order: number
  meta: Record<string, unknown>
  children: OrgUnitTreeNode[]
}

export type OrgUnitMemberRow = {
  user_id: string
  role_in_unit: string
  email: string | null
  full_name: string | null
  short_id: string | null
}

function resolveClient(tenantId?: string) {
  return tenantId ? withTenant(tenantId) : api
}

export function flattenOrgUnitTree(nodes: OrgUnitTreeNode[], depth = 0): { id: string; label: string }[] {
  const out: { id: string; label: string }[] = []
  for (const n of nodes) {
    const pad = depth > 0 ? `${'\u2014 '.repeat(depth)}` : ''
    out.push({ id: n.id, label: `${pad}${n.name}`.trim() })
    if (n.children?.length) out.push(...flattenOrgUnitTree(n.children, depth + 1))
  }
  return out
}

export async function fetchOrgUnitTree(opts?: { tenantId?: string }): Promise<OrgUnitTreeNode[]> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.get<OrgUnitTreeNode[]>('/admin/org-units/tree')
  return Array.isArray(data) ? data : []
}

export type OrgStructureExport = {
  version: number
  tenant_id?: string
  units: Array<Record<string, unknown>>
}

export type OrgStructureImportSummary = {
  created: number
  updated: number
}

export async function exportOrgStructureSnapshot(opts?: { tenantId?: string }): Promise<OrgStructureExport> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.get<OrgStructureExport>('/admin/org-units/export')
  return data as OrgStructureExport
}

export async function importOrgStructureMerge(
  body: { version: 1; units: Array<Record<string, unknown>> },
  opts?: { tenantId?: string },
): Promise<OrgStructureImportSummary> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.post<OrgStructureImportSummary>('/admin/org-units/import', body)
  return data as OrgStructureImportSummary
}

export async function createOrgUnit(
  body: {
    name: string
    parent_id?: string | null
    unit_type?: string
    code?: string | null
    leader_user_id?: string | null
    sort_order?: number
  },
  opts?: { tenantId?: string },
): Promise<Record<string, unknown>> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.post('/admin/org-units', body)
  return data as Record<string, unknown>
}

export async function patchOrgUnit(
  unitId: string,
  body: Partial<{
    name: string
    parent_id: string | null
    unit_type: string
    code: string | null
    leader_user_id: string | null
    sort_order: number
  }>,
  opts?: { tenantId?: string },
): Promise<Record<string, unknown>> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.patch(`/admin/org-units/${encodeURIComponent(unitId)}`, body)
  return data as Record<string, unknown>
}

export async function deleteOrgUnit(unitId: string, opts?: { tenantId?: string }): Promise<void> {
  const client = resolveClient(opts?.tenantId)
  await client.delete(`/admin/org-units/${encodeURIComponent(unitId)}`)
}

export async function listOrgUnitMembers(unitId: string, opts?: { tenantId?: string }): Promise<OrgUnitMemberRow[]> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.get<OrgUnitMemberRow[]>(`/admin/org-units/${encodeURIComponent(unitId)}/members`)
  return Array.isArray(data) ? data : []
}

export async function addOrgUnitMember(
  unitId: string,
  body: { user_id: string; role_in_unit?: string },
  opts?: { tenantId?: string },
): Promise<void> {
  const client = resolveClient(opts?.tenantId)
  await client.post(`/admin/org-units/${encodeURIComponent(unitId)}/members`, body)
}

export async function removeOrgUnitMember(unitId: string, userId: string, opts?: { tenantId?: string }): Promise<void> {
  const client = resolveClient(opts?.tenantId)
  await client.delete(`/admin/org-units/${encodeURIComponent(unitId)}/members/${encodeURIComponent(userId)}`)
}
