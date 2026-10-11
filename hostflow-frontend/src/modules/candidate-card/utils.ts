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

export function countryFlag(code: string | null | undefined): string {
  const normalized = String(code || '').trim().toUpperCase()
  if (!/^[A-Z]{2}$/.test(normalized)) return ''
  return ccToFlag(normalized)
}

export function ageFromIsoDate(iso: string | null | undefined, now = new Date()): number | null {
  if (!iso) return null
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  if (!match) return null
  const birth = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
  if (Number.isNaN(birth.getTime())) return null
  let age = now.getFullYear() - birth.getFullYear()
  const month = now.getMonth() - birth.getMonth()
  if (month < 0 || (month === 0 && now.getDate() < birth.getDate())) age -= 1
  if (age < 0 || age > 120) return null
  return age
}

export function formatYearsCount(count: number, locale: string): string {
  const abs = Math.abs(Math.trunc(count))
  if (locale.startsWith('ru')) {
    const mod100 = abs % 100
    const mod10 = abs % 10
    if (mod100 > 10 && mod100 < 20) return `${count} лет`
    if (mod10 === 1) return `${count} год`
    if (mod10 > 1 && mod10 < 5) return `${count} года`
    return `${count} лет`
  }
  if (locale.startsWith('pl')) {
    if (abs === 1) return `${count} rok`
    const mod100 = abs % 100
    const mod10 = abs % 10
    if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) return `${count} lata`
    return `${count} lat`
  }
  return `${count} ${abs === 1 ? 'year' : 'years'}`
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

