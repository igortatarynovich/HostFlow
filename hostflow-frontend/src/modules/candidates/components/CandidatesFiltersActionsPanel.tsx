import type { ReactNode, RefObject } from 'react'
import { Link } from 'react-router-dom'
import type { UserSavedView } from '../../../api/types'
import { toCSV } from '../candidateUtils'
import type { AugmentedCandidate, CandidateOpsMode } from '../types'
import { CandidatesQuickViewsBar, type QuickViewKey } from './CandidatesQuickViewsBar'

type QuickDocFilter = { key: string; label: string; statuses: string[]; active: boolean }

type CandidatesFiltersActionsPanelProps = {
  t: (key: string, options?: any) => string
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
  /** Разрешить «Сохранить вид» (фильтры, избранное, быстрый вид из URL). */
  viewSaveEnabled: boolean
  /** Режим перестановки/ресайза колонок таблицы (R1.5 Phase C). */
  tableLayoutCustomize: boolean
  onTableLayoutCustomizeChange: (value: boolean) => void
}

export function CandidatesFiltersActionsPanel({
  t,
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
  viewSaveEnabled,
  tableLayoutCustomize,
  onTableLayoutCustomizeChange,
}: CandidatesFiltersActionsPanelProps) {
  return (
    <section className="space-y-2">
      <div className="rounded-xl border border-slate-200/90 bg-gradient-to-b from-white to-slate-50/80 p-2.5 shadow-sm">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
          {t('app.candidates.rail.list_controls', { defaultValue: 'List & filters' })}
        </p>

        <div className="flex flex-wrap items-center gap-2 border-b border-slate-200/80 pb-3">
        {viewToggle}
        <button className={secondaryBtn} onClick={onRefresh} disabled={loading} title={t('app.candidates.actions.refresh_title')}>
          {loading ? t('app.candidates.actions.refreshing') : t('app.candidates.actions.refresh')}
        </button>
        <button
          type="button"
          className={
            tableLayoutCustomize
              ? 'inline-flex items-center gap-2 rounded-md border border-brand-500 bg-brand-50 px-3 py-2 text-sm font-semibold text-brand-900 hover:bg-brand-100'
              : secondaryBtn
          }
          title={t('app.candidates.table.customize_layout_title', {
            defaultValue: 'Reorder columns (⋮⋮) and resize widths. Column visibility stays under ⋯.',
          })}
          onClick={() => onTableLayoutCustomizeChange(!tableLayoutCustomize)}
        >
          {tableLayoutCustomize
            ? t('app.candidates.table.customize_layout_done', { defaultValue: 'Done customizing' })
            : t('app.candidates.table.customize_layout', { defaultValue: 'Customize table' })}
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

        <div className="pt-3">
          <CandidatesQuickViewsBar
            variant="rail"
            t={t}
            quickViewParam={quickViewParam}
            onApplyQuickViewFilters={onApplyQuickViewFilters}
            isFavoriteFilter={isFavoriteFilter}
            onFavoriteFilterToggle={onFavoriteFilterToggle}
            quickDocFilters={quickDocFilters}
            quickFiltersExpanded={quickFiltersExpanded}
            onToggleQuickDocFilter={onToggleQuickDocFilter}
            onQuickFiltersExpandedChange={onQuickFiltersExpandedChange}
            savedViews={savedViews}
            onApplySavedView={onApplySavedView}
            onDeleteSavedView={onDeleteSavedView}
            onOpenSaveView={onOpenSaveView}
            viewSaveEnabled={viewSaveEnabled}
          />
        </div>
      </div>

      <details className="rounded-lg border border-slate-200/90 bg-white/90 px-2.5 py-2 shadow-sm">
        <summary className="cursor-pointer select-none text-xs font-medium text-slate-600 hover:text-slate-900">
          {t('app.candidates.filters.more_filters_summary', { defaultValue: 'More filters (handoff, contact, ops mode)' })}
        </summary>
        <div className="mt-2 space-y-2 border-t border-slate-100 pt-2">
          <label className="block text-xs font-medium text-slate-600">{t('app.candidates.filters.handoff_status_menu', { defaultValue: 'Handoff' })}</label>
          <select className="input w-full text-sm py-1.5" value={handoffStatusFilter} onChange={(e) => onHandoffStatusFilterChange(e.target.value)}>
            <option value="">{t('app.candidates.filters.any', { defaultValue: '— any —' })}</option>
            <option value="none">{t('app.candidates.filters.handoff_none', { defaultValue: 'No handoff' })}</option>
            <option value="pending">{t('app.candidates.filters.handoff_pending', { defaultValue: 'Pending' })}</option>
            <option value="accepted">{t('app.candidates.filters.handoff_accepted', { defaultValue: 'Accepted' })}</option>
            <option value="rejected">{t('app.candidates.filters.handoff_rejected', { defaultValue: 'Rejected' })}</option>
            <option value="returned">{t('app.candidates.filters.handoff_returned', { defaultValue: 'Returned' })}</option>
          </select>
          <label className="block text-xs font-medium text-slate-600">{t('app.candidates.filters.contact_attempts_menu', { defaultValue: 'Contact attempts' })}</label>
          <select className="input w-full text-sm py-1.5" value={contactAttemptsFilter} onChange={(e) => onContactAttemptsFilterChange(e.target.value)}>
            <option value="">{t('app.candidates.filters.any', { defaultValue: '— any —' })}</option>
            <option value="none">{t('app.candidates.filters.contact_none', { defaultValue: 'None' })}</option>
            <option value="some">{t('app.candidates.filters.contact_some', { defaultValue: '1–2' })}</option>
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
      </details>
    </section>
  )
}
