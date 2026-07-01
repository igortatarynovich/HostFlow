/**
 * Ruleset-related types
 */

export interface RulesetVersion {
  id: string;
  ruleset: Record<string, any>;
  comment?: string | null;
  is_active: boolean;
  created_at: string;
  created_by?: string | null;
  origin_version_id?: string | null;
}

export interface RulesetDiff {
  added: Record<string, any>;
  removed: Record<string, any>;
  modified: Record<string, { old: any; new: any }>;
}

export interface RulesetUsageResponse {
  version_id: string;
  used_by_documents: number;
  used_by_candidates: number;
  last_used_at?: string | null;
}

