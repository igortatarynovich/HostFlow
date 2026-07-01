/**
 * Client-side filtering / sorting for Pipeline kanban columns (extracted from Pipeline.tsx).
 */

import type { PipelineOut } from '../../api/types';
import { normalizeSearchValue, phoneTextMatches, textMatches } from '../candidates/candidateUtils';
import { parseISODateMaybe, pickMiniFields } from './utils';

export type PipelineColumnFiltersState = {
  search: string;
  manager: string;
  citizenship: string;
  docs: string;
  from: string;
  to: string;
};

export function pipelineColumnItemMatches(item: unknown, filters: PipelineColumnFiltersState): boolean {
  const row = item as Record<string, unknown>;
  const c = (row?.candidate as Record<string, unknown>) || row || {};

  if (filters.search) {
    const normalizedQuery = normalizeSearchValue(filters.search);
    const name =
      `${String(c.first_name || '')} ${String(c.last_name || '')}`.trim() ||
      String(c.name || '') ||
      String(row.candidate_name || '');
    const email = String(c.email || row.candidate_email || '');
    const phone = String(c.phone || row.candidate_phone || '');
    const haystacks = [name, email, phone];
    const match = haystacks.some((value, idx) =>
      idx === 2 ? phoneTextMatches(value, normalizedQuery) : textMatches(value, normalizedQuery),
    );
    if (!match) return false;
  }

  if (filters.manager) {
    const mid =
      (c as { recruiter_id?: string }).recruiter_id ||
      (c as { manager_id?: string }).manager_id ||
      (c as { manager?: string }).manager ||
      (row as { recruiter_id?: string }).recruiter_id ||
      (row as { manager?: string }).manager ||
      (row as { manager_id?: string }).manager_id;
    if (String(mid || '') !== String(filters.manager)) return false;
  }

  const wantCit = filters.citizenship.trim().toUpperCase();
  if (wantCit) {
    const { citizenship } = pickMiniFields(item);
    if ((citizenship || '').toUpperCase() !== wantCit) return false;
  }

  if (filters.docs) {
    const { docsStats } = pickMiniFields(item);
    const total = docsStats?.total ?? 0;
    const done = docsStats?.done ?? 0;
    const all = total > 0 && done === total;
    const none = total > 0 && done === 0;
    const some = total > 0 && done > 0 && done < total;
    if (filters.docs === 'yes' && !all) return false;
    if (filters.docs === 'no' && !none) return false;
    if (filters.docs === 'partial' && !some) return false;
  }

  const from = filters.from ? new Date(filters.from + 'T00:00:00') : null;
  const to = filters.to ? new Date(filters.to + 'T23:59:59') : null;
  if (from || to) {
    const dtStr = (c.created_at as string | undefined) || (row.created_at as string | undefined);
    const d = parseISODateMaybe(dtStr);
    if (from && d && d < from) return false;
    if (to && d && d > to) return false;
  }

  return true;
}

export function sortPipelineColumnItemsNewestFirst(items: unknown[]): unknown[] {
  return [...items].sort((a, b) => {
    const ra = a as Record<string, unknown>;
    const rb = b as Record<string, unknown>;
    const cA = (ra?.candidate as Record<string, unknown>) || ra || {};
    const cB = (rb?.candidate as Record<string, unknown>) || rb || {};
    const dateA = parseISODateMaybe(
      (cA.created_at as string | undefined) || (ra.created_at as string | undefined),
    );
    const dateB = parseISODateMaybe(
      (cB.created_at as string | undefined) || (rb.created_at as string | undefined),
    );
    if (!dateA && !dateB) return 0;
    if (!dateA) return 1;
    if (!dateB) return -1;
    return dateB.getTime() - dateA.getTime();
  });
}

const hasActiveFilters = (f: PipelineColumnFiltersState): boolean =>
  Boolean(
    f.search || f.manager || f.citizenship || f.docs || f.from || f.to,
  );

/**
 * Per-column filtered + sorted rows for kanban display.
 */
export function buildFilteredPipelineColumns(
  data: PipelineOut | null,
  columnsOrder: string[],
  filters: PipelineColumnFiltersState,
): Record<string, unknown[]> {
  const res: Record<string, unknown[]> = {};
  if (!data?.columns) return res;

  for (const code of columnsOrder || []) {
    let arr: unknown[] = data.columns?.[code] || [];
    if (hasActiveFilters(filters)) {
      arr = arr.filter((item) => pipelineColumnItemMatches(item, filters));
    }
    res[code] = sortPipelineColumnItemsNewestFirst(arr);
  }
  return res;
}

export type PipelineColumnInsights = {
  total: number;
  newCount: number;
  docsReady: number;
  docsAttention: number;
};

export function computePipelineColumnInsights(
  filteredColumns: Record<string, unknown[]>,
  columnsOrder: string[],
): PipelineColumnInsights {
  let newCount = 0;
  let docsReady = 0;
  let docsAttention = 0;
  let total = 0;

  for (const code of columnsOrder || []) {
    const items = filteredColumns?.[code] || [];
    total += items.length;
    items.forEach((item) => {
      const row = item as Record<string, unknown>;
      const stage =
        row?.stage ??
        row?.status ??
        (row?.candidate as Record<string, unknown> | undefined)?.stage ??
        (row?.candidate as Record<string, unknown> | undefined)?.status;
      const s = String(stage || '');
      if (s === 'new' || s.startsWith('new_')) {
        newCount += 1;
      }
      const { docsStats } = pickMiniFields(item);
      if (docsStats) {
        const dTotal = docsStats.total;
        const done = docsStats.done;
        if (dTotal > 0) {
          if (done === dTotal) {
            docsReady += 1;
          } else if (done < dTotal) {
            docsAttention += 1;
          }
        }
      }
    });
  }

  return { total, newCount, docsReady, docsAttention };
}
