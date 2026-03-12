/**
 * Constants for candidate card module
 */

import type { ServiceItemStatus, ServiceOrderStatus } from '../../api/types';

export const ADDRESS_KEYS = ['country', 'city', 'street', 'house', 'apt', 'zip'] as const;
export const UUID_RE = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;
export const CREATE_FIELDS = new Set([
  'first_name',
  'last_name',
  'email',
  'phone',
  'phone_country_code',
  'languages',
  'stage',
  'manager_id',
  'company_id',
  'vacancy_id',
  'status_reason',
]);
export const PATCH_AFTER_CREATE_FIELDS = new Set([
  'address',
  'city',
  'country_code',
  'birth_date',
  'note',
  'extra',
  'status_reason',
]);
export const MAX_EMPLOYMENTS = 3;
export const SERVICE_ORDER_STATUSES: ServiceOrderStatus[] = [
  'draft',
  'quoted',
  'approved',
  'scheduled',
  'in_progress',
  'delivered',
  'cancelled',
  'refunded',
];
export const SERVICE_ITEM_STATUSES: ServiceItemStatus[] = [
  'pending',
  'scheduled',
  'in_progress',
  'delivered',
  'cancelled',
];
export const POLAND_BASIS_VALUES = [
  '',
  'visa_d',
  'visa_c',
  'karta_pobytu',
  'eu_citizen',
  'waiting_for_trc',
  'other',
];

