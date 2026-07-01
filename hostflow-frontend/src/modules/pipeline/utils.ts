/**
 * Utility functions for pipeline module
 */

import { TERMINAL_STAGE_CODES } from './constants';

export function sanitizeStagePath(
  stages: string[],
  targetStage: string,
  terminalStages: ReadonlySet<string> = TERMINAL_STAGE_CODES,
): string[] {
  if (!stages.length) return [];
  return stages.filter((stage) => stage === targetStage || !terminalStages.has(stage));
}

export function normalizeStageCode(value: unknown): string | undefined {
  if (value == null) return undefined;
  const str = String(value).trim();
  return str ? str.toLowerCase() : undefined;
}

// ---- small helpers for card mini-details
export function parseJSONMaybe(v: any) {
  try {
    if (v && typeof v === 'string') return JSON.parse(v);
    if (v && typeof v === 'object') return v;
  } catch {
    /* ignore */
  }
  return null;
}

export function pickMiniFields(item: any) {
  const c = item?.candidate || item || {};
  const extra = parseJSONMaybe(c.extra) || parseJSONMaybe(item?.extra) || {};
  const docs = parseJSONMaybe(c.docs_progress) || parseJSONMaybe(item?.docs_progress) || {};

  const phone: string | undefined = c.phone || extra.phone || extra.phone_number || undefined;

  const citizenship: string | undefined =
    extra.citizenship || extra.passport_country || extra.country || undefined;

  let docsBadge: string | undefined = undefined;
  let docsStats: { total: number; done: number } | undefined;
  if (docs && typeof docs === 'object') {
    const keys = Object.keys(docs);
    if (keys.length) {
      const done = keys.filter(
        (k) => docs[k] === true || docs[k] === 'done' || docs[k] === 'ok',
      ).length;
      docsBadge = `${done}/${keys.length}`;
      docsStats = { total: keys.length, done };
    } else {
      docsStats = { total: 0, done: 0 };
    }
  }

  return { phone, citizenship, docsBadge, docsStats };
}

/** Per-column signals for §2.14 health badges (client-side from pipeline payload). */
export type PipelineColumnHealth = { docsNeedAttention: number; newStage: number }

export function summarizePipelineColumnHealth(items: unknown[]): PipelineColumnHealth {
  let docsNeedAttention = 0
  let newStage = 0
  for (const item of items) {
    const row = item as Record<string, unknown> | null | undefined
    const raw =
      row?.stage ?? row?.status ?? (row?.candidate as Record<string, unknown> | undefined)?.stage ?? (row?.candidate as Record<string, unknown> | undefined)?.status
    const s = String(raw || '').trim().toLowerCase()
    if (s === 'new' || s.startsWith('new_')) newStage += 1
    const { docsStats } = pickMiniFields(item)
    if (docsStats && docsStats.total > 0 && docsStats.done < docsStats.total) docsNeedAttention += 1
  }
  return { docsNeedAttention, newStage }
}

export function parseISODateMaybe(v?: string) {
  if (!v) return null;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Build `tel:` href from a display phone string (digits only). */
export function telHrefFromDisplay(display: string | null | undefined): string | undefined {
  if (!display) return undefined;
  const digits = String(display).replace(/[\s()-]/g, '');
  return digits ? `tel:${digits}` : undefined;
}

