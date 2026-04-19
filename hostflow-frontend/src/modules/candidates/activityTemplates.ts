/**
 * Activity (reminder) templates for bulk create and quick-select.
 * type is sent to API; defaultTitle is used as placeholder/initial title.
 */
export type ActivityTemplate = {
  key: string
  type: string
  defaultTitle: string
  defaultOffsetMinutes: number
}

export const ACTIVITY_TEMPLATES: ActivityTemplate[] = [
  { key: 'call', type: 'call', defaultTitle: 'Call', defaultOffsetMinutes: 15 },
  { key: 'email', type: 'email', defaultTitle: 'Send email', defaultOffsetMinutes: 60 },
  { key: 'document_request', type: 'document_request', defaultTitle: 'Request document', defaultOffsetMinutes: 120 },
  { key: 'follow_up', type: 'follow_up', defaultTitle: 'Follow up', defaultOffsetMinutes: 60 },
]

