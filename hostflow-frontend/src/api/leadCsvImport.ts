import { api } from './client'
import http from './http'

/** GET/POST /api/v1/settings/leads/import — same shape as backend LeadImportJobOut */
export type LeadImportJobOut = {
  id: string
  filename: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  total_rows: number
  processed_rows: number
  success_rows: number
  duplicate_rows: number
  failed_rows: number
  created_at: string
  started_at?: string | null
  finished_at?: string | null
  error_report?: Array<{ row?: number; error?: string }> | null
}

/**
 * Upload a CSV; creates leads via the same pipeline as Meta (source csv_import).
 * Requires administrator. Headers must include email and/or phone (or phone_number).
 */
export async function postLeadCsvImport(file: File, sync = false): Promise<LeadImportJobOut> {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await http.post<LeadImportJobOut>('/settings/leads/import', fd, {
    params: { sync },
  })
  return data
}

export async function getLeadImportJob(jobId: string): Promise<LeadImportJobOut> {
  const { data } = await api.get<LeadImportJobOut>(`/settings/leads/import/${jobId}`)
  return data
}

export async function listLeadImportJobs(limit = 20): Promise<LeadImportJobOut[]> {
  const { data } = await api.get<{ items: LeadImportJobOut[] }>('/settings/leads/import', {
    params: { limit },
  })
  return data.items ?? []
}

export async function pollLeadImportJob(
  jobId: string,
  options?: { intervalMs?: number; maxAttempts?: number },
): Promise<LeadImportJobOut> {
  const intervalMs = options?.intervalMs ?? 750
  const maxAttempts = options?.maxAttempts ?? 120
  for (let i = 0; i < maxAttempts; i++) {
    const job = await getLeadImportJob(jobId)
    if (job.status === 'completed' || job.status === 'failed') return job
    await new Promise((r) => setTimeout(r, intervalMs))
  }
  return getLeadImportJob(jobId)
}
