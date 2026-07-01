import type { DocumentRuntimeV1 } from '../../utils/runtimeBadgePresentation'
import { RECRUITMENT_DOSSIER_BLOCKS } from './recruitmentDossierBlocks'
import type { RecruitmentBlockStatus } from './recruitmentDossierBlocks'

export const RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY = 'recruitment_dossier_confirmed_blocks'
export const RECRUITMENT_CONFIRM_FINGERPRINTS_EXTRA_KEY = 'recruitment_dossier_confirm_fingerprints'

export type RecruitmentChecklistRow = {
  key: string
  status: RecruitmentBlockStatus
  fingerprint?: string
}

function normType(raw: string): string {
  return String(raw || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')
}

function docTypesForBlockKey(blockKey: string): string[] {
  const block = RECRUITMENT_DOSSIER_BLOCKS.find((b) => b.key === blockKey)
  return block?.docTypes.map(normType) ?? []
}

export function readConfirmedRecruitmentBlocks(extra: Record<string, unknown> | null | undefined): string[] {
  const raw = extra?.[RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY]
  if (!Array.isArray(raw)) return []
  return raw.map((x) => String(x || '').trim()).filter(Boolean)
}

export function readRecruitmentConfirmFingerprints(
  extra: Record<string, unknown> | null | undefined,
): Record<string, string> {
  const raw = extra?.[RECRUITMENT_CONFIRM_FINGERPRINTS_EXTRA_KEY]
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
  const out: Record<string, string> = {}
  for (const [key, value] of Object.entries(raw)) {
    const k = String(key || '').trim()
    const v = String(value || '').trim()
    if (k && v) out[k] = v
  }
  return out
}

/** Fingerprint of reviewed content — changes when files/data change → re-confirm required. */
export function buildRecruitmentBlockConfirmFingerprint(args: {
  blockKey: string
  status: RecruitmentBlockStatus
  missingDocTypes?: string[]
  missingFieldCodes?: string[]
  runtimeByType?: Map<string, DocumentRuntimeV1>
}): string {
  const docTypes = docTypesForBlockKey(args.blockKey)
  const runtimeParts = docTypes
    .map((type) => {
      const runtime = args.runtimeByType?.get(type)
      if (!runtime) return `${type}:missing`
      const docId = String(runtime.document_id || '').trim()
      const workflow = String(runtime.workflow_status || '').trim().toLowerCase()
      return `${type}:${docId || 'none'}:${workflow}`
    })
    .sort()
  return [
    args.status,
    (args.missingDocTypes || []).slice().sort().join(','),
    (args.missingFieldCodes || []).slice().sort().join(','),
    runtimeParts.join(';'),
  ].join('|')
}

function fingerprintMatches(
  blockKey: string,
  fingerprint: string | undefined,
  stored: Record<string, string>,
): boolean {
  const fp = String(fingerprint || '').trim()
  if (!fp) return false
  const saved = stored[blockKey]
  if (!saved) return true
  return saved === fp
}

/** Keep confirmations only for blocks still ready with matching review fingerprint. */
export function pruneConfirmedRecruitmentBlocks(
  confirmed: string[],
  rows: RecruitmentChecklistRow[],
  fingerprints: Record<string, string> = {},
): string[] {
  const rowByKey = new Map(rows.map((r) => [r.key, r]))
  return confirmed.filter((key) => {
    const row = rowByKey.get(key)
    if (!row || row.status !== 'ready') return false
    return fingerprintMatches(key, row.fingerprint, fingerprints)
  })
}

export function recruitmentBlocksPendingConfirm(
  rows: RecruitmentChecklistRow[],
  confirmed: ReadonlySet<string>,
): string[] {
  return rows
    .filter((r) => r.status === 'ready' && !confirmed.has(r.key))
    .map((r) => r.key)
}

export function recruitmentPackageHandoffReady(args: {
  pkgReady: boolean | null | undefined
  pendingConfirmCount: number
}): boolean {
  if (args.pkgReady === false) return false
  if (args.pendingConfirmCount > 0) return false
  return args.pkgReady === true
}
