import type { ReactNode, RefObject } from 'react'
import { Link } from 'react-router-dom'
import { toCSV } from '../candidateUtils'
import type { AugmentedCandidate, CandidateOpsMode } from '../types'

type QuickViewKey = 'my_work_today' | 'docs_incomplete' | 'ready_for_handoff' | 'new_this_week' | 'no_next_action' | 'overdue_next_action'

type QuickDocFilter = { key: string; label: string; statuses: string[]; active: boolean }

type CandidatesFiltersActionsPanelProps = {
  t: (key: string, options?: any) => string
  searchRef: RefObject<HTMLInputElement | null>
  q: string
  onQChange: (value: string) => void
  handoffStatusFilter: string
  onHandoffStatusFilterChange: (value: string) => void
  contactAttemptsFilter: string
  onContactAttemptsFilterChange: (value: string) => void
  opsModeFilter: CandidateOpsMode[]
  onOpsModeFilterChange: (value: CandidateOpsMode[]) => void
  opsModeOptions: Array<{ value: CandidateOpsMode; label: string }>
  opsModeLabelMap: Record<string, string>
  viewToggle: ReactNode
  secondaryBtn: string
  onRefresh: () => void
  loading: boolean
  actionsMenuRef: RefObject<HTMLDivElement | null>
  actionsMenuOpen: boolean
  onActionsMenuOpenChange: (value: boolean | ((prev: boolean) => boolean)) => void
  displayedItems: any[]
  resolveManagerLabel: (candidate: AugmentedCandidate) => string | null
  onResetFilters: () => void
  hasFilterBadges: boolean
  onOpenSaveView: () => void
  columnToggleKeys: readonly string[]
  visibleCols: Record<string, boolean>
  onVisibleColsChange: (value: Record<string, boolean>) => void
  visibleColsStorageKey: string
  columnLabelMap: Record<string, string>
  canManage: boolean
  quickViewParam: string
  onQuickViewNavigate: (path: string) => void
  onApplyQuickViewFilters: (key: QuickViewKey) => void
  isFavoriteFilter: boolean | null
  onFavoriteFilterToggle: () => void
  quickDocFilters: QuickDocFilter[]
  quickFiltersExpanded: boolean
  onToggleQuickDocFilter: (statuses: string[], active: boolean) => void
  onQuickFiltersExpandedChange: (updater: (prev: boolean) => boolean) => void
}

export function CandidatesFiltersActionsPanel({
  t,
  searchRef,
  q,
  onQChange,
  handoffStatusFilter,
  onHandoffStatusFilterChange,
  contactAttemptsFilter,
  onContactAttemptsFilterChange,
  opsModeFilter,
  onOpsModeFilterChange,
  opsModeOptions,
  opsModeLabelMap,
  viewToggle,
  secondaryBtn,
  onRefresh,
  loading,
  actionsMenuRef,
  actionsMenuOpen,
  onActionsMenuOpenChange,
  displayedItems,
  resolveManagerLabel,
  onResetFilters,
  hasFilterBadges,
  onOpenSaveView,
  columnToggleKeys,
  visibleCols,
  onVisibleColsChange,
  visibleColsStorageKey,
  columnLabelMap,
  canManage,
  quickViewParam,
  onQuickViewNavigate,
  onApplyQuickViewFilters,
  isFavoriteFilter,
  onFavoriteFilterToggle,
  quickDocFilters,
  quickFiltersExpanded,
  onToggleQuickDocFilter,
  onQuickFiltersExpandedChange,
}: CandidatesFiltersActionsPanelProps) {
  return (
    <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3">
        <div className="flex-1">
          <label className="block text-xs font-medium text-slate-600 mb-1.5" htmlFor="cand-search">
            {t('app.candidates.search.label')}
          </label>
          <input
            id="cand-search"
            ref={searchRef}
            className="input w-full text-sm py-2 px-3 border border-slate-300 focus:border-brand-500 focus:ring-1 focus:ring-brand-200"
            value={q}
            onChange={(e) => onQChange(e.target.value)}
            placeholder={t('app.candidates.search.placeholder')}
          />
          <p className="mt-1.5 text-[10px] text-slate-400 leading-relaxed">{t('app.candidates.search.hint')}</p>
        </div>
        <div className="space-y-2 pt-2 border-t border-slate-200">
          <label className="block text-xs font-medium text-slate-600">{t('app.candidates.filters.handoff_status_menu', { defaultValue: 'Przekazanie' })}</label>
          <select className="input w-full text-sm py-1.5" value={handoffStatusFilter} onChange={(e) => onHandoffStatusFilterChange(e.target.value)}>
            <option value="">{t('app.candidates.filters.any', { defaultValue: '— dowolne —' })}</option>
            <option value="none">{t('app.candidates.filters.handoff_none', { defaultValue: 'Bez przekazania' })}</option>
            <option value="pending">{t('app.candidates.filters.handoff_pending', { defaultValue: 'Oczekuje' })}</option>
            <option value="accepted">{t('app.candidates.filters.handoff_accepted', { defaultValue: 'Przekazano' })}</option>
            <option value="rejected">{t('app.candidates.filters.handoff_rejected', { defaultValue: 'Odrzucono' })}</option>
            <option value="returned">{t('app.candidates.filters.handoff_returned', { defaultValue: 'Zwrócono' })}</option>
          </select>
          <label className="block text-xs font-medium text-slate-600">{t('app.candidates.filters.contact_attempts_menu', { defaultValue: 'Próby kontaktu' })}</label>
          <select className="input w-full text-sm py-1.5" value={contactAttemptsFilter} onChange={(e) => onContactAttemptsFilterChange(e.target.value)}>
            <option value="">{t('app.candidates.filters.any', { defaultValue: '— dowolne —' })}</option>
            <option value="none">{t('app.candidates.filters.contact_none', { defaultValue: 'Bez prób' })}</option>
            <option value="some">{t('app.candidates.filters.contact_some', { defaultValue: '1–2 próby' })}</option>
            <option value="limit_reached">{t('app.candidates.filters.contact_limit', { defaultValue: '3+ (limit)' })}</option>
          </select>
          <label className="block text-xs font-medium text-slate-600">{t('app.candidates.filters.ops_mode_menu')}</label>
          <select
            className="input w-full text-sm py-1.5"
            value={opsModeFilter[0] || ''}
            onChange={(e) => {
              const value = String(e.target.value || '').trim() as CandidateOpsMode | ''
              if (!value) {
                onOpsModeFilterChange([])
                return
              }
              if (value === 'in_work' || value === 'later' || value === 'no_reply_needed' || value === 'escalated') {
                onOpsModeFilterChange([value])
              }
            }}
          >
            <option value="">{t('app.candidates.filters.any')}</option>
            {(opsModeOptions.length > 0
              ? opsModeOptions
              : [
                  { value: 'in_work', label: opsModeLabelMap.in_work },
                  { value: 'later', label: opsModeLabelMap.later },
                  { value: 'no_reply_needed', label: opsModeLabelMap.no_reply_needed },
                  { value: 'escalated', label: opsModeLabelMap.escalated },
                ]
            ).map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200">
          {viewToggle}
          <button className={secondaryBtn} onClick={onRefresh} disabled={loading} title={t('app.candidates.actions.refresh_title')}>
            {loading ? t('app.candidates.actions.refreshing') : t('app.candidates.actions.refresh')}
          </button>
          <div className="relative" ref={actionsMenuRef}>
            <button type="button" className={secondaryBtn} title={t('app.candidates.actions.more')} onClick={() => onActionsMenuOpenChange((prev) => !prev)}>
              ⋯
            </button>
            {actionsMenuOpen && (
              <div className="absolute right-0 z-20 mt-2 w-64 rounded-md border border-slate-200 bg-white p-3 shadow-lg">
                <div className="space-y-0.5">
                  <button
                    className="btn-secondary w-full justify-start text-left text-xs py-1.5 px-2"
                    title={t('app.candidates.actions.export_title')}
                    onClick={() => {
                      const rows = displayedItems.map((item) => {
                        const c = item as AugmentedCandidate
                        const docsMeta = c.__docsMeta
                        return {
                          name: `${c.first_name ?? ''} ${c.last_name ?? ''}`.trim(),
                          email: c.email ?? '',
                          phone: c.phone ?? '',
                          citizenship: (() => {
                            try {
                              const ex = typeof (c as any).extra === 'string' ? JSON.parse((c as any).extra) : (c as any).extra || {}
                              return ex.citizenship || ex.passport_country || ''
                            } catch {
                              return ''
                            }
                          })(),
                          vacancy: (c as any).vacancy?.title || (c as any).vacancy_title || '',
                          short_id: (c as any).short_id || '',
                          manager: resolveManagerLabel(c) || '',
                          stage: c.stage,
                          docs_status: t(docsMeta.readinessLabelKey),
                          docs_ordered_at: docsMeta.orderDate ?? '',
                          docs_valid_from: docsMeta.validFrom ?? '',
                          docs_has_files: docsMeta.hasFiles ? t('common.words.yes') : t('common.words.no'),
                        }
                      })
                      const csv = toCSV(rows, [
                        { key: 'name', title: t('app.candidates.table.columns.name') },
                        { key: 'email', title: 'Email' },
                        { key: 'phone', title: t('app.candidates.table.columns.phone') },
                        { key: 'citizenship', title: t('app.candidates.table.columns.citizenship') },
                        { key: 'vacancy', title: t('app.candidates.table.columns.vacancy') },
                        { key: 'short_id', title: 'Short ID' },
                        { key: 'manager', title: t('app.candidates.table.columns.manager') },
                        { key: 'stage', title: t('app.candidates.table.columns.stage') },
                        { key: 'docs_status', title: t('app.candidates.table.columns.docs_status') },
                        { key: 'docs_ordered_at', title: t('app.candidates.table.columns.docs_ordered') },
                        { key: 'docs_valid_from', title: t('app.candidates.table.columns.docs_valid') },
                        { key: 'docs_has_files', title: t('app.candidates.table.columns.docs_files') },
                      ])
                      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
                      const url = URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = url
                      a.download = 'candidates.csv'
                      a.click()
                      URL.revokeObjectURL(url)
                      onActionsMenuOpenChange(false)
                    }}
                  >
                    {t('app.candidates.actions.export')}
                  </button>
                  <button
                    className="btn-secondary w-full justify-start text-left text-xs py-1.5 px-2 disabled:opacity-60"
                    onClick={() => {
                      onResetFilters()
                      onActionsMenuOpenChange(false)
                    }}
                    disabled={!hasFilterBadges}
                  >
                    {t('app.candidates.actions.reset_filters')}
                  </button>
                  <button
                    className="btn-secondary w-full justify-start text-left text-xs py-1.5 px-2 disabled:opacity-60"
                    onClick={() => {
                      onActionsMenuOpenChange(false)
                      onOpenSaveView()
                    }}
                    disabled={!hasFilterBadges}
                  >
                    {t('app.candidates.views.save_action')}
                  </button>
                </div>
                <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mt-3 pt-2 border-t border-slate-100">
                  {t('app.candidates.table.columns.title')}
                </div>
                <div className="mt-1.5 max-h-48 space-y-0.5 overflow-auto">
                  {columnToggleKeys.map((key) => (
                    <label key={key} className="flex items-center gap-1.5 text-xs py-0.5">
                      <input
                        type="checkbox"
                        checked={!!visibleCols[key]}
                        onChange={(e) => {
                          const next = { ...visibleCols, [key]: e.currentTarget.checked }
                          onVisibleColsChange(next)
                          try {
                            localStorage.setItem(visibleColsStorageKey, JSON.stringify(next))
                          } catch {}
                        }}
                      />
                      <span>{columnLabelMap[key]}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
          {canManage && (
            <Link className="btn-primary text-xs py-1.5 px-2.5 font-medium" to="/app/candidates/new" title={t('app.candidates.actions.new_candidate_title')}>
              {t('app.candidates.actions.new_candidate')}
            </Link>
          )}
        </div>
      </div>

      <div className="pt-2.5 border-t border-slate-200">
        <h3 className="text-xs font-semibold text-slate-600 mb-2 uppercase tracking-wide">
          {t('app.candidates.views.quick_views_title', { defaultValue: 'Quick Views' })}
        </h3>
        <div className="flex flex-wrap items-center gap-2 mb-2">
          {(
            [
              ['my_work_today', t('app.candidates.views.quick_my_work_today', { defaultValue: 'My work today' })],
              ['docs_incomplete', t('app.candidates.views.quick_docs_incomplete', { defaultValue: 'Docs incomplete' })],
              ['ready_for_handoff', t('app.candidates.views.quick_ready_for_handoff', { defaultValue: 'Ready for handoff' })],
              ['new_this_week', t('app.candidates.views.quick_new_this_week', { defaultValue: 'New this week' })],
              ['no_next_action', t('app.candidates.views.quick_no_next_action', { defaultValue: 'No next action' })],
              ['overdue_next_action', t('app.candidates.views.quick_overdue_next_action', { defaultValue: 'Overdue next action' })],
            ] as Array<[QuickViewKey, string]>
          ).map(([key, label]) => {
            const active = quickViewParam === key
            return (
              <button
                key={key}
                type="button"
                onClick={() => {
                  if (key === 'no_next_action') {
                    onQuickViewNavigate('/app/candidates/no-next-action')
                    return
                  }
                  if (key === 'overdue_next_action') {
                    onQuickViewNavigate('/app/tasks?tab=tasks&t_status=active&t_entity=candidate')
                    return
                  }
                  onApplyQuickViewFilters(key)
                }}
                className={[
                  'rounded-md px-2.5 py-1.5 text-xs font-medium transition-all',
                  active
                    ? 'bg-brand-600 text-white shadow-sm hover:bg-brand-700'
                    : 'bg-white text-brand-700 border border-brand-200 hover:bg-brand-50 hover:border-brand-300',
                ].join(' ')}
              >
                {label}
              </button>
            )
          })}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={onFavoriteFilterToggle}
            className={[
              'rounded-md px-2.5 py-1.5 text-xs font-medium transition-all',
              isFavoriteFilter === true
                ? 'bg-brand-600 text-white shadow-sm hover:bg-brand-700'
                : 'bg-white text-brand-700 border border-brand-200 hover:bg-brand-50 hover:border-brand-300',
            ].join(' ')}
          >
            {t('app.candidates.filters.only_favorites')}
          </button>
          {(quickFiltersExpanded ? quickDocFilters : quickDocFilters.slice(0, 3)).map((filter) => (
            <button
              key={filter.key}
              type="button"
              onClick={() => onToggleQuickDocFilter(filter.statuses, filter.active)}
              className={[
                'rounded-md px-2.5 py-1.5 text-xs font-medium transition-all',
                filter.active
                  ? 'bg-brand-600 text-white shadow-sm hover:bg-brand-700'
                  : 'bg-white text-brand-700 border border-brand-200 hover:bg-brand-50 hover:border-brand-300',
              ].join(' ')}
            >
              {filter.label}
            </button>
          ))}
          {quickDocFilters.length > 3 && (
            <button
              type="button"
              className="rounded-md px-2.5 py-1.5 text-xs font-medium border border-slate-300 text-slate-700 hover:bg-slate-50 hover:border-slate-400 transition-all"
              onClick={() => onQuickFiltersExpandedChange((prev) => !prev)}
            >
              {quickFiltersExpanded ? t('app.candidates.filters.quick_less') : t('app.candidates.filters.quick_more')}
            </button>
          )}
        </div>
      </div>
    </section>
  )
}
