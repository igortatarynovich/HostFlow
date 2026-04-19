/**
 * Core utility functions for candidate data processing
 */

export function sanitizeDocsProgress(value: any): Record<string, any> {
  if (value == null) return {};
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return typeof parsed === 'object' && !Array.isArray(parsed) && parsed ? parsed : {};
    } catch {
      return {};
    }
  }
  if (typeof value === 'object' && !Array.isArray(value)) {
    return { ...value };
  }
  return {};
}

export function firstNonEmpty(...values: any[]): string {
  for (const val of values) {
    if (val == null) continue;
    const str = String(val).trim();
    if (str) return str;
  }
  return '';
}

export function normalizeDateString(value: any): string | null {
  if (!value) return null;
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const parsed = Date.parse(trimmed);
    if (Number.isNaN(parsed)) {
      return trimmed.length >= 10 ? trimmed.slice(0, 10) : trimmed;
    }
    return new Date(parsed).toISOString().slice(0, 10);
  }
  return null;
}

export function toTimestamp(value: string | null): number {
  if (!value) return 0;
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export function formatDateSafe(value: string | null, locale?: string): string {
  if (!value) return '—';
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return value;
  const resolved =
    locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : locale || undefined;
  return new Intl.DateTimeFormat(resolved, { year: 'numeric', month: '2-digit', day: '2-digit' }).format(
    new Date(parsed)
  );
}

export function extractExtraObject(raw: any): Record<string, any> {
  if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
    return raw;
  }
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed;
      }
    } catch {
      /* ignore malformed JSON */
    }
  }
  return {};
}

export function isRangeActive(range: { from: string | null; to: string | null }): boolean {
  return Boolean(range.from || range.to);
}

export function parseBoundary(value: string | null, endOfDay = false): number | null {
  if (!value) return null;
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return null;
  if (!endOfDay) return parsed;
  const end = new Date(parsed);
  end.setHours(23, 59, 59, 999);
  return end.getTime();
}

export function matchesDateRange(value: string | null, range: { from: string | null; to: string | null }): boolean {
  if (!isRangeActive(range)) return true;
  if (!value) return false;
  const target = Date.parse(value);
  if (Number.isNaN(target)) return false;
  const from = parseBoundary(range.from, false);
  const to = parseBoundary(range.to, true);
  if (from !== null && target < from) return false;
  if (to !== null && target > to) return false;
  return true;
}

export function compareStrings(a: string | null | undefined, b: string | null | undefined): number {
  return (a || '').localeCompare(b || '', undefined, { sensitivity: 'base' });
}

export function compareNumbers(a: number, b: number): number {
  return a - b;
}

export function normalizeStageKey(value?: string | null): string {
  return (value ?? '').trim().toLowerCase();
}

export function isLikelyNewStage(stage: string): boolean {
  return stage === 'new' || stage.startsWith('new_') || stage.includes('new');
}

export function normalizeSearchValue(value: string): string {
  return value.trim().toLowerCase();
}

export function textMatches(source: string | null | undefined, query: string): boolean {
  if (!query) return true;
  if (!source) return false;
  return source.toLowerCase().includes(query);
}

/**
 * Phone search: pasted numbers (e.g. from WhatsApp) often contain spaces;
 * stored values may be compact. Match with whitespace ignored and, for long
 * queries, digit-only substring match.
 */
export function phoneTextMatches(source: string | null | undefined, rawQuery: string): boolean {
  const q0 = rawQuery.trim().toLowerCase();
  if (!q0) return true;
  if (!source) return false;
  const s0 = source.toLowerCase();
  if (s0.includes(q0)) return true;
  const qCompact = q0.replace(/\s/g, '');
  const sCompact = s0.replace(/\s/g, '');
  if (qCompact && sCompact.includes(qCompact)) return true;
  const qDigits = qCompact.replace(/\D/g, '');
  const sDigits = sCompact.replace(/\D/g, '');
  if (qDigits.length >= 7 && sDigits.includes(qDigits)) return true;
  return false;
}

export function boolRank(value: boolean | null | undefined): number {
  if (value === true) return 2;
  if (value === false) return 1;
  return 0;
}

export function toCSV(rows: any[], headers: { key: string; title: string }[]): string {
  const esc = (v: any) => {
    if (v === null || v === undefined) return '';
    const s = String(v);
    if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  };
  const head = headers.map((h) => esc(h.title)).join(',');
  const body = rows.map((r) => headers.map((h) => esc(r[h.key])).join(',')).join('\n');
  return head + '\n' + body;
}

