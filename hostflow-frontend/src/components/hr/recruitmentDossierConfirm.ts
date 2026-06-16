import type { RecruitmentBlockStatus } from './recruitmentDossierBlocks'

export const RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY = 'recruitment_dossier_confirmed_blocks'

export type RecruitmentChecklistRow = {
  key: string
  status: RecruitmentBlockStatus
}

export function readConfirmedRecruitmentBlocks(extra: Record<string, unknown> | null | undefined): string[] {
  const raw = extra?.[RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY]
  if (!Array.isArray(raw)) return []
  return raw.map((x) => String(x || '').trim()).filter(Boolean)
}

/** Keep confirmations only for blocks that are still ready (data changed → re-verify). */
export function pruneConfirmedRecruitmentBlocks(
  confirmed: string[],
  rows: RecruitmentChecklistRow[],
): string[] {
  const readyKeys = new Set(rows.filter((r) => r.status === 'ready').map((r) => r.key))
  return confirmed.filter((key) => readyKeys.has(key))
}

export function recruitmentBlocksPendingConfirm(
  rows: RecruitmentChecklistRow[],
  confirmed: ReadonlySet<string>,
): string[] {
  return rows.filter((r) => r.status === 'ready' && !confirmed.has(r.key)).map((r) => r.key)
}

export function recruitmentPackageHandoffReady(args: {
  pkgReady: boolean | null | undefined
  pendingConfirmCount: number
}): boolean {
  if (args.pkgReady === false) return false
  if (args.pendingConfirmCount > 0) return false
  return args.pkgReady === true
}
