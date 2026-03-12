/**
 * Utility functions for dashboard module
 */

import { DAY_MS } from './constants';
import type { QuickRange, ListResp } from './types';

export function formatDateInput(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function calcRange(range: QuickRange): { from: string; to: string } {
  const today = new Date();
  const to = formatDateInput(today);
  if (range === 'all') return { from: '', to: '' };
  if (range === 'ytd') {
    const start = new Date(today.getFullYear(), 0, 1);
    return { from: formatDateInput(start), to };
  }
  const days = range === '7d' ? 7 : range === '30d' ? 30 : 90;
  const from = new Date(today.getTime() - days * DAY_MS);
  return { from: formatDateInput(from), to };
}

export function normalizeKey(value?: string | null): string {
  if (!value) return '';
  const normalized = value
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '_')
    .replace(/-+/g, '_');
  return normalized;
}

export function normalizeTotal<T>(payload: ListResp<T>): number {
  if (Array.isArray(payload)) return payload.length;
  if (typeof payload === 'object') {
    if (typeof payload.total === 'number') return payload.total;
    if (Array.isArray(payload.items)) return payload.items.length;
  }
  return 0;
}

/** Compute previous period of same length, immediately before [from, to] */
export function calcPrevPeriod(from: string, to: string): { from: string; to: string } | null {
  if (!from || !to) return null;
  const fromD = new Date(from);
  const toD = new Date(to);
  const deltaMs = toD.getTime() - fromD.getTime();
  if (deltaMs <= 0) return null;
  const prevToD = new Date(fromD.getTime() - 86400000);
  const prevFromD = new Date(prevToD.getTime() - deltaMs);
  return { from: formatDateInput(prevFromD), to: formatDateInput(prevToD) };
}

export function formatDelta(current: number, prev: number): string {
  if (prev === 0) return current > 0 ? '+100%' : '0%';
  const pct = Math.round(((current - prev) / prev) * 100);
  return pct >= 0 ? `+${pct}%` : `${pct}%`;
}

