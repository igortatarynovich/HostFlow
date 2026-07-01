import type { RequirementPipelineBlockers } from '../api/types/candidateRequirements'
import type { DocBlockersPayload } from './candidateStageDocPolicy'
import { mapRequirementPipelineBlockers } from './requirementsPipelineBlockers'

export type WorkPanelRequirementRow = {
  requirement_code: string
  public_name?: string | null
  fulfilled?: boolean
  evaluation_status?: string | null
  evidence_variant_code?: string | null
  evidence_status?: string | null
  linked_document?: {
    document_id?: string | null
    document_type_code?: string | null
    status?: string | null
  } | null
}

export type WorkPanelRequirementsSummary = {
  all_fulfilled?: boolean
  pipeline_blockers?: RequirementPipelineBlockers
  items?: WorkPanelRequirementRow[]
}

export function parseWorkPanelRequirementsSummary(raw: unknown): WorkPanelRequirementsSummary | null {
  if (!raw || typeof raw !== 'object') return null
  const o = raw as Record<string, unknown>
  const itemsRaw = o.items
  const items: WorkPanelRequirementRow[] = Array.isArray(itemsRaw)
    ? itemsRaw
        .filter((x): x is Record<string, unknown> => x !== null && typeof x === 'object' && !Array.isArray(x))
        .map((row) => {
          const linkedRaw = row.linked_document
          const linked =
            linkedRaw && typeof linkedRaw === 'object' && !Array.isArray(linkedRaw)
              ? {
                  document_id:
                    typeof (linkedRaw as Record<string, unknown>).document_id === 'string'
                      ? ((linkedRaw as Record<string, unknown>).document_id as string)
                      : null,
                  document_type_code:
                    typeof (linkedRaw as Record<string, unknown>).document_type_code === 'string'
                      ? ((linkedRaw as Record<string, unknown>).document_type_code as string)
                      : null,
                  status:
                    typeof (linkedRaw as Record<string, unknown>).status === 'string'
                      ? ((linkedRaw as Record<string, unknown>).status as string)
                      : null,
                }
              : null
          return {
            requirement_code: String(row.requirement_code || ''),
            public_name: typeof row.public_name === 'string' ? row.public_name : null,
            fulfilled: Boolean(row.fulfilled),
            evaluation_status: typeof row.evaluation_status === 'string' ? row.evaluation_status : null,
            evidence_variant_code:
              typeof row.evidence_variant_code === 'string' ? row.evidence_variant_code : null,
            evidence_status: typeof row.evidence_status === 'string' ? row.evidence_status : null,
            linked_document: linked,
          }
        })
        .filter((row) => row.requirement_code)
    : []
  const pb = o.pipeline_blockers
  return {
    all_fulfilled: Boolean(o.all_fulfilled),
    pipeline_blockers: pb && typeof pb === 'object' && !Array.isArray(pb) ? (pb as RequirementPipelineBlockers) : undefined,
    items,
  }
}

export function blockersFromWorkPanelRequirements(
  summary: WorkPanelRequirementsSummary | null | undefined,
): DocBlockersPayload {
  if (!summary?.pipeline_blockers) {
    return { missing: [], problematic: [], inProgress: [] }
  }
  return mapRequirementPipelineBlockers(summary.pipeline_blockers)
}
