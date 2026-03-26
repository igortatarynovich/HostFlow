/**
 * Utility functions for services module
 */

import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { ORDER_STATUSES, SERVICES_BILLING_URL_FILTER_SET } from './constants';

const ORDER_STATUS_SET = new Set<string>(ORDER_STATUSES);

const currency = new Intl.NumberFormat('pl-PL', {
  style: 'currency',
  currency: 'PLN',
});

export function formatAmount(value: number | null | undefined, fallback = '-'): string {
  if (value == null || Number.isNaN(value)) {
    return fallback;
  }
  try {
    return currency.format(value);
  } catch (err) {
    return value.toFixed(2);
  }
}

export type ServicesWorkspaceTab = 'overview' | 'orders' | 'catalog' | 'analytics' | 'billing';

function buildServicesWorkspaceUrl(opts: {
  tab: ServicesWorkspaceTab;
  companyId?: string | null;
  orderId?: string | null;
  status?: string | null;
  candidateId?: string | null;
  vacancyId?: string | null;
  billingFilter?: string | null;
}): string {
  const qs = new URLSearchParams();
  const ordersStandalone = opts.tab === 'orders';
  if (!ordersStandalone) {
    qs.set('tab', opts.tab);
  }
  const c = opts.companyId != null ? String(opts.companyId).trim() : '';
  if (c) qs.set('company_id', c);
  const oid = opts.orderId != null ? String(opts.orderId).trim() : '';
  if (oid) qs.set('order_id', oid);
  const st = opts.status != null ? String(opts.status).trim() : '';
  if (st && ORDER_STATUS_SET.has(st)) qs.set('status', st);
  const cand = opts.candidateId != null ? String(opts.candidateId).trim() : '';
  if (cand) qs.set('candidate_id', cand);
  else {
    const vac = opts.vacancyId != null ? String(opts.vacancyId).trim() : '';
    if (vac) qs.set('vacancy_id', vac);
  }
  const bf = opts.billingFilter != null ? String(opts.billingFilter).trim() : '';
  if (bf && SERVICES_BILLING_URL_FILTER_SET.has(bf) && bf !== 'all') qs.set('billing_filter', bf);
  const path = ordersStandalone ? CRM_APP_PATHS.orders : CRM_APP_PATHS.services;
  const q = qs.toString();
  return q ? `${path}?${q}` : path;
}

/** Any Services tab with optional scope / order / status (matches ServicesPage query params). */
export function servicesWorkspacePath(
  tab: ServicesWorkspaceTab,
  opts?: {
    companyId?: string | null;
    orderId?: string | null;
    status?: string | null;
    candidateId?: string | null;
    vacancyId?: string | null;
    billingFilter?: string | null;
  },
): string {
  return buildServicesWorkspaceUrl({ tab, ...opts });
}

/** Deep link to Services workspace (Orders tab) for a service order; query keys match ServicesPage. */
export function serviceOrderWorkspacePath(orderId: string, companyId?: string | null): string {
  return buildServicesWorkspaceUrl({ tab: 'orders', orderId, companyId });
}

/** Deep link to Services → Orders with optional company scope and order status filter (matches ServicesPage `status` query). */
export function servicesOrdersTabPath(opts?: {
  companyId?: string | null;
  status?: string | null;
  candidateId?: string | null;
  vacancyId?: string | null;
}): string {
  return buildServicesWorkspaceUrl({ tab: 'orders', ...opts });
}

/** Money still owed on an invoice (non-negative). */
export function invoiceOutstandingAmount(total: number | null | undefined, paid: number | null | undefined): number {
  return Math.max(0, Number(total ?? 0) - Number(paid ?? 0));
}

const DAY_MS = 24 * 60 * 60 * 1000;

function startOfDay(d: Date): Date {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

/**
 * Whole calendar days past due_date when there is still outstanding balance.
 * Returns null if not past due or nothing owed.
 */
export function invoiceDaysPastDue(
  dueDateIso: string | null | undefined,
  outstanding: number,
): number | null {
  if (outstanding <= 0 || !dueDateIso) return null;
  const due = new Date(dueDateIso);
  if (Number.isNaN(due.getTime())) return null;
  const today = startOfDay(new Date());
  const d0 = startOfDay(due);
  const diff = Math.floor((today.getTime() - d0.getTime()) / DAY_MS);
  return diff > 0 ? diff : null;
}

type OrderNextItemLike = {
  status: string;
  schedules?: unknown[] | null;
  service?: { requires_schedule?: boolean } | null;
};

type OrderNextOrderLike = {
  status: string;
  items: OrderNextItemLike[];
};

type OrderNextInvoiceLike = {
  invoice_id?: string;
  status?: string;
  total_amount?: number;
  paid_amount?: number;
};

export type ServiceOrderNextAction =
  | { key: 'cancelled' }
  | { key: 'draft' }
  | { key: 'on_hold' }
  | { key: 'invoice_needed' }
  | { key: 'collect_payment' }
  | { key: 'closed' }
  | { key: 'schedule_slots' }
  | { key: 'deliver_lines'; count: number }
  | { key: 'mark_completed' }
  | { key: 'review' };

/**
 * Heuristic "next step" for service order list/detail (fulfillment + billing), without async summary.
 */
export function resolveServiceOrderNextAction(
  order: OrderNextOrderLike,
  inv: OrderNextInvoiceLike | null | undefined,
): ServiceOrderNextAction {
  const st = String(order.status || '').trim();
  const invOutstanding = inv?.invoice_id
    ? invoiceOutstandingAmount(inv.total_amount, inv.paid_amount)
    : 0;
  const invStatus = String(inv?.status || '').toLowerCase();

  if (st === 'cancelled') return { key: 'cancelled' };
  if (st === 'draft') return { key: 'draft' };
  if (st === 'on_hold') return { key: 'on_hold' };

  const activeItems = (order.items || []).filter((i) => i.status !== 'cancelled');
  const undelivered = activeItems.filter((i) => i.status !== 'delivered').length;
  const needsSchedule = activeItems.some(
    (i) =>
      i.status !== 'delivered' &&
      Boolean(i.service?.requires_schedule) &&
      (!Array.isArray(i.schedules) || i.schedules.length === 0),
  );

  if (st === 'completed') {
    if (!inv?.invoice_id) return { key: 'invoice_needed' };
    if (invOutstanding > 0 && invStatus !== 'paid' && invStatus !== 'cancelled') {
      return { key: 'collect_payment' };
    }
    return { key: 'closed' };
  }

  if (needsSchedule) return { key: 'schedule_slots' };
  if (undelivered > 0) return { key: 'deliver_lines', count: undelivered };

  if (st === 'confirmed' || st === 'in_progress') {
    return { key: 'mark_completed' };
  }

  return { key: 'review' };
}
