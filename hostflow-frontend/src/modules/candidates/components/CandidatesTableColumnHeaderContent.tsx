// src/modules/candidates/components/CandidatesTableColumnHeaderContent.tsx
//
// Renders the contents of a single <th> in the Candidates table:
//   - sort button
//   - column-specific filter menu (text / range / multi-value)
//
// Extracted from `renderColumnHeaderContent` + the inline
// `renderSortButton`, `renderRangeMenu`, `renderTextFilterMenu` helpers in
// `src/pages/Candidates.tsx` (Phase 1 #4 god-component split).
//
// All cross-cutting state and setters are passed via a single `ctx` bag.

import type { ReactNode } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import type { TranslateFn } from '../../../i18n'
import type { ColumnTextFilters, DateRangeFilter, SortKey } from '../types'
import { isRangeActive } from '../candidateUtils'
import { ColumnFilterMenu } from './ColumnFilterMenu'

interface FilterOption {
  value: string
  label: string
}

export interface CandidatesTableColumnHeaderCtx {
  // ---- i18n ----------------------------------------------------------
  t: TranslateFn

  // ---- sort state ----------------------------------------------------
  sortKey: SortKey
  sortDir: 'asc' | 'desc'
  handleSortChange: (key: SortKey) => void

  // ---- text filters --------------------------------------------------
  textFilters: ColumnTextFilters
  setTextFilter: (key: keyof ColumnTextFilters, value: string) => void

  // ---- column labels -------------------------------------------------
  columnLabelMap: Record<string, string>

  // ---- header (checkbox) --------------------------------------------
  allVisibleSelected: boolean
  canManage: boolean
  setChecked: Dispatch<SetStateAction<Record<string, boolean>>>
  displayedItems: Array<{ id: string }>

  // ---- catalog filter options + selected + setters ------------------
  vacancyFilterOptions: FilterOption[]
  vacancyFilter: string[]
  setVacancyFilter: (next: string[]) => void
  managerFilterOptions: FilterOption[]
  managerFilter: string[]
  setManagerFilter: (next: string[]) => void
  stageFilterOptions: FilterOption[]
  stageFilter: string[]
  setStageFilter: (next: string[]) => void
  preferredChannelOptions: FilterOption[]
  preferredChannelFilter: string[]
  setPreferredChannelFilter: (next: string[]) => void
  inPolandOptions: FilterOption[]
  inPolandFilter: string[]
  setInPolandFilter: (next: string[]) => void
  polandBasisOptions: FilterOption[]
  polandBasisFilter: string[]
  setPolandBasisFilter: (next: string[]) => void
  trailerTypesOptions: FilterOption[]
  trailerTypesFilter: string[]
  setTrailerTypesFilter: (next: string[]) => void
  reasonFilterOptions: FilterOption[]
  statusReasonFilter: string[]
  setStatusReasonFilter: (next: string[]) => void
  intakeApplicationKindFilter: '' | 'client' | 'candidate'
  setIntakeApplicationKindFilter: Dispatch<SetStateAction<'' | 'client' | 'candidate'>>
  docsStatusFilterOptions: FilterOption[]
  docsStatusFilter: string[]
  setDocsStatusFilter: (next: string[]) => void
  docsOrderFilterOptions: FilterOption[]
  docsOrderedFilter: string[]
  setDocsOrderedFilter: (next: string[]) => void
  docsHasFilesOptions: FilterOption[]
  docsHasFilesFilter: string[]
  setDocsHasFilesFilter: (next: string[]) => void
  tagsFilter: string[]
  setTagsFilter: (next: string[]) => void

  // ---- date ranges ---------------------------------------------------
  createdRange: DateRangeFilter
  setCreatedRange: (next: DateRangeFilter) => void
  firstContactRange: DateRangeFilter
  setFirstContactRange: (next: DateRangeFilter) => void
  docsValidRange: DateRangeFilter
  setDocsValidRange: (next: DateRangeFilter) => void

  // ---- tag aggregation source ---------------------------------------
  enrichedItems: Array<{ tags?: string[] | null }>
}

function renderSortButton(label: string, key: SortKey, ctx: CandidatesTableColumnHeaderCtx): ReactNode {
  const { sortKey, sortDir, handleSortChange, t } = ctx
  return (
    <button
      type="button"
      className="inline-flex h-5 min-w-0 shrink items-center gap-1 whitespace-nowrap font-semibold leading-none text-left text-slate-700 hover:text-brand-600 transition-colors group/sort relative"
      onClick={() => handleSortChange(key)}
      title={
        sortKey === key
          ? t('app.candidates.table.sort_by', { values: { column: label, dir: sortDir === 'asc' ? t('common.sort.asc') : t('common.sort.desc') } }) || `Сортировка по ${label} (${sortDir === 'asc' ? '↑' : '↓'})`
          : t('app.candidates.table.click_to_sort', { values: { column: label } }) || `Кликните для сортировки по ${label}`
      }
    >
      <span className="truncate">{label}</span>
      {sortKey === key && (
        <span
          className="inline-flex h-4 w-4 items-center justify-center text-[11px] text-brand-600/90 font-semibold"
          title={sortDir === 'asc' ? t('common.sort.asc') || 'По возрастанию' : t('common.sort.desc') || 'По убыванию'}
        >
          {sortDir === 'asc' ? '▲' : '▼'}
        </span>
      )}
      {sortKey !== key && (
        <span className="inline-flex h-4 w-4 items-center justify-center text-[10px] text-slate-300 opacity-0 transition-opacity group-hover/sort:opacity-100 group-focus-visible/sort:opacity-100">↕</span>
      )}
    </button>
  )
}

function renderRangeMenu(
  title: string,
  range: DateRangeFilter,
  onChange: (next: DateRangeFilter) => void,
  onReset: () => void,
  ctx: CandidatesTableColumnHeaderCtx,
): ReactNode {
  const { t } = ctx
  return (
    <ColumnFilterMenu title={title} count={isRangeActive(range) ? 1 : 0}>
      {(close) => (
        <div className="space-y-2">
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            {t('app.candidates.filters.date_from')}
            <input
              type="date"
              className="input"
              value={range.from ?? ''}
              onChange={(e) => onChange({ ...range, from: e.currentTarget.value || null })}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            {t('app.candidates.filters.date_to')}
            <input
              type="date"
              className="input"
              value={range.to ?? ''}
              onChange={(e) => onChange({ ...range, to: e.currentTarget.value || null })}
            />
          </label>
          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              className="btn-secondary btn-xs"
              onClick={() => {
                onReset()
                close()
              }}
            >
              {t('app.candidates.filters.reset')}
            </button>
            <button type="button" className="btn-primary btn-xs" onClick={close}>
              {t('common.actions.close')}
            </button>
          </div>
        </div>
      )}
    </ColumnFilterMenu>
  )
}

function renderTextFilterMenu(
  key: keyof ColumnTextFilters,
  title: string,
  placeholder: string,
  ctx: CandidatesTableColumnHeaderCtx,
): ReactNode {
  const { t, textFilters, setTextFilter } = ctx
  return (
    <ColumnFilterMenu title={title} count={textFilters[key].trim() ? 1 : 0}>
      {(close) => (
        <div className="space-y-2">
          <input
            className="input"
            value={textFilters[key]}
            onChange={(e) => setTextFilter(key, e.currentTarget.value)}
            placeholder={placeholder}
          />
          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              className="btn-secondary btn-xs"
              onClick={() => {
                setTextFilter(key, '')
                close()
              }}
              disabled={!textFilters[key]}
            >
              {t('app.candidates.filters.reset')}
            </button>
            <button type="button" className="btn-primary btn-xs" onClick={close}>
              {t('common.actions.close')}
            </button>
          </div>
        </div>
      )}
    </ColumnFilterMenu>
  )
}

export interface CandidatesTableColumnHeaderContentProps {
  columnKey: string
  ctx: CandidatesTableColumnHeaderCtx
}

export function CandidatesTableColumnHeaderContent({ columnKey, ctx }: CandidatesTableColumnHeaderContentProps): ReactNode {
  const {
    t, columnLabelMap,
    allVisibleSelected, canManage, setChecked, displayedItems,
    vacancyFilterOptions, vacancyFilter, setVacancyFilter,
    managerFilterOptions, managerFilter, setManagerFilter,
    stageFilterOptions, stageFilter, setStageFilter,
    preferredChannelOptions, preferredChannelFilter, setPreferredChannelFilter,
    inPolandOptions, inPolandFilter, setInPolandFilter,
    polandBasisOptions, polandBasisFilter, setPolandBasisFilter,
    trailerTypesOptions, trailerTypesFilter, setTrailerTypesFilter,
    reasonFilterOptions, statusReasonFilter, setStatusReasonFilter,
    intakeApplicationKindFilter, setIntakeApplicationKindFilter,
    docsStatusFilterOptions, docsStatusFilter, setDocsStatusFilter,
    docsOrderFilterOptions, docsOrderedFilter, setDocsOrderedFilter,
    docsHasFilesOptions, docsHasFilesFilter, setDocsHasFilesFilter,
    tagsFilter, setTagsFilter,
    createdRange, setCreatedRange,
    firstContactRange, setFirstContactRange,
    docsValidRange, setDocsValidRange,
    enrichedItems,
  } = ctx

  switch (columnKey) {
    case 'checkbox':
      return (
        <div className="flex items-center justify-center">
          <input
            type="checkbox"
            checked={allVisibleSelected}
            disabled={!canManage}
            onChange={(e) => {
              if (!canManage) return
              const val = e.currentTarget.checked
              setChecked((prev) => {
                const next = { ...prev }
                displayedItems.forEach((candidate) => {
                  next[candidate.id] = val
                })
                return next
              })
            }}
            className="cursor-pointer w-4 h-4"
            title={allVisibleSelected ? (t('app.candidates.table.deselect_all') || 'Снять выделение со всех') : (t('app.candidates.table.select_all') || 'Выделить все видимые')}
            aria-label={allVisibleSelected ? (t('app.candidates.table.deselect_all') || 'Снять выделение со всех') : (t('app.candidates.table.select_all') || 'Выделить все видимые')}
          />
        </div>
      )
    case 'name':
      return (
        <>
          {renderSortButton(columnLabelMap.name, 'name', ctx)}
          {renderTextFilterMenu('name', t('app.candidates.filters.name_menu'), t('app.candidates.filters.name_placeholder'), ctx)}
        </>
      )
    case 'email':
      return (
        <>
          {renderSortButton(columnLabelMap.email, 'email', ctx)}
          {renderTextFilterMenu('email', t('app.candidates.filters.email_menu'), t('app.candidates.filters.email_placeholder'), ctx)}
        </>
      )
    case 'phone':
      return (
        <>
          {renderSortButton(columnLabelMap.phone, 'phone', ctx)}
          {renderTextFilterMenu('phone', t('app.candidates.filters.phone_menu'), t('app.candidates.filters.phone_placeholder'), ctx)}
        </>
      )
    case 'citizenship':
      return (
        <>
          {renderSortButton(columnLabelMap.citizenship, 'citizenship', ctx)}
          {renderTextFilterMenu('citizenship', t('app.candidates.filters.citizenship_menu'), t('app.candidates.filters.citizenship_placeholder'), ctx)}
        </>
      )
    case 'vacancy':
      return (
        <>
          {renderSortButton(columnLabelMap.vacancy, 'vacancy', ctx)}
          <ColumnFilterMenu
            title={t('app.candidates.filters.vacancy_menu')}
            options={vacancyFilterOptions}
            selected={vacancyFilter}
            onChange={setVacancyFilter}
          />
        </>
      )
    case 'short':
      return (
        <>
          {renderSortButton(columnLabelMap.short, 'short_id', ctx)}
          {renderTextFilterMenu('short', t('app.candidates.filters.short_menu'), t('app.candidates.filters.short_placeholder'), ctx)}
        </>
      )
    case 'manager':
      return (
        <>
          {renderSortButton(columnLabelMap.manager, 'manager', ctx)}
          <ColumnFilterMenu
            title={t('app.candidates.filters.manager_menu')}
            options={managerFilterOptions}
            selected={managerFilter}
            onChange={setManagerFilter}
          />
        </>
      )
    case 'stage':
      return (
        <>
          {renderSortButton(columnLabelMap.stage, 'stage', ctx)}
          <ColumnFilterMenu
            title={t('app.candidates.filters.stage_menu')}
            options={stageFilterOptions}
            selected={stageFilter}
            onChange={setStageFilter}
          />
        </>
      )
    case 'risk':
      return <>{renderSortButton(columnLabelMap.risk, 'risk_score', ctx)}</>
    case 'created':
      return (
        <>
          {renderSortButton(columnLabelMap.created, 'created_at', ctx)}
          {renderRangeMenu(
            t('app.candidates.filters.created_menu'),
            createdRange,
            (next) => setCreatedRange(next),
            () => setCreatedRange({ from: null, to: null }),
            ctx,
          )}
        </>
      )
    case 'firstContact':
      return (
        <>
          {renderSortButton(columnLabelMap.firstContact, 'first_contact', ctx)}
          {renderRangeMenu(
            t('app.candidates.filters.first_contact_menu'),
            firstContactRange,
            (next) => setFirstContactRange(next),
            () => setFirstContactRange({ from: null, to: null }),
            ctx,
          )}
        </>
      )
    case 'preferredChannel':
      return (
        <>
          {renderSortButton(columnLabelMap.preferredChannel, 'preferred_channel', ctx)}
          <ColumnFilterMenu
            title={t('app.candidates.filters.preferred_channel_menu')}
            options={preferredChannelOptions}
            selected={preferredChannelFilter}
            onChange={setPreferredChannelFilter}
          />
        </>
      )
    case 'inPoland':
      return (
        <>
          {renderSortButton(columnLabelMap.inPoland, 'in_poland', ctx)}
          <ColumnFilterMenu
            title={t('app.candidates.filters.in_poland_menu')}
            options={inPolandOptions}
            selected={inPolandFilter}
            onChange={setInPolandFilter}
          />
        </>
      )
    case 'polandBasis':
      return (
        <>
          {renderSortButton(columnLabelMap.polandBasis, 'poland_basis', ctx)}
          <ColumnFilterMenu
            title={t('app.candidates.filters.poland_basis_menu')}
            options={polandBasisOptions}
            selected={polandBasisFilter}
            onChange={setPolandBasisFilter}
          />
        </>
      )
    case 'trailerTypes':
      return (
        <>
          {renderSortButton(columnLabelMap.trailerTypes, 'trailer_types', ctx)}
          <ColumnFilterMenu
            title={t('app.candidates.filters.trailer_types_menu')}
            options={trailerTypesOptions}
            selected={trailerTypesFilter}
            onChange={setTrailerTypesFilter}
          />
        </>
      )
    case 'reasons':
      return (
        <>
          {renderSortButton(columnLabelMap.reasons, 'reasons', ctx)}
          <ColumnFilterMenu
            title={t('app.candidates.filters.reason_menu')}
            options={reasonFilterOptions}
            selected={statusReasonFilter}
            onChange={setStatusReasonFilter}
          />
        </>
      )
    case 'intakeKind':
      return (
        <ColumnFilterMenu
          title={t('app.candidates.filters.intake_kind_menu', { defaultValue: 'Public intake' })}
          options={[
            { value: 'client', label: t('app.candidates.filters.intake_kind_client', { defaultValue: 'Client inquiry only' }) },
            {
              value: 'candidate',
              label: t('app.candidates.filters.intake_kind_candidate', { defaultValue: 'Not client inquiry' }),
            },
          ]}
          selected={intakeApplicationKindFilter ? [intakeApplicationKindFilter] : []}
          onChange={(next) => {
            if (next.length === 0) {
              setIntakeApplicationKindFilter('')
              return
            }
            const last = next[next.length - 1]
            setIntakeApplicationKindFilter(last === 'client' || last === 'candidate' ? last : '')
          }}
        />
      )
    case 'is_favorite':
      return (
        <>
          {renderSortButton(columnLabelMap.is_favorite, 'is_favorite', ctx)}
        </>
      )
    case 'tags': {
      const allTags = new Set<string>()
      enrichedItems.forEach((item) => {
        const tags = Array.isArray(item.tags) ? item.tags : []
        tags.forEach((tag) => {
          if (tag && typeof tag === 'string') {
            allTags.add(tag.trim())
          }
        })
      })
      const tagOptions = Array.from(allTags).sort().map((tag) => ({
        value: tag,
        label: tag,
      }))
      return (
        <>
          {renderSortButton(columnLabelMap.tags, 'tags', ctx)}
          <ColumnFilterMenu
            title={t('app.candidates.filters.tags_menu')}
            options={tagOptions}
            selected={tagsFilter}
            onChange={setTagsFilter}
          />
        </>
      )
    }
    case 'docsStatus':
      return (
        <>
          {renderSortButton(columnLabelMap.docsStatus, 'docs_status', ctx)}
          <ColumnFilterMenu
            title={t('app.candidates.filters.docs_status_menu')}
            options={docsStatusFilterOptions}
            selected={docsStatusFilter}
            onChange={setDocsStatusFilter}
          />
        </>
      )
    case 'docsOrdered':
      return (
        <>
          {renderSortButton(columnLabelMap.docsOrdered, 'docs_ordered_at', ctx)}
          <ColumnFilterMenu
            title={t('app.candidates.filters.docs_order_menu')}
            options={docsOrderFilterOptions}
            selected={docsOrderedFilter}
            onChange={setDocsOrderedFilter}
          />
        </>
      )
    case 'docsValid':
      return (
        <>
          {renderSortButton(columnLabelMap.docsValid, 'docs_valid_from', ctx)}
          {renderRangeMenu(
            t('app.candidates.filters.docs_valid_menu'),
            docsValidRange,
            (next) => setDocsValidRange(next),
            () => setDocsValidRange({ from: null, to: null }),
            ctx,
          )}
        </>
      )
    case 'docsFiles':
      return (
        <>
          {renderSortButton(columnLabelMap.docsFiles, 'docs_has_files', ctx)}
          <ColumnFilterMenu
            title={t('app.candidates.filters.docs_files_menu')}
            options={docsHasFilesOptions}
            selected={docsHasFilesFilter}
            onChange={setDocsHasFilesFilter}
          />
        </>
      )
    default:
      return null
  }
}
