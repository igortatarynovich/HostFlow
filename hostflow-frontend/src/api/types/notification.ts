/**
 * Notification and reminder-related types
 */

export interface NotificationItem {
  id: string;
  event_type: string;
  channel: string;
  payload: Record<string, any>;
  entity_type?: string | null;
  entity_id?: string | null;
  is_read: boolean;
  created_at: string;
  delivered_at?: string | null;
  read_at?: string | null;
}

export interface NotificationListResponse {
  items: NotificationItem[];
}

export type ReminderStatus = 'new' | 'pending' | 'sent' | 'overdue' | 'done' | 'cancelled';

export interface ReminderRecord {
  id: string;
  title?: string | null;
  description?: string | null;
  type: string;
  entity_type: string;
  entity_id: string;
  owner_id?: string | null;
  assignee_id?: string | null;
  priority?: string | null;
  channel?: string | null;
  status: ReminderStatus;
  due_at: string;
  remind_at?: string | null;
  duration_minutes?: number | null;
  source?: string | null;
  snoozed_until?: string | null;
  completed_at?: string | null;
  recurrence_json?: Record<string, any> | null;
  payload: Record<string, any>;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ReminderListResponse {
  items: ReminderRecord[];
}

