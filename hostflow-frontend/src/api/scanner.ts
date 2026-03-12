import http from './http'

const publicOrigin = () => (typeof window !== 'undefined' && window.location ? window.location.origin : '')
const publicUrl = (path: string) => `${publicOrigin()}${path}`

export type ScanPreset = {
  code: string
  name: string
  aspect_ratio: number
  expected_pages: string[]
  min_resolution_width: number
  min_resolution_height: number
  max_angle_deviation_deg: number
  min_brightness: number
  max_brightness: number
  min_sharpness: number
  target_width: number
}

export type ScanPage = {
  id: string
  page_code: string
  status: string
  quality_score?: number | null
  issues: string[]
  rotation: number
  applied_filter?: string | null
  preview_url?: string | null
  original_url?: string | null
}

export type ScanSession = {
  id: string
  candidate_id: string
  document_type: string
  document_kind_id?: string | null
  preset_code: string
  status: string
  expected_pages: string[]
  pages: ScanPage[]
  quality_summary?: Record<string, any>
  processed_at?: string | null
  attached_at?: string | null
  failed_reason?: string | null
  can_attach_to_candidate: boolean
  upload_limits: {
    max_pages: number
    max_file_size_mb: number
  }
}

export async function fetchPublicScanPresets(): Promise<ScanPreset[]> {
  const { data } = await http.get(publicUrl('/public/scan/presets'))
  return data
}

export async function createPublicScanSession(payload: {
  token: string
  document_type: string
  preset_code?: string
  document_kind_id?: string
  expected_pages?: string[]
  meta?: Record<string, any>
}): Promise<ScanSession> {
  const { data } = await http.post(publicUrl('/public/scan-sessions'), payload)
  return data
}

export async function getPublicScanSession(id: string): Promise<ScanSession> {
  if (!id || id === 'undefined' || id === 'null') {
    throw new Error('Session ID is required')
  }
  const { data } = await http.get(publicUrl(`/public/scan-sessions/${id}`))
  return data
}

export async function uploadPublicScanPage(params: {
  sessionId: string
  page_code: string
  file: Blob
  rotation?: number
  filter?: string
  meta?: Record<string, any>
}): Promise<ScanSession> {
  const form = new FormData()
  form.append('page_code', params.page_code)
  form.append('file', params.file)
  if (typeof params.rotation === 'number') {
    form.append('rotation', String(params.rotation))
  }
  if (params.filter) {
    form.append('filter_name', params.filter)
  }
  if (params.meta) {
    form.append('meta', JSON.stringify(params.meta))
  }
  const url = publicUrl(`/public/scan-sessions/${params.sessionId}/pages`)
  try {
    const { data } = await http.post(url, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  } catch (err: any) {
    console.error('[scanner API] Upload error:', {
      url,
      sessionId: params.sessionId,
      pageCode: params.page_code,
      filter: params.filter,
      hasMeta: !!params.meta,
      error: err?.message,
      response: err?.response?.data,
      status: err?.response?.status,
    })
    throw err
  }
}

export async function processPublicScanSession(sessionId: string): Promise<ScanSession> {
  const { data } = await http.post(publicUrl(`/public/scan-sessions/${sessionId}/process`))
  return data
}

export async function uploadPublicScanPdf(params: {
  sessionId: string
  file: Blob
  meta?: Record<string, any>
}): Promise<ScanSession> {
  const form = new FormData()
  form.append('file', params.file)
  if (params.meta) {
    form.append('meta', JSON.stringify(params.meta))
  }
  const url = publicUrl(`/public/scan-sessions/${params.sessionId}/pdf`)
  const { data } = await http.post(url, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
