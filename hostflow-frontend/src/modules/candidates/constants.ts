/**
 * Constants for candidates module
 */

/** Правый work-panel: ширина колонки грида и `max-width` aside (должны совпадать). */
export const CANDIDATES_WORK_PANEL_RAIL_WIDTH_PX = 440

export const DOC_READINESS_META: Record<string, { labelKey: string; className: string }> = {
  pending: { labelKey: 'app.candidates.docs.readiness.pending', className: 'bg-gray-100 text-gray-600' },
  requested: { labelKey: 'app.candidates.docs.readiness.requested', className: 'bg-blue-50 text-blue-700' },
  ordered: { labelKey: 'app.candidates.docs.readiness.ordered', className: 'bg-indigo-50 text-indigo-700' },
  in_progress: { labelKey: 'app.candidates.docs.readiness.in_progress', className: 'bg-sky-50 text-sky-700' },
  awaiting_review: { labelKey: 'app.candidates.docs.readiness.awaiting_review', className: 'bg-amber-50 text-amber-700' },
  ready: { labelKey: 'app.candidates.docs.readiness.ready', className: 'bg-green-50 text-green-700' },
  problem: { labelKey: 'app.candidates.docs.readiness.problem', className: 'bg-rose-50 text-rose-700' },
};

export const DOC_READINESS_ORDER: Record<string, number> = {
  problem: 6,
  awaiting_review: 5,
  in_progress: 4,
  ordered: 3,
  requested: 2,
  pending: 1,
  ready: 0,
};

export const DOC_ORDER_FILTERS: Array<{ value: string; labelKey: string }> = [
  { value: 'ordered', labelKey: 'app.candidates.docs.order_filter.ordered' },
  { value: 'not_ordered', labelKey: 'app.candidates.docs.order_filter.not_ordered' },
];

export const QUICK_DOC_STATUS_SETS: Record<string, string[]> = {
  ready: ['ready'],
  attention: ['problem', 'awaiting_review', 'in_progress'],
  pending: ['pending', 'requested', 'ordered'],
};

/** Навигационные quick views (не фильтры списка): единый источник для хука и drill-down ссылок. */
export const CANDIDATES_QUICK_VIEW_NAV_PATHS = {
  no_next_action: '/app/candidates/no-next-action',
  overdue_next_action: '/app/tasks?tab=tasks&t_status=active&t_entity=candidate',
} as const

export const FILTER_STORAGE_KEY = 'cand.filters';
export const VISIBLE_COLS_STORAGE_KEY = 'cand.visibleCols';
export const COLUMN_WIDTHS_STORAGE_KEY = 'cand.columnWidths';
export const COLUMN_ORDER_STORAGE_KEY = 'cand.columnOrder';
export const CANDIDATE_LIST_STORAGE_KEY = 'cand.list.cache';
export const CANDIDATE_CACHE_TTL_MS = 24 * 60 * 60 * 1000; // keep cached list for a day between visits
export const SCROLL_STATE_KEY = 'cand.scroll';
export const SCROLL_STATE_TTL_MS = 24 * 60 * 60 * 1000; // keep last position for a day
export const APP_SCROLL_SELECTOR = 'main.flex-1';
export const RESTORE_SCROLL_MAX_ATTEMPTS = 10;

export const EMPTY_OPTION_VALUE = '__empty__';

export const SORTABLE_KEYS = [
  'created_at',
  'name',
  'email',
  'phone',
  'citizenship',
  'vacancy',
  'short_id',
  'manager',
  'stage',
  'risk_score',
  'reasons',
  'is_favorite',
  'tags',
  'docs_status',
  'docs_ordered_at',
  'docs_valid_from',
  'docs_has_files',
  'first_contact',
  'preferred_channel',
  'in_poland',
  'poland_basis',
  'trailer_types',
] as const;

export function isSortKey(value: any): value is typeof SORTABLE_KEYS[number] {
  return typeof value === 'string' && SORTABLE_KEYS.includes(value as any);
}

export const DEFAULT_VISIBLE_COLS: Record<string, boolean> = {
  name: true,
  email: false,
  phone: false,
  citizenship: false,
  vacancy: true,
  short: false,
  manager: true,
  stage: true,
  /** Phase C: optional column — enable via column picker (Overview / digests still surface risk). */
  risk: false,
  created: false,
  firstContact: false,
  preferredChannel: false,
  inPoland: false,
  polandBasis: false,
  trailerTypes: false,
  /** Статусы/причины — быстрый сигнал «что не так». */
  reasons: true,
  is_favorite: false,
  docsStatus: true,
  docsOrdered: false,
  docsValid: false,
  docsFiles: false,
};

// Порядок колонок по умолчанию (только видимые)
export const DEFAULT_COLUMN_ORDER: string[] = [
  // Operational compact schema: scan stage → docs → role fit → assignee; risk is opt-in.
  'name',
  'stage',
  'docsStatus',
  'reasons',
  'vacancy',
  'manager',
  'risk',
  // Optional operational doc signals (kept for power users).
  'docsOrdered',
  'docsValid',
  'docsFiles',
];
