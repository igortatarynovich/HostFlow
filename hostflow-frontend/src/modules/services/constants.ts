/**
 * Constants for services module
 */

import type { ServiceItemStatus, ServiceOrderStatus, ServiceScheduleStatus } from '../../api/types';

export const ORDER_STATUSES: ServiceOrderStatus[] = [
  'draft',
  'confirmed',
  'in_progress',
  'on_hold',
  'completed',
  'cancelled',
];

export const SCHEDULE_STATUSES: ServiceScheduleStatus[] = [
  'reserved',
  'confirmed',
  'completed',
  'no_show',
  'cancelled',
];

export const ITEM_STATUSES: ServiceItemStatus[] = ['pending', 'scheduled', 'in_progress', 'delivered', 'cancelled'];

export const DOCUMENT_STATUSES = ['approved', 'verified', 'pending_validation'] as const;

