/**
 * Normalize `/vacancies/:id/pipeline` payloads and optional rebuild from flat candidates.
 */

import type { PipelineOut } from '../../api/types/pipeline';
import { KANBAN_ORDER } from './constants';
import type { AnyObj } from './types';

function groupByStage(links: any[], stageKey: string): Record<string, any[]> {
  const acc: Record<string, any[]> = {};
  for (const it of links) {
    const code = it?.[stageKey] ?? it?.stage ?? it?.status ?? it?.stage_code;
    if (!code) continue;
    if (!acc[code]) acc[code] = [];
    acc[code].push(it);
  }
  return acc;
}

const KANBAN_CODES = KANBAN_ORDER as readonly string[];

/**
 * Maps arbitrary backend shapes into `PipelineOut` columns + statuses and counts total cards.
 */
export function normalizeVacancyPipelinePayload(
  raw: AnyObj,
  columnOrder: string[],
): { normalized: PipelineOut; total: number } {
  const ps = raw?.profile_stages;
  let columnsIn: any = raw?.columns ?? raw?.columns_by_status ?? raw?.data ?? raw?.pipeline;
  let statusesIn: string[] = raw?.statuses ?? raw?.status_order ?? raw?.stages ?? [];

  if (Array.isArray(columnsIn)) {
    const obj: Record<string, any[]> = {};
    for (const col of columnsIn) {
      const code = col?.code || col?.status || col?.stage || col?.stage_code;
      if (!code) continue;
      const items = col?.items ?? col?.rows ?? col?.candidates ?? [];
      obj[code] = Array.isArray(items) ? items : [];
    }
    columnsIn = obj;
    if (!statusesIn?.length) statusesIn = Object.keys(obj);
  }

  if (!columnsIn && Array.isArray(raw?.links)) {
    const grouped = groupByStage(raw.links, 'stage');
    columnsIn = Object.keys(grouped).length ? grouped : groupByStage(raw.links, 'status');
    if (!statusesIn?.length) statusesIn = Object.keys(columnsIn || {});
  }

  if (!columnsIn || typeof columnsIn !== 'object') {
    columnsIn = {};
  }

  const backendKeys = columnsIn && typeof columnsIn === 'object' ? Object.keys(columnsIn) : [];
  const profileColOrder =
    ps?.column_order ??
    (ps?.stage_columns && typeof ps.stage_columns === 'object'
      ? Object.keys(ps.stage_columns as Record<string, unknown>)
      : undefined);
  const baseOrder: string[] =
    Array.isArray(profileColOrder) && profileColOrder.length
      ? profileColOrder
      : columnOrder.length
        ? [...columnOrder]
        : Array.from(KANBAN_ORDER);
  const extra = backendKeys.filter((k) => !baseOrder.includes(k));
  const statuses: string[] = [...baseOrder, ...extra];

  const columns: Record<string, any[]> = {};
  (statuses || []).forEach((code) => {
    const rawCol = columnsIn?.[code];
    const arr = Array.isArray(rawCol)
      ? rawCol
      : (rawCol?.items ?? rawCol?.rows ?? rawCol?.candidates ?? []);
    const items = Array.isArray(arr)
      ? arr.map((it) => ({
          id: it?.link_id || it?.id,
          candidate_id: it?.candidate_id || it?.candidate?.id,
          candidate_name:
            it?.candidate_name ||
            it?.candidate?.name ||
            [it?.candidate?.first_name, it?.candidate?.last_name].filter(Boolean).join(' ') ||
            it?.name,
          candidate_email: it?.candidate_email || it?.candidate?.email,
          candidate: it?.candidate || undefined,
          ...it,
        }))
      : [];
    columns[code] = items;
  });

  const normalized: PipelineOut = { ...(raw as any), columns, statuses } as PipelineOut;

  let total = 0;
  for (const s of statuses) total += normalized.columns?.[s]?.length || 0;

  return { normalized, total };
}

/**
 * When pipeline payload is empty, rebuild columns from `/candidates` rows for one vacancy.
 */
export function rebuildPipelineColumnsFromCandidates(
  raw: AnyObj,
  filteredCandidates: any[],
  statuses: string[],
  stageToColumn: Record<string, string>,
): PipelineOut {
  const grouped: Record<string, any[]> = {};
  for (const c of filteredCandidates) {
    const code = c?.stage ?? c?.status ?? c?.stage_code ?? 'new';
    const columnKey =
      stageToColumn[code] || (KANBAN_CODES.includes(String(code)) ? String(code) : 'new');
    if (!grouped[columnKey]) grouped[columnKey] = [];
    grouped[columnKey].push({
      id: c?.id,
      candidate_id: c?.id,
      candidate_name:
        c?.name || [c?.first_name, c?.last_name].filter(Boolean).join(' ') || '—',
      candidate_email: c?.email,
      candidate: {
        id: c?.id,
        name: c?.name || [c?.first_name, c?.last_name].filter(Boolean).join(' '),
        email: c?.email,
        stage: code,
        status: code,
      },
      stage: code,
      status: code,
    });
  }

  const finalStatuses = [...new Set([...statuses, ...Object.keys(grouped)])];
  const rebuilt: Record<string, any[]> = {};
  for (const s of finalStatuses) {
    rebuilt[s] = grouped[s] || [];
  }

  return { ...(raw as any), columns: rebuilt, statuses: finalStatuses } as PipelineOut;
}
