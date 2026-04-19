import type { UserSavedView } from '../../../api/types'

export type QuickViewKey =
  | 'my_work_today'
  | 'overdue_next_action'
  | 'no_next_action'
  | 'docs_incomplete'
  | 'ready_for_handoff'
  | 'new_this_week'

export type QuickDocFilter = { key: string; label: string; statuses: string[]; active: boolean }

type CandidatesQuickViewsBarProps = {
  t: (key: string, options?: any) => string
  quickViewParam: string
  onApplyQuickViewFilters: (key: QuickViewKey) => void
  isFavoriteFilter: boolean | null
  onFavoriteFilterToggle: () => void
  quickDocFilters: QuickDocFilter[]
  quickFiltersExpanded: boolean
  onToggleQuickDocFilter: (statuses: string[], active: boolean) => void
  onQuickFiltersExpandedChange: (updater: (prev: boolean) => boolean) => void
  savedViews?: UserSavedView[]
  onApplySavedView?: (view: UserSavedView) => void
  onDeleteSavedView?: (id: string) => void
  /** Только `variant="rail"`: кнопка «Сохранить вид» (доступна при активных фильтрах / избранном / qv). */
  onOpenSaveView?: () => void
  viewSaveEnabled?: boolean
  /** `standalone` = full bar (legacy); `rail` = right rail (quick views dropdown + saved); `tableToolbar` = favorites + doc chips above the table. */
  variant?: 'rail' | 'standalone' | 'tableToolbar'
}

export function CandidatesQuickViewsBar({
  t,
  quickViewParam,
  onApplyQuickViewFilters,
  isFavoriteFilter,
  onFavoriteFilterToggle,
  quickDocFilters,
  quickFiltersExpanded,
  onToggleQuickDocFilter,
  onQuickFiltersExpandedChange,
  savedViews = [],
  onApplySavedView,
  onDeleteSavedView,
  onOpenSaveView,
  viewSaveEnabled = false,
  variant = 'rail',
}: CandidatesQuickViewsBarProps) {
  const QV_URL_KEYS = new Set<QuickViewKey>(['my_work_today', 'docs_incomplete', 'ready_for_handoff', 'new_this_week'])

  const presets: Array<[QuickViewKey, string]> = [
    ['my_work_today', t('app.candidates.views.quick_my_work_today', { defaultValue: 'My work today' })],
    ['docs_incomplete', t('app.candidates.views.quick_docs_incomplete', { defaultValue: 'Docs incomplete' })],
    ['ready_for_handoff', t('app.candidates.views.quick_ready_for_handoff', { defaultValue: 'Ready for handoff' })],
    ['new_this_week', t('app.candidates.views.quick_new_this_week', { defaultValue: 'New this week' })],
    ['no_next_action', t('app.candidates.views.quick_no_next_action', { defaultValue: 'No next action' })],
    ['overdue_next_action', t('app.candidates.views.quick_overdue_next_action', { defaultValue: 'Overdue next action' })],
  ]

  const chipScrollRow =
    'flex max-w-full flex-nowrap items-center gap-1.5 overflow-x-auto overflow-y-hidden py-0.5 [scrollbar-width:thin]'

  const presetBtn = (active: boolean) =>
    [
      'shrink-0 whitespace-nowrap rounded-md px-2 py-0.5 text-[11px] font-medium transition-colors',
      active
        ? 'bg-brand-600 text-white shadow-sm hover:bg-brand-700'
        : 'border border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50',
    ].join(' ')

  const shortcutBtn = (active: boolean) =>
    [
      'shrink-0 whitespace-nowrap rounded-lg border px-2.5 py-1.5 text-[11px] font-medium shadow-sm transition-colors',
      active
        ? 'border-brand-400 bg-brand-50 text-brand-900 hover:bg-brand-100/80'
        : 'border-slate-200/90 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50/90',
    ].join(' ')

  const sectionLabel =
    'shrink-0 whitespace-nowrap pr-1 text-[10px] font-semibold uppercase leading-none tracking-wide text-slate-500'

  if (variant === 'tableToolbar') {
    return (
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1.5 lg:justify-end">
        <button
          type="button"
          onClick={onFavoriteFilterToggle}
          className={shortcutBtn(isFavoriteFilter === true)}
        >
          {t('app.candidates.filters.only_favorites')}
        </button>
        {(quickFiltersExpanded ? quickDocFilters : quickDocFilters.slice(0, 3)).map((filter) => (
          <button
            key={filter.key}
            type="button"
            onClick={() => onToggleQuickDocFilter(filter.statuses, filter.active)}
            className={shortcutBtn(filter.active)}
          >
            {filter.label}
          </button>
        ))}
        {quickDocFilters.length > 3 && (
          <button
            type="button"
            className="shrink-0 whitespace-nowrap rounded-lg border border-slate-200/90 bg-white px-2.5 py-1.5 text-[11px] font-medium text-slate-600 shadow-sm hover:bg-slate-50"
            onClick={() => onQuickFiltersExpandedChange((prev) => !prev)}
          >
            {quickFiltersExpanded ? t('app.candidates.filters.quick_less') : t('app.candidates.filters.quick_more')}
          </button>
        )}
      </div>
    )
  }

  if (variant === 'standalone') {
    return (
      <div className="flex flex-col gap-1 px-2 py-1 sm:px-2.5">
        <div className="flex min-h-0 flex-col gap-1.5 lg:flex-row lg:items-stretch lg:gap-0">
          <div className="flex min-w-0 min-h-7 flex-1 items-center gap-2 lg:pr-4">
            <div className={sectionLabel}>{t('app.candidates.views.quick_views_title', { defaultValue: 'Quick Views' })}</div>
            <div className={chipScrollRow}>
              {presets.map(([key, label]) => {
                const active = quickViewParam === key
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => onApplyQuickViewFilters(key)}
                    className={presetBtn(active)}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
          </div>

          <div
            className="hidden lg:block w-px shrink-0 self-stretch bg-slate-100"
            aria-hidden
          />

          <div className="flex min-w-0 min-h-7 flex-1 items-center gap-2 lg:pl-4">
            <div className={sectionLabel}>
              {t('app.candidates.views.shortcut_filters_title', { defaultValue: 'Shortcuts' })}
            </div>
            <div className={chipScrollRow}>
              <button type="button" onClick={onFavoriteFilterToggle} className={shortcutBtn(isFavoriteFilter === true)}>
                {t('app.candidates.filters.only_favorites')}
              </button>
              {(quickFiltersExpanded ? quickDocFilters : quickDocFilters.slice(0, 3)).map((filter) => (
                <button
                  key={filter.key}
                  type="button"
                  onClick={() => onToggleQuickDocFilter(filter.statuses, filter.active)}
                  className={shortcutBtn(filter.active)}
                >
                  {filter.label}
                </button>
              ))}
              {quickDocFilters.length > 3 && (
                <button
                  type="button"
                  className="shrink-0 whitespace-nowrap rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-medium text-slate-600 hover:bg-slate-50"
                  onClick={() => onQuickFiltersExpandedChange((prev) => !prev)}
                >
                  {quickFiltersExpanded ? t('app.candidates.filters.quick_less') : t('app.candidates.filters.quick_more')}
                </button>
              )}
            </div>
          </div>
        </div>

        {savedViews.length > 0 && onApplySavedView && onDeleteSavedView ? (
          <div className="flex min-h-7 items-center gap-2 border-t border-slate-100/90 pt-1">
            <div className={sectionLabel}>
              {t('app.candidates.views.saved_inline_title', { defaultValue: 'My saved views' })}
            </div>
            <div className={chipScrollRow}>
              {savedViews.map((v) => (
                <span
                  key={v.id}
                  className="inline-flex shrink-0 items-center gap-0.5 rounded-md border border-slate-200 bg-white pl-1.5 pr-0.5 py-0.5 text-[11px]"
                >
                  <button
                    type="button"
                    className="max-w-[10rem] truncate text-left font-medium text-slate-800 hover:text-brand-700"
                    title={t('app.candidates.views.apply_title', { values: { name: v.name } })}
                    onClick={() => onApplySavedView(v)}
                  >
                    {v.name}
                  </button>
                  <button
                    type="button"
                    className="shrink-0 rounded px-0.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                    title={t('app.candidates.views.delete_title')}
                    aria-label={t('app.candidates.views.delete_title')}
                    onClick={() => onDeleteSavedView(v.id)}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    )
  }

  const railSelectValue = QV_URL_KEYS.has(quickViewParam as QuickViewKey) ? quickViewParam : ''

  return (
    <div className="space-y-2.5 rounded-lg border border-slate-200/80 bg-white/95 p-2.5 shadow-sm">
      <div className="space-y-1">
        <label htmlFor="candidates-rail-quick-view" className="block text-[10px] font-semibold uppercase tracking-wide text-slate-500">
          {t('app.candidates.views.quick_views_title', { defaultValue: 'Quick Views' })}
        </label>
        <select
          id="candidates-rail-quick-view"
          className="input w-full rounded-lg border-slate-200/90 py-2 text-sm text-slate-800 shadow-sm"
          value={railSelectValue}
          aria-label={t('app.candidates.views.quick_views_title', { defaultValue: 'Quick Views' })}
          onChange={(e) => {
            const key = e.target.value as QuickViewKey | ''
            if (!key) return
            onApplyQuickViewFilters(key)
          }}
        >
          <option value="">{t('app.candidates.views.quick_views_placeholder', { defaultValue: 'Quick view…' })}</option>
          {presets.map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {onOpenSaveView ? (
        <button
          type="button"
          disabled={!viewSaveEnabled}
          onClick={onOpenSaveView}
          className="btn-secondary w-full justify-center rounded-lg py-2 text-xs font-medium shadow-sm disabled:cursor-not-allowed disabled:opacity-50"
          title={
            viewSaveEnabled
              ? undefined
              : t('app.candidates.views.save_needs_filters_hint', {
                  defaultValue: 'Apply at least one filter to save this view.',
                })
          }
        >
          {t('app.candidates.views.save_action')}
        </button>
      ) : null}

      {savedViews.length > 0 && onApplySavedView && onDeleteSavedView ? (
        <div className="border-t border-slate-200/80 pt-2">
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            {t('app.candidates.views.saved_inline_title', { defaultValue: 'My saved views' })}
          </div>
          <div className="flex max-h-[5.5rem] flex-wrap gap-1 overflow-y-auto [scrollbar-width:thin]">
            {savedViews.map((v) => (
              <span
                key={v.id}
                className="inline-flex max-w-full items-center gap-0.5 rounded-lg border border-slate-200/90 bg-slate-50/90 py-0.5 pl-1.5 pr-0.5 text-[11px] shadow-sm"
              >
                <button
                  type="button"
                  className="max-w-[9rem] truncate text-left font-medium text-slate-800 hover:text-brand-700"
                  title={t('app.candidates.views.apply_title', { values: { name: v.name } })}
                  onClick={() => onApplySavedView(v)}
                >
                  {v.name}
                </button>
                <button
                  type="button"
                  className="shrink-0 rounded px-0.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                  title={t('app.candidates.views.delete_title')}
                  aria-label={t('app.candidates.views.delete_title')}
                  onClick={() => onDeleteSavedView(v.id)}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
