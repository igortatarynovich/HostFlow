/**
 * Constants for tenants module
 */

import type { SeatRequest, TenantModuleSettings, TenantStatus, TenantType } from '../../api/types';

export const STATUS_BADGE: Record<TenantStatus, string> = {
  active: 'bg-emerald-100 text-emerald-800',
  suspended: 'bg-rose-100 text-rose-800',
  trial: 'bg-amber-100 text-amber-800',
};

export const TYPE_BADGE: Record<TenantType, string> = {
  platform: 'bg-blue-100 text-blue-800',
  agency: 'bg-purple-100 text-purple-800',
  company: 'bg-slate-100 text-slate-800',
};

export const MODULE_LABELS: Record<keyof TenantModuleSettings, string> = {
  candidates: 'app.platform.tenants.modules.items.candidates',
  companies: 'app.platform.tenants.modules.items.companies',
  vacancies: 'app.platform.tenants.modules.items.vacancies',
  documents: 'app.platform.tenants.modules.items.documents',
  leads: 'app.platform.tenants.modules.items.leads',
  services: 'app.platform.tenants.modules.items.services',
  client_portal: 'app.platform.tenants.modules.items.client_portal',
  hr: 'app.platform.tenants.modules.items.hr',
};

export const SEAT_STATUS_BADGE: Record<SeatRequest['status'], string> = {
  pending: 'bg-amber-100 text-amber-800',
  approved: 'bg-emerald-100 text-emerald-800',
  rejected: 'bg-rose-100 text-rose-800',
};

