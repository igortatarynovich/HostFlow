/**
 * Utility functions for tenants module
 */

import { isAxiosError } from 'axios';
import type { TenantLicense, TenantLicenseInput, TenantLicensePatchInput } from '../../api/types';

export type LicenseFormState = {
  plan: string;
  max_recruiters: string;
  max_supervisors: string;
  max_client_managers: string;
  max_viewers: string;
  max_storage_gb: string;
  max_companies: string;
  expires_at: string;
  auto_renew: boolean;
  notes: string;
};

export const DEFAULT_LICENSE: LicenseFormState = {
  plan: '',
  max_recruiters: '0',
  max_supervisors: '0',
  max_client_managers: '0',
  max_viewers: '0',
  max_storage_gb: '0',
  max_companies: '0',
  expires_at: '',
  auto_renew: true,
  notes: '',
};

export function toLicenseForm(license?: TenantLicense | null): LicenseFormState {
  if (!license) return { ...DEFAULT_LICENSE };
  return {
    plan: license.plan ?? '',
    max_recruiters: String(license.max_recruiters ?? 0),
    max_supervisors: String(license.max_supervisors ?? 0),
    max_client_managers: String(license.max_client_managers ?? 0),
    max_viewers: String(license.max_viewers ?? 0),
    max_storage_gb: String(license.max_storage_gb ?? 0),
    max_companies: String(license.max_companies ?? 0),
    expires_at: license.expires_at ?? '',
    auto_renew: Boolean(license.auto_renew),
    notes: license.notes ?? '',
  };
}

export function parseNumber(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function licenseFormToPatch(form: LicenseFormState): TenantLicensePatchInput {
  return {
    plan: form.plan.trim() || undefined,
    max_recruiters: parseNumber(form.max_recruiters),
    max_supervisors: parseNumber(form.max_supervisors),
    max_client_managers: parseNumber(form.max_client_managers),
    max_viewers: parseNumber(form.max_viewers),
    max_storage_gb: parseNumber(form.max_storage_gb),
    max_companies: parseNumber(form.max_companies),
    expires_at: form.expires_at || null,
    auto_renew: Boolean(form.auto_renew),
    notes: form.notes?.trim() || null,
  };
}

export function licenseFormToInput(form: LicenseFormState): TenantLicenseInput {
  return {
    plan: form.plan.trim(),
    max_recruiters: parseNumber(form.max_recruiters),
    max_supervisors: parseNumber(form.max_supervisors),
    max_client_managers: parseNumber(form.max_client_managers),
    max_viewers: parseNumber(form.max_viewers),
    max_storage_gb: parseNumber(form.max_storage_gb),
    max_companies: parseNumber(form.max_companies),
    expires_at: form.expires_at || null,
    auto_renew: Boolean(form.auto_renew),
    notes: form.notes?.trim() || null,
  };
}

export function formatValues(values: Record<string, string | number>) {
  return {
    values: Object.fromEntries(Object.entries(values).map(([key, value]) => [key, String(value)])),
  };
}

export function formatErrorMessage(err: unknown, fallback: string): string {
  if (isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim().length > 0) return detail;
    if (typeof err.message === 'string') return err.message;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

