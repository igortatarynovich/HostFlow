/**
 * Backend `GET /settings/communications` enforces `assert_comm_feature_access(..., communicationsAdmin)`.
 * Default allowed roles (unless overridden in tenant settings): administrator, supervisor.
 * Platform superadmin bypass exists only on the server.
 */
export const ROLES_CAN_LOAD_FULL_COMMUNICATIONS_SETTINGS = new Set(['administrator', 'supervisor'])

export function roleMayLoadFullCommunicationsSettings(role: string | undefined): boolean {
  return ROLES_CAN_LOAD_FULL_COMMUNICATIONS_SETTINGS.has(String(role || '').toLowerCase())
}
