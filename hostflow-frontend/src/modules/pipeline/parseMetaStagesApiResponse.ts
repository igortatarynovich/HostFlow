/**
 * Maps `/meta/stages` payloads into state patches for column order, column→stages, and stage sequence.
 */

import { DEFAULT_COLUMN_STAGES, KANBAN_ORDER } from './constants';

export type MetaStagesStatePatch = {
  columnStages?: Record<string, string[]>;
  columnOrder?: string[];
  stageSequence?: string[];
};

function trimCodes(list: unknown[]): string[] {
  return Array.from(
    new Set(
      list
        .map((code: unknown) => (code != null ? String(code).trim() : ''))
        .filter(Boolean),
    ),
  );
}

/**
 * Returns which pipeline meta fields should update from a `/meta/stages` body.
 * Empty object means no changes.
 */
export function parseMetaStagesApiResponse(data: unknown): MetaStagesStatePatch {
  const patch: MetaStagesStatePatch = {};

  if (Array.isArray(data)) {
    const codes = trimCodes(
      data.map((it: unknown) => (typeof it === 'string' ? it : (it as { code?: string })?.code)),
    );
    if (codes.length) patch.stageSequence = codes;
    return patch;
  }

  if (!data || typeof data !== 'object') {
    return patch;
  }

  const metaObj = data as Record<string, unknown>;
  const orderCandidates = Array.isArray(metaObj.order)
    ? metaObj.order
    : Array.isArray(metaObj.codes)
      ? metaObj.codes
      : [];
  const explicitSequence = trimCodes(orderCandidates as unknown[]);

  let groups: Record<string, string[]> = {};
  if (metaObj.groups && typeof metaObj.groups === 'object') {
    for (const [column, list] of Object.entries(metaObj.groups as Record<string, unknown>)) {
      const key = String(column || '').trim();
      if (!key) continue;
      const values = trimCodes(Array.isArray(list) ? (list as unknown[]) : []);
      if (values.length) {
        groups[key] = values;
      }
    }
  }

  if (!Object.keys(groups).length && metaObj.column_of && typeof metaObj.column_of === 'object') {
    const derived: Record<string, string[]> = {};
    for (const [stageCode, column] of Object.entries(metaObj.column_of as Record<string, unknown>)) {
      const colKey = String(column || '').trim();
      const stageKey = String(stageCode || '').trim();
      if (!colKey || !stageKey) continue;
      derived[colKey] = derived[colKey] || [];
      if (!derived[colKey].includes(stageKey)) {
        derived[colKey].push(stageKey);
      }
    }
    if (Object.keys(derived).length) {
      groups = derived;
    }
  }

  if (Object.keys(groups).length) {
    const mergedGroups: Record<string, string[]> = {};
    Object.entries(DEFAULT_COLUMN_STAGES).forEach(([column, stages]) => {
      mergedGroups[column] = Array.isArray(stages) ? [...stages] : [];
    });
    Object.entries(groups).forEach(([column, stages]) => {
      mergedGroups[column] = Array.isArray(stages) ? [...stages] : [];
    });

    patch.columnStages = mergedGroups;

    const metaColumns = Object.keys(groups);
    const orderedColumns = Array.from(
      new Set([
        ...metaColumns,
        ...KANBAN_ORDER.filter((column) => !metaColumns.includes(column)),
      ]),
    );
    if (orderedColumns.length) {
      patch.columnOrder = orderedColumns;
    }

    const flattened = orderedColumns.flatMap((column) => mergedGroups[column] || []);
    if (explicitSequence.length) {
      patch.stageSequence = explicitSequence;
    } else if (flattened.length) {
      patch.stageSequence = Array.from(new Set(flattened));
    }
    return patch;
  }

  if (explicitSequence.length) {
    patch.stageSequence = explicitSequence;
  }
  return patch;
}
