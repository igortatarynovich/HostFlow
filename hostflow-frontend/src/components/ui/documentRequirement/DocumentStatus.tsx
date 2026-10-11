import { StatusBadge } from '../StatusBadge'
import type { StatusBadgeSemantic } from '../statusBadgeSemantics'

export type DocumentStatusKind =
  | 'missing'
  | 'uploaded'
  | 'review'
  | 'approved'
  | 'rejected'
  | 'ordered'
  | 'received'
  | 'absent'

const SEMANTIC: Record<DocumentStatusKind, StatusBadgeSemantic> = {
  missing: 'neutral',
  uploaded: 'info',
  review: 'warning',
  approved: 'success',
  rejected: 'danger',
  ordered: 'info',
  received: 'success',
  absent: 'neutral',
}

export function DocumentStatus({ kind, label }: { kind: DocumentStatusKind; label: string }) {
  return <StatusBadge size="sm" shape="pill" semantic={SEMANTIC[kind]} label={label} />
}
