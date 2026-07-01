/**
 * Utility functions for candidate card module
 */

import { UUID_RE, ADDRESS_KEYS } from './constants';
import type { AddressFields } from './types';

export function createLocalId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `tmp-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export function ccToFlag(cc: string): string {
  return cc.replace(/./g, (ch) => String.fromCodePoint(127397 + ch.toUpperCase().charCodeAt(0)));
}

export function makeAddress(value?: Partial<AddressFields> | null): AddressFields {
  const base: AddressFields = { country: '', city: '', street: '', house: '', apt: '', zip: '' };
  if (!value || typeof value !== 'object') return { ...base };
  const next: AddressFields = { ...base };
  for (const key of ADDRESS_KEYS) {
    const val = (value as any)[key];
    next[key] = val != null ? String(val) : '';
  }
  return next;
}

export function isUuidLike(value: unknown): value is string {
  return typeof value === 'string' && UUID_RE.test(value);
}

export function formatDateTime(value?: string | null, locale?: string): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const resolved = locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : locale;
  return date.toLocaleString(resolved);
}

export function parseJSONSafe<T>(value: unknown, fallback: T): T {
  if (value == null) return fallback;
  if (typeof value === 'object') return value as T;
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return parsed as T;
    } catch {
      return fallback;
    }
  }
  return fallback;
}

export function splitFullName(value?: string | null): { first: string; last: string } {
  if (!value || typeof value !== 'string') return { first: '', last: '' };
  const parts = value
    .split(/\s+/)
    .map((part) => part.trim())
    .filter(Boolean);
  if (parts.length === 0) return { first: '', last: '' };
  if (parts.length === 1) return { first: parts[0], last: '' };
  return { first: parts.shift() || '', last: parts.join(' ') };
}

const currencyFmt = new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' });
export function formatAmount(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '-';
  try {
    return currencyFmt.format(value);
  } catch {
    return value.toFixed(2);
  }
}

export function mapResidencyStatusToPolandBasis(value?: string): string {
  if (!value) return '';
  const normalized = value.toLowerCase();
  if (normalized.includes('visa') && normalized.includes('d')) return 'visa_d';
  if (normalized.includes('visa') && normalized.includes('c')) return 'visa_c';
  if (normalized.includes('karta') || normalized.includes('residence')) return 'karta_pobytu';
  if (normalized.includes('eu') || normalized.includes('european')) return 'eu_citizen';
  if (normalized.includes('waiting') || normalized.includes('trc')) return 'waiting_for_trc';
  return 'other';
}

