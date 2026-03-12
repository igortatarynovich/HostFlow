/**
 * Type definitions for candidates module
 */

import type { Candidate } from '../../api/types';

export type CandidateOpsMode = 'in_work' | 'later' | 'no_reply_needed' | 'escalated';

export type DateRangeFilter = { from: string | null; to: string | null };

export type ColumnTextFilters = {
  name: string;
  email: string;
  phone: string;
  citizenship: string;
  short: string;
};

export type DocsMeta = {
  readinessState: string;
  readinessLabelKey: string;
  readinessClass: string;
  readinessKey: string;
  rank: number;
  orderDate: string | null;
  orderTs: number;
  validFrom: string | null;
  validTs: number;
  hasFiles: boolean;
  isOrdered: boolean;
};

export type CandidateExtraNormalized = {
  citizenship: string | null;
  preferredContact: string | null;
  firstContactAt: string | null;
  inPoland: boolean | null;
  polandStayBasis: string | null;
  trailerTypes: string[];
  opsMode: CandidateOpsMode | null;
};

export type UICandidate = Candidate & {
  manager_name?: string | null;
  manager_short?: string | null;
};

export type AugmentedCandidate = UICandidate & {
  __docsMeta: DocsMeta;
  __extra: CandidateExtraNormalized;
  __reasonCodes: string[];
  __reasonFallbackLabels: string[];
};

export type ManagerItem = { id: string; name: string };

// API may return either a plain array or a paginated object
export type ListResp = { items?: UICandidate[]; total?: number } | UICandidate[];

export type CandidateFilterSnapshot = {
  stage: string[];
  vacancy: string[];
  manager: string[];
  statusReasons: string[];
  tags: string[];
  docsStatus: string[];
  docsOrdered: string[];
  createdRange: DateRangeFilter;
  firstContactRange: DateRangeFilter;
  docsValidRange: DateRangeFilter;
  preferredChannels: string[];
  polandPresence: string[];
  polandBasis: string[];
  trailerTypes: string[];
  opsModes: CandidateOpsMode[];
  docsHasFiles: string[];
  query: string;
  textFilters: ColumnTextFilters;
  isFavorite: boolean | null;
};

export type CandidateListCacheEntry = { items: UICandidate[]; total: number; timestamp: number };

export type SortKey =
  | 'created_at'
  | 'name'
  | 'email'
  | 'phone'
  | 'citizenship'
  | 'vacancy'
  | 'short_id'
  | 'manager'
  | 'stage'
  | 'reasons'
  | 'docs_status'
  | 'docs_ordered_at'
  | 'docs_valid_from'
  | 'docs_has_files'
  | 'first_contact'
  | 'preferred_channel'
  | 'in_poland'
  | 'poland_basis'
  | 'trailer_types';

export function makeEmptyTextFilters(): ColumnTextFilters {
  return {
    name: '',
    email: '',
    phone: '',
    citizenship: '',
    short: '',
  };
}
