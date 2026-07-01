/**
 * Kanban column → stage resolution and multi-hop stage paths for PATCH sequencing.
 */

import { useCallback, useMemo } from 'react';
import {
  DEFAULT_COLUMN_STAGES,
  DEFAULT_STAGE_BY_COLUMN,
  DEFAULT_STAGE_SEQUENCE,
} from './constants';
import { sanitizeStagePath } from './utils';

export function usePipelineStagePath(
  columnStages: Record<string, string[]>,
  stageSequence: string[],
  columnOrder: string[],
) {
  const stageDefaults = useMemo(() => {
    const map: Record<string, string> = { ...DEFAULT_STAGE_BY_COLUMN };
    Object.entries(columnStages || {}).forEach(([column, codes]) => {
      if (!column) return;
      if (Array.isArray(codes) && codes.length) {
        map[column] = String(codes[0]);
      }
    });
    return map;
  }, [columnStages]);

  const orderedStageCodes = useMemo(() => {
    const seq = Array.from(new Set(stageSequence.filter(Boolean)));
    if (seq.length) return seq;
    const fallback = columnOrder.flatMap((column) => columnStages[column] || []);
    if (fallback.length) return Array.from(new Set(fallback.filter(Boolean)));
    return DEFAULT_STAGE_SEQUENCE;
  }, [stageSequence, columnOrder, columnStages]);

  const stageIndexMap = useMemo(() => {
    const map: Record<string, number> = {};
    orderedStageCodes.forEach((code, idx) => {
      map[code] = idx;
    });
    return map;
  }, [orderedStageCodes]);

  const stageToColumn = useMemo(() => {
    const map: Record<string, string> = {};
    Object.entries(DEFAULT_COLUMN_STAGES).forEach(([column, stages]) => {
      stages.forEach((stage) => {
        if (stage) map[stage] = column;
      });
    });
    Object.entries(columnStages).forEach(([column, stages]) => {
      stages.forEach((stage) => {
        if (stage) map[stage] = column;
      });
    });
    return map;
  }, [columnStages]);

  const resolveColumnStage = useCallback(
    (column: string) => {
      const key = String(column || '').trim();
      if (!key) return '';
      const codes = columnStages[key];
      if (Array.isArray(codes) && codes.length) {
        return codes[0];
      }
      return stageDefaults[key] || key;
    },
    [columnStages, stageDefaults],
  );

  const buildStagePath = useCallback(
    (fromStage: string | undefined, column: string) => {
      const targetStage = resolveColumnStage(column);
      if (!targetStage) {
        return { targetStage: column, stages: [] as string[] };
      }
      if (!fromStage) {
        return { targetStage, stages: [targetStage] };
      }
      if (fromStage === targetStage) {
        return { targetStage, stages: [] as string[] };
      }
      const fromIdx = stageIndexMap[fromStage];
      const targetIdx = stageIndexMap[targetStage];
      if (fromIdx === undefined || targetIdx === undefined) {
        return { targetStage, stages: [targetStage] };
      }
      if (targetIdx <= fromIdx) {
        return { targetStage, stages: [targetStage] };
      }
      const stages: string[] = [];
      for (let idx = fromIdx + 1; idx <= targetIdx; idx += 1) {
        const stage = orderedStageCodes[idx];
        if (stage) {
          stages.push(stage);
        }
      }
      const sanitizedStages = sanitizeStagePath(stages, targetStage);
      if (!sanitizedStages.length) {
        sanitizedStages.push(targetStage);
      }
      return { targetStage, stages: sanitizedStages };
    },
    [orderedStageCodes, resolveColumnStage, stageIndexMap],
  );

  return {
    orderedStageCodes,
    stageToColumn,
    resolveColumnStage,
    buildStagePath,
  };
}
