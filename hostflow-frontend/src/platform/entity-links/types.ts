/**
 * Entity Links — navigation into Entity Workspace (not field-bound).
 * Primary Entity Link = main path to full card; Secondary Links = other workspace hops in a row.
 */

export type EntityLinkRole = 'primary' | 'secondary'

export type EntityLinkDescriptor = {
  /** Stable link id within resource (e.g. candidate-card, order-number, avatar). */
  id: string
  role: EntityLinkRole
  /** Optional column/cell anchor when rendered inside DataTable. */
  fieldId?: string
  label?: string
}
