/**
 * Type definitions for users module
 */

export type DetailTab = 'overview' | 'companies' | 'audit';

export interface AuditState {
  loading: boolean;
  entries: import('../../api/types').UserAuditEntry[];
  error: string | null;
}

export const EMPTY_AUDIT: AuditState = { loading: false, entries: [], error: null };

