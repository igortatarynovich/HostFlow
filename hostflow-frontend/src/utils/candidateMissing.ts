export type CandidateMissingCode = 'candidate_deleted' | 'candidate_not_found'

export type CandidateMissingState = {
  code: CandidateMissingCode
  applicationId: string | null
  canRecreate: boolean
}

function readDetail(err: unknown): unknown {
  const response = (err as { response?: { status?: number; data?: { detail?: unknown } } })?.response
  if (!response || Number(response.status) !== 404) return undefined
  return response.data?.detail
}

export function parseCandidateMissingError(err: unknown): CandidateMissingState | null {
  const detail = readDetail(err)
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const rec = detail as { code?: unknown; application_id?: unknown; can_recreate?: unknown }
    const code = String(rec.code || '').trim()
    const applicationId =
      typeof rec.application_id === 'string' && rec.application_id.trim()
        ? rec.application_id.trim()
        : null
    if (code === 'candidate_deleted' || code === 'candidate_not_found') {
      return {
        code,
        applicationId,
        canRecreate: Boolean(rec.can_recreate) && code === 'candidate_deleted' && Boolean(applicationId),
      }
    }
  }
  if (detail !== undefined) {
    return { code: 'candidate_not_found', applicationId: null, canRecreate: false }
  }
  return null
}
