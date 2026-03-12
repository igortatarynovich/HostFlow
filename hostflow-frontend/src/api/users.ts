import { api, withTenant } from './client'
import type {
  AdminUser,
  AdminUserDetail,
  ManagerOption,
  UserAuditEntry,
  UserInvite,
  UserRole,
  UserAvatar,
  UserMe,
  UserMeUpdatePayload,
  UserNotificationPreference,
  UserSessionInfo,
} from './types'

export type AdminUserCreateResponse = AdminUser & { temporary_password?: string | null }

function ensureArray<T>(value: any, fallback: T[] = []): T[] {
  if (Array.isArray(value)) return value as T[]
  if (value && Array.isArray(value.items)) return value.items as T[]
  return fallback
}

function resolveClient(tenantId?: string) {
  return tenantId ? withTenant(tenantId) : api
}

export async function listAdminUsers(opts?: { tenantId?: string }): Promise<AdminUser[]> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.get('/admin/users')
  return ensureArray<AdminUser>(data)
}

export async function fetchUserDetail(userId: string, opts?: { tenantId?: string }): Promise<AdminUserDetail> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.get(`/admin/users/${userId}`)
  return data as AdminUserDetail
}

export async function createUserInvite(payload: {
  email: string
  role: UserRole
  supervisor_id?: string | null
  company_ids?: string[]
  expires_in_hours?: number
}, opts?: { tenantId?: string }): Promise<UserInvite> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.post('/admin/users/invite', payload)
  return data as UserInvite
}

export async function createTenantUser(payload: {
  email: string
  role: UserRole
  full_name?: string | null
  short_id?: string | null
  password?: string | null
  supervisor_id?: string | null
  company_ids?: string[]
}, opts?: { tenantId?: string }): Promise<AdminUserCreateResponse> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.post('/admin/users', payload)
  return data as AdminUserCreateResponse
}

export async function updateUserSupervisor(
  userId: string,
  supervisorId: string | null,
  opts?: { tenantId?: string },
): Promise<AdminUser> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.patch(`/admin/users/${userId}/supervisor`, {
    supervisor_id: supervisorId,
  })
  return data as AdminUser
}

export async function updateUserCompanies(
  userId: string,
  companyIds: string[],
  opts?: { tenantId?: string },
): Promise<AdminUserDetail> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.patch(`/admin/users/${userId}/companies`, {
    company_ids: companyIds,
  })
  return data as AdminUserDetail
}

export async function changeUserRole(
  userId: string,
  role: UserRole,
  opts?: { tenantId?: string },
): Promise<AdminUser> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.patch(`/admin/users/${userId}/role`, { role })
  return data as AdminUser
}

export async function setUserActive(userId: string, value: boolean, opts?: { tenantId?: string }): Promise<AdminUser> {
  const endpoint = value ? 'activate' : 'deactivate'
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.post(`/admin/users/${userId}/${endpoint}`)
  return data as AdminUser
}

export async function revokeRefreshTokens(userId: string, opts?: { tenantId?: string }): Promise<number> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.post(`/admin/users/${userId}/revoke-refresh`)
  return Number(data?.revoked ?? 0)
}

export async function fetchUserAudit(
  userId: string,
  limit = 50,
  opts?: { tenantId?: string },
): Promise<UserAuditEntry[]> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.get(`/admin/users/${userId}/audit`, { params: { limit } })
  return ensureArray<UserAuditEntry>(data)
}

export async function listTenantManagers(opts?: { tenantId?: string }): Promise<ManagerOption[]> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.get('/users/managers')
  return ensureArray<ManagerOption>(data)
}

export async function changeSelfPassword(payload: { current_password: string; new_password: string }): Promise<void> {
  await api.post('/users/me/password', payload)
}

export async function resetUserPassword(
  userId: string,
  opts?: { tenantId?: string },
): Promise<{ revoked_sessions: number }> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.post(`/admin/users/${userId}/password/reset`)
  return {
    revoked_sessions: Number(data?.revoked_sessions ?? 0),
  }
}

export async function requestPasswordReset(email: string): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post('/auth/password/request-reset', { email })
  return data as { ok: boolean; message: string }
}

export async function registerSelfService(payload: {
  email: string
  password: string
  workspace_name: string
  full_name?: string
  plan_code?: string
  accept_terms: boolean
  accept_privacy: boolean
}): Promise<{
  ok: boolean
  user: { id: string; email: string; role: string; tenant_id: string; full_name?: string | null }
  tenant: {
    id: string
    name: string
    slug: string
    workspace_label?: string | null
    status?: string | null
    trial_ends_at?: string | null
    trial_days?: number | null
  }
  meta?: {
    welcome_email_sent?: boolean
  }
}> {
  const { data } = await api.post('/auth/register', payload)
  return data
}

export async function resetPasswordWithToken(token: string, newPassword: string): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post('/auth/password/reset-with-token', { token, new_password: newPassword })
  return data as { ok: boolean; message: string }
}

export async function acceptInvite(payload: { token: string; password: string; full_name?: string; short_id?: string }): Promise<unknown> {
  const { data } = await api.post('/auth/invite/accept', payload)
  return data
}

export async function changeUserPasswordAdmin(
  userId: string,
  payload: { new_password: string; revoke_sessions?: boolean },
  opts?: { tenantId?: string },
): Promise<number> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.post(`/admin/users/${userId}/password`, {
    new_password: payload.new_password,
    revoke_sessions: payload.revoke_sessions ?? true,
  })
  return Number(data?.revoked ?? 0)
}

export async function deleteUserAdmin(userId: string, opts?: { tenantId?: string }): Promise<number> {
  const client = resolveClient(opts?.tenantId)
  const { data } = await client.delete(`/admin/users/${userId}`)
  return Number(data?.revoked_sessions ?? 0)
}

export async function getUserMe(): Promise<UserMe> {
  const { data } = await api.get('/users/me')
  return data as UserMe
}

export async function patchUserMe(payload: UserMeUpdatePayload): Promise<UserMe> {
  const { data } = await api.patch('/users/me', payload)
  return data as UserMe
}

export async function uploadUserAvatar(file: File | Blob): Promise<UserAvatar> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/users/me/avatar', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data as UserAvatar
}

export async function getNotificationPreferences(): Promise<Record<string, UserNotificationPreference>> {
  const { data } = await api.get('/users/me/notifications')
  return data as Record<string, UserNotificationPreference>
}

export async function updateNotificationPreferences(
  payload: Record<string, UserNotificationPreference>,
): Promise<Record<string, UserNotificationPreference>> {
  const { data } = await api.patch('/users/me/notifications', payload)
  return data as Record<string, UserNotificationPreference>
}

export async function listUserSessions(): Promise<UserSessionInfo[]> {
  const { data } = await api.get('/users/me/sessions')
  return ensureArray<UserSessionInfo>(data)
}

export async function revokeUserSessions(): Promise<number> {
  const { data } = await api.delete('/users/me/sessions')
  return Number(data?.revoked ?? 0)
}
