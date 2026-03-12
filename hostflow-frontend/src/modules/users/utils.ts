/**
 * Utility functions for users module
 */

import type { Company } from '../../api/types';

export function normalizeList<T>(value: any): T[] {
  if (Array.isArray(value)) return value as T[];
  if (value && Array.isArray(value.items)) return value.items as T[];
  return [];
}

export function parseCompanies(data: any): Company[] {
  const items = normalizeList<any>(data);
  const result: Company[] = [];
  for (const item of items) {
    const id = item?.id || item?.uuid || item?.company_id;
    if (!id) continue;
    result.push({
      id,
      name: item?.name || item?.title || item?.label || id,
      country: item?.country ?? null,
      city: item?.city ?? null,
    });
  }
  return result;
}

export function extractErrorDetail(err: unknown): string | null {
  const responseDetail = (err as any)?.response?.data?.detail;
  if (!responseDetail) return null;
  if (typeof responseDetail === 'string') return responseDetail;
  if (Array.isArray(responseDetail)) {
    const messages = responseDetail
      .map((item) => {
        if (!item) return null;
        if (typeof item === 'string') return item;
        if (typeof item === 'object' && 'msg' in item) return String(item.msg);
        return JSON.stringify(item);
      })
      .filter(Boolean);
    return messages.length ? messages.join('; ') : null;
  }
  if (typeof responseDetail === 'object') {
    if ('msg' in responseDetail) return String(responseDetail.msg);
    return JSON.stringify(responseDetail);
  }
  return String(responseDetail);
}

