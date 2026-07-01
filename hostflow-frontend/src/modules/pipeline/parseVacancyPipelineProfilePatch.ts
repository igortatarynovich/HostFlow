/**
 * Vacancy pipeline API may embed `profile_stages`; derive UI state patches from raw payload.
 */

import type { AnyObj } from './types';

export type VacancyPipelineProfilePatch = {
  /** `null` = clear profile overlay; otherwise the raw profile object for state. */
  profile: AnyObj | null;
  columnOrder?: string[];
  columnStages?: Record<string, string[]>;
  stageSequence?: string[];
};

export function parseVacancyPipelineProfileStagesPatch(raw: AnyObj): VacancyPipelineProfilePatch {
  const ps = raw?.profile_stages;
  if (ps && typeof ps === 'object') {
    const colOrder = Array.isArray(ps.column_order)
      ? (ps.column_order as string[])
      : ((ps.stage_columns && Object.keys(ps.stage_columns as object)) as string[]) || [];
    const colStages =
      ps.stage_columns && typeof ps.stage_columns === 'object'
        ? (ps.stage_columns as Record<string, string[]>)
        : {};
    const seq = Array.isArray(ps.stage_codes) ? (ps.stage_codes as string[]) : [];
    const patch: VacancyPipelineProfilePatch = { profile: ps as AnyObj };
    if (colOrder.length) patch.columnOrder = colOrder;
    if (Object.keys(colStages).length) patch.columnStages = colStages;
    if (seq.length) patch.stageSequence = seq;
    return patch;
  }
  return { profile: null };
}
