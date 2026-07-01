import { api } from './client'

export type EmailConfig = {
  id: string
  tenant_id: string
  provider: string
  smtp_host: string | null
  smtp_port: number | null
  smtp_user: string | null
  from_email: string
  from_name: string | null
  use_tls: boolean
  is_active: boolean
  has_password: boolean
}

export type EmailConfigUpdate = {
  smtp_host?: string
  smtp_port?: number
  smtp_user?: string
  smtp_password?: string
  from_email: string
  from_name?: string
  use_tls?: boolean
  is_active?: boolean
}

export async function getEmailConfig(): Promise<EmailConfig | null> {
  const { data } = await api.get<EmailConfig | null>('/settings/email')
  return data
}

export async function upsertEmailConfig(payload: EmailConfigUpdate): Promise<EmailConfig> {
  const { data } = await api.put<EmailConfig>('/settings/email', payload)
  return data
}

export async function sendTestEmail(to: string): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post<{ ok: boolean; message: string }>('/settings/email/test', { to })
  return data
}
