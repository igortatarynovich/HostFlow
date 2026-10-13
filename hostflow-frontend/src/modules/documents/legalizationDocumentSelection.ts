import { normalizeDocTypeCode } from './documentUtils'

export type ContractGroup = { codes: string[] }

type StayContract = {
  evidence?: Array<{ codes?: string[] | null }> | null
  documents?: string[] | null
  dependent_documents?: string[] | null
} | null | undefined

const rawCode = (value?: string | null): string =>
  String(value || '').trim().toLowerCase().replace(/-/g, '_')

/** Codes the evidence contract names. Inbox aliases stay out of the match. */
export function codesKnownToContract(codes: Iterable<string>): Set<string> {
  const known = new Set<string>()
  for (const value of codes) {
    const key = rawCode(value)
    if (!key || key === 'unclassified') continue
    known.add(key)
    const normalized = normalizeDocTypeCode(key)
    if (normalized && normalized !== 'unclassified') known.add(normalized)
  }
  return known
}

export function matchesContract(code: string | null | undefined, known: Set<string>): boolean {
  const key = rawCode(code)
  if (!key || key === 'unclassified') return false
  if (known.has(key)) return true
  const normalized = normalizeDocTypeCode(key)
  return Boolean(normalized && normalized !== 'unclassified' && known.has(normalized))
}

export function stayContractGroups(selected: StayContract): ContractGroup[] {
  if (!selected) return []
  const fromEvidence = (selected.evidence || [])
    .map((group) => ({ codes: (group.codes || []).map((code) => String(code || '')).filter(Boolean) }))
    .filter((group) => codesKnownToContract(group.codes).size > 0)
  if (fromEvidence.length) return fromEvidence
  const groups: ContractGroup[] = []
  if (selected.documents?.length) groups.push({ codes: [...selected.documents] })
  if (selected.dependent_documents?.length) groups.push({ codes: [...selected.dependent_documents] })
  return groups.filter((group) => codesKnownToContract(group.codes).size > 0)
}

export function workContractGroups(
  label: string | null | undefined,
  options: Array<{ code: string; documents?: string[] | null }> = [],
): ContractGroup[] {
  const chosen = options.find((item) => item.code === label)
  const codes = (chosen?.documents || []).map((code) => String(code || '')).filter(Boolean)
  if (codes.length) return [{ codes }]
  if (label === 'oswiadczenie') return [{ codes: ['oswiadczenie'] }]
  if (label === 'work_permit') return [{ codes: ['work_permit'] }]
  return []
}

export function contractAsks(groups: ContractGroup[], code: string | null | undefined): boolean {
  return groups.some((group) => matchesContract(code, codesKnownToContract(group.codes)))
}
