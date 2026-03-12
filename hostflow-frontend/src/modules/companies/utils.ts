/**
 * Utility functions for companies module
 */

import type { AnyRecord, AddressForm, ContactInfo } from './types';
import { CONTACT_ROLE_SET, CONTACT_ROLE_ALIASES } from './constants';

export function normalizeContactRole(value?: string | null): string | undefined {
  if (value === null || value === undefined) return undefined;
  const normalized = String(value).trim().toUpperCase();
  if (!normalized) return undefined;
  const canonical = normalized.replace(/[\s-]+/g, '_');
  if (CONTACT_ROLE_SET.has(canonical)) return canonical;
  if (CONTACT_ROLE_SET.has(normalized)) return normalized;
  const alias = CONTACT_ROLE_ALIASES[canonical] ?? CONTACT_ROLE_ALIASES[normalized];
  if (alias && CONTACT_ROLE_SET.has(alias)) return alias;
  return undefined;
}

export function combinePhone(data: AnyRecord): string {
  const parts: string[] = [];
  const prefixRaw = data.phone_prefix ?? data.phone_code;
  if (prefixRaw) {
    const prefix = String(prefixRaw);
    parts.push(prefix.startsWith('+') ? prefix : `+${prefix}`);
  }
  if (data.phone_local) {
    parts.push(String(data.phone_local));
  }
  if (!parts.length && data.phone) {
    parts.push(String(data.phone));
  }
  return parts.join(' ').trim();
}

export function asRecord(value: unknown): AnyRecord {
  if (!value) return {};
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
      return {};
    }
    try {
      const parsed = JSON.parse(trimmed);
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? (parsed as AnyRecord) : {};
    } catch (err) {
      console.warn('[Companies] failed to parse JSON record', err);
      return {};
    }
  }
  if (typeof value === 'object' && !Array.isArray(value)) {
    return value as AnyRecord;
  }
  return {};
}

export function asArray<T = any>(value: unknown): T[] {
  if (!value) return [];
  if (Array.isArray(value)) return value as T[];
  if (typeof value === 'object') return Object.values(value as AnyRecord) as T[];
  return [];
}

export function mergeRecords(...records: Array<AnyRecord | null | undefined>): AnyRecord {
  const result: AnyRecord = {};
  for (const rec of records) {
    if (!rec) continue;
    for (const [key, value] of Object.entries(rec)) {
      if (value !== undefined) {
        result[key] = value;
      }
    }
  }
  return result;
}

export function extractAddress(raw: unknown): AddressForm {
  const data = asRecord(raw);
  return {
    country: data.country ?? data.country_code ?? undefined,
    city: data.city ?? undefined,
    street: data.street ?? data.address ?? undefined,
    zip: data.zip ?? data.postal_code ?? data.postcode ?? undefined,
    house: data.house ?? data.house_number ?? undefined,
    apartment: data.apartment ?? data.flat ?? data.unit ?? undefined,
    region: data.region ?? data.state ?? data.province ?? undefined,
  };
}

export function normalizeNumberString(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'number') return String(value);
  const str = String(value).trim();
  return str || '';
}

export function normalizeStringArray(value: unknown): string[] {
  if (!value) return [];
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter((item) => item.length > 0);
  }
  if (typeof value === 'string') {
    return value
      .split(',')
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
  }
  return [];
}

export function addressToPayload(address: AddressForm): AnyRecord | null {
  if (!address.country && !address.city && !address.street) return null;
  return {
    country: address.country || undefined,
    city: address.city || undefined,
    street: address.street || undefined,
    zip: address.zip || undefined,
    house: address.house || undefined,
    apartment: address.apartment || undefined,
    region: address.region || undefined,
  };
}

export function normalizeContacts(raw: unknown): ContactInfo[] {
  if (!raw) return [];
  if (Array.isArray(raw)) {
    return (raw as unknown[]).map((item, idx) => {
      const data = asRecord(item);
      const combinedPhone = combinePhone(data);
      const roleHint =
        (typeof data.role === 'string' && data.role) ||
        (typeof data.type === 'string' && data.type) ||
        (typeof data.position === 'string' && data.position) ||
        undefined;
      const normalizedRole = normalizeContactRole(roleHint);
      const roleHintLower = roleHint ? String(roleHint).trim().toLowerCase() : '';
      const isPrimary =
        data.is_primary !== undefined ? Boolean(data.is_primary) : roleHintLower === 'main' || idx === 0;
      return {
        role: normalizedRole,
        full_name: data.full_name ?? data.name ?? undefined,
        email: data.email ?? undefined,
        phone: combinedPhone || (data.phone ? String(data.phone) : undefined),
        is_primary: isPrimary,
        is_portal_user: data.is_portal_user ?? undefined,
      };
    });
  }
  const obj = asRecord(raw);
  return Object.entries(obj).map(([key, value], idx) => {
    const data = asRecord(value);
    const combinedPhone = combinePhone(data);
    const preferredRole =
      (typeof data.role === 'string' && data.role.trim()) ||
      (typeof data.type === 'string' && data.type.trim()) ||
      (typeof data.position === 'string' && data.position.trim()) ||
      key;
    const roleHintValue = preferredRole ?? key;
    const normalizedRole = normalizeContactRole(roleHintValue);
    const roleHintLower = String(roleHintValue ?? '').trim().toLowerCase();
    const isPrimary =
      data.is_primary !== undefined ? Boolean(data.is_primary) : roleHintLower === 'main' || idx === 0;
    return {
      role: normalizedRole,
      full_name: data.full_name ?? data.name ?? undefined,
      email: data.email ?? undefined,
      phone: combinedPhone || (data.phone ? String(data.phone) : undefined),
      is_primary: isPrimary,
      is_portal_user: data.is_portal_user ?? undefined,
    };
  });
}

