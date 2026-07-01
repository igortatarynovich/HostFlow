import type { ReminderRecord } from '../../api/types/notification'

/** NBA groups that support inline “Do now” → bulk activities (first batch of matching leads/candidates). */
export const NBA_QUICK_REMINDER_GROUP_IDS = new Set([
  'leads_no_next_action',
  'leads_next_overdue',
  /** §2.12 funnel insights → same lead list as chip link; bulk follow-up (Suggested actions v0). */
  'leads_funnel_weak_step',
  'leads_funnel_slow_stage',
  'candidates_no_next_action',
  'candidates_next_overdue',
])

/** NBA: “Process batch” → POST /leads/bulk/process-new-queue (Team+; Meta status=new). */
export const NBA_QUICK_PROCESS_NEW_GROUP_IDS = new Set(['leads_new_unprocessed'])

/** Reminder statuses that still need action (candidate IDs for overdue NBA batch). */
export const NBA_CANDIDATE_OVERDUE_REMINDER_STATUSES: ReminderRecord['status'][] = [
  'new',
  'pending',
  'sent',
  'overdue',
]

export const NBA_QUICK_BATCH_LIMIT = 50
