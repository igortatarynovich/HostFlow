/**
 * Pure helpers: optimistic column moves + bulk stage-plan / rejection stats.
 */

import type { PipelineOut } from '../../api/types/pipeline';
import { normalizeStageCode } from './utils';
import { parseStageTransitionError } from './pipelineStageErrors';

export type StagePathPlan = { targetStage: string; stages: string[] };

export type BuildStagePathFn = (fromStage: string | undefined, column: string) => StagePathPlan;

export type BulkStageRejectionStats = {
  rodoBlocked: number;
  docsBlocked: number;
  missingByDocs: string[];
};

export function summarizeBulkStageRejectionStats(
  rejected: PromiseRejectedResult[],
): BulkStageRejectionStats {
  let rodoBlocked = 0;
  let docsBlocked = 0;
  const missingByDocs: string[] = [];
  for (const rej of rejected) {
    const parsed = parseStageTransitionError(rej.reason);
    if (parsed.kind === 'rodo') {
      rodoBlocked += 1;
    } else if (parsed.kind === 'handoff_docs') {
      docsBlocked += 1;
      missingByDocs.push(...parsed.missingTypes);
    }
  }
  return { rodoBlocked, docsBlocked, missingByDocs };
}

/** Stage plans for each selected id from current column matrix (bulk modal). */
export function buildBulkColumnStagePlansFromMatrix(
  columns: Record<string, unknown[]> | undefined,
  selectedIds: string[],
  targetColumn: string,
  buildStagePath: BuildStagePathFn,
): Record<string, StagePathPlan> {
  const stagePlans: Record<string, StagePathPlan> = {};
  const flat = Object.values(columns || {}).flat() as any[];
  for (const id of selectedIds) {
    const item = flat.find((c: any) => String(c?.candidate?.id || c?.candidate_id) === id);
    const currentStageRaw =
      item?.stage ?? item?.status ?? item?.candidate?.stage ?? item?.candidate?.status;
    const normalizedCurrent = normalizeStageCode(currentStageRaw);
    stagePlans[id] = buildStagePath(normalizedCurrent, targetColumn);
  }
  return stagePlans;
}

/**
 * Optimistically moves all selected cards into `toColumn` (kanban bulk bar).
 * Returns updated pipeline snapshot and per-id stage plans for PATCH sequencing.
 */
export function applyOptimisticBulkSelectionMove(
  prev: PipelineOut | null,
  selectedIds: string[],
  toColumn: string,
  buildStagePath: BuildStagePathFn,
): { next: PipelineOut | null; stagePlans: Record<string, StagePathPlan> } {
  const stagePlans: Record<string, StagePathPlan> = {};
  if (!prev) {
    return { next: prev, stagePlans };
  }
  const next = { ...prev, columns: { ...prev.columns } as Record<string, any[]> };
  const movedCards: any[] = [];
  for (const key of Object.keys(next.columns)) {
    const col = next.columns[key] || [];
    const keep: any[] = [];
    for (const card of col) {
      const cid = String(card?.candidate?.id || card?.candidate_id);
      if (selectedIds.includes(cid)) {
        const currentStageRaw =
          card?.stage ?? card?.status ?? card?.candidate?.stage ?? card?.candidate?.status;
        const normalizedCurrent = normalizeStageCode(currentStageRaw);
        movedCards.push(card);
        stagePlans[cid] = buildStagePath(normalizedCurrent, toColumn);
      } else {
        keep.push(card);
      }
    }
    next.columns[key] = keep;
  }
  const normalizedCards = movedCards.map((card) => {
    const cid = String(card?.candidate?.id || card?.candidate_id);
    const plan = stagePlans[cid] || buildStagePath(undefined, toColumn);
    const finalStage = plan.targetStage;
    const candidateData = card?.candidate
      ? { ...card.candidate, stage: finalStage, status: finalStage }
      : card?.candidate;
    return {
      ...card,
      stage: finalStage,
      status: finalStage,
      candidate: candidateData,
    };
  });
  next.columns[toColumn] = [...(next.columns[toColumn] || []), ...normalizedCards];
  return { next, stagePlans };
}

/** Optimistically moves one card to a column (DnD). */
export function applyOptimisticDndCardMove(
  prev: PipelineOut | null,
  candidateId: string,
  toColumn: string,
  targetStage: string,
): PipelineOut | null {
  if (!prev) return prev;
  const next = { ...prev, columns: { ...prev.columns } as Record<string, any[]> };
  let card: any = null;
  for (const key of Object.keys(next.columns)) {
    const col = next.columns[key] || [];
    const idx = col.findIndex(
      (it) => String(it.candidate?.id || it.candidate_id) === String(candidateId),
    );
    if (idx > -1) {
      card = col[idx];
    }
    next.columns[key] = col.filter(
      (it) => String(it.candidate?.id || it.candidate_id) !== String(candidateId),
    );
  }
  if (!card) {
    card = { id: candidateId, candidate_id: candidateId };
  }
  const candidateData = card?.candidate
    ? { ...card.candidate, stage: targetStage, status: targetStage }
    : card?.candidate;
  const updatedCard = { ...card, stage: targetStage, status: targetStage, candidate: candidateData };
  next.columns[toColumn] = [...(next.columns[toColumn] || []), updatedCard];
  return next;
}
