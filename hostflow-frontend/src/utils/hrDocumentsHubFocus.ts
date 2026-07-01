export type HubEmployeeRow = {
  workforce_employee_id?: string | null
}

/** Show pack preview only when the employee filter matches exactly one employee. */
export function resolveFocusedEmployeeId(
  employeeFilter: string,
  rows: HubEmployeeRow[],
): string | null {
  const needle = employeeFilter.trim().toLowerCase()
  if (!needle) return null
  const ids = new Set<string>()
  for (const row of rows) {
    const id = row.workforce_employee_id
    if (id && id.toLowerCase().includes(needle)) ids.add(id)
  }
  return ids.size === 1 ? [...ids][0] : null
}
