/**
 * Platform operators: JWT and profile should agree, but we merge defensively so a stale
 * token cannot downgrade superadmin to a tenant membership role.
 */
export function isPlatformSuperadminRole(role: string | null | undefined): boolean {
  const r = String(role || '').trim().toLowerCase()
  return r === 'superadmin' || r === 'super_admin'
}
