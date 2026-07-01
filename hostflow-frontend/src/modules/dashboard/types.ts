/**
 * Type definitions for dashboard module
 */

export type ListResp<T> = { items: T[]; total?: number } | T[];

export type NamedCount = { key: string; label: string; count: number };

export type StageBreakdownItem = NamedCount & { by_stage?: Record<string, number> };

export type CandidateSnapshot = {
  id: string;
  stage: string | null;
  stage_label: string | null;
  company: string | null;
  company_id?: string | null;
  vacancy: string | null;
  vacancy_id?: string | null;
  source: string | null;
  citizenship: string | null;
  country: string | null;
  manager?: string | null;
  manager_id?: string | null;
  manager_name?: string | null;
  manager_short?: string | null;
  /**
   * Phase 2.6.G-5 Stage F — canonical assignee columns alongside the
   * legacy ``manager*`` ones. The backend joins ``users`` via
   * ``Candidate.recruiter_id`` and serialises both triplets; declaring
   * them here lets dashboard drill-down helpers read the canonical id
   * without falling through to ``any``.
   */
  recruiter_id?: string | null;
  recruiter_name?: string | null;
  recruiter_short?: string | null;
  status_reason_codes?: string[];
  status_reason_labels?: string[];
  reason_stage?: string | null;
  reason_stage_label?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type CandidateSlicesResponse = {
  period: { from: string | null; to: string | null };
  by: 'created' | 'updated';
  total: number;
  companies_total?: number;
  vacancies_total?: number;
  stages: NamedCount[];
  companies: StageBreakdownItem[];
  vacancies: StageBreakdownItem[];
  sources: NamedCount[];
  citizenships: NamedCount[];
  countries: NamedCount[];
  reasons: {
    rejected: NamedCount[];
    declined: NamedCount[];
  };
  snapshot: CandidateSnapshot[];
};

export type PivotDimension = 'stage' | 'company' | 'vacancy' | 'source' | 'manager' | 'citizenship' | 'country' | 'reason';

export type QuickRange = '7d' | '30d' | '90d' | 'ytd' | 'all';

export type LoadOverrides = {
  from?: string;
  to?: string;
  field?: 'created' | 'updated';
  vacancyId?: string | null;
  companyId?: string | null;
  managerId?: string | null;
  candidateId?: string | null;
  stages?: string[];
  compare?: boolean;
};

export type DashboardWidgetId =
  | 'handoff'
  | 'contact'
  | 'documents'
  | 'managerLoad'
  | 'countries'
  | 'stageStack'
  | 'globalStats'
  | 'stages'
  | 'reasons'
  | 'companies'
  | 'vacancies'
  | 'sources'
  | 'docsRisk'
  | 'velocity'
  | 'pivot'
  | 'pivotChart';

/** Full list for the “Widgets” picker (defaults are a subset). */
export const DASHBOARD_WIDGET_CATALOG: DashboardWidgetId[] = [
  'pivot',
  'pivotChart',
  'stageStack',
  'globalStats',
  'handoff',
  'contact',
  'documents',
  'managerLoad',
  'countries',
  'stages',
  'reasons',
  'companies',
  'vacancies',
  'sources',
  'docsRisk',
  'velocity',
];

/** Default: only the raw pivot table; legacy widgets stay available via Configure. */
export const DEFAULT_VISIBLE_WIDGETS: DashboardWidgetId[] = ['pivot'];

export type DashboardFilterId =
  | 'period'
  | 'dateRange'
  | 'dateField'
  | 'vacancy'
  | 'company'
  | 'manager'
  | 'candidate'
  | 'stages'
  | 'compare'
  | 'presets'
  | 'widgets';

export const DEFAULT_VISIBLE_FILTERS: DashboardFilterId[] = [
  'period',
  'dateRange',
  'dateField',
  'vacancy',
  'company',
  'manager',
  'candidate',
  'compare',
  'presets',
  'widgets',
];
// 'stages' filter excluded from defaults - low value, available via Configure

export type DashboardPreset = {
  dateFrom: string;
  dateTo: string;
  activeRange: string;
  dateField: 'created' | 'updated';
  vacancyFilter: string;
  companyFilter: string;
  managerFilter: string;
  candidateFilter?: string;
  stagesFilter: string[];
  compareWithPrevious: boolean;
  visibleWidgets?: string[];
  visibleFilters?: string[];
  pivotPrimary?: string;
  pivotSecondary?: string;
};

export type StageLabelConfig = {
  hired: string[];
  rejected: string[];
  declined: string[];
  /** Late hiring / HR paperwork (excluded from «hired» KPI). */
  employment_pending?: string[];
};

export type StageOutcome = 'hired' | 'rejected' | 'declined' | 'pipeline';

