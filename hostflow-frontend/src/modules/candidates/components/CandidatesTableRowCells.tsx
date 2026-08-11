// src/modules/candidates/components/CandidatesTableRowCells.tsx
//
// Renders all <td> cells for one candidate row in the Candidates table.
// Extracted from the inline `renderCandidateRowTds` render-prop in
// `src/pages/Candidates.tsx` (Phase 1 #4 god-component split).
//
// The component receives:
//   - `index`, `c`     — per-row inputs (forwarded by Virtuoso `itemContent`)
//   - `ctx`            — shared catalog/state/handler bag built once on the
//                        page and memoised by React's referential equality.
//
// Keeping deps in a single `ctx` object lets the page wire the component
// without inflating the call site (one prop instead of ~35), while still
// passing them as plain props (so React can short-circuit re-renders when
// `ctx` is memoised).

import type { ReactNode } from 'react'
import clsx from 'clsx'
import { Link } from 'react-router-dom'
import {
  IconArrowRight,
  IconBookmark,
  IconBookmarkFilled,
  IconMail,
  IconPhone,
} from '@tabler/icons-react'
import api from '../../../api/client'
import type { Dispatch, SetStateAction } from 'react'
import type { LocaleCode, TranslateFn } from '../../../i18n'
import { CRM_APP_PATHS } from '../../../app/crmAppPaths'
import { getRegionDisplayName } from '../../../utils/catalogLocale'
import { formatErrorForDisplay } from '../../../utils/errorHandling'
import type { PlanLimitModalContextValue } from '../../../contexts/PlanLimitModalContext'
import { DOC_READINESS_META, EMPTY_OPTION_VALUE } from '../constants'
import { formatDateSafe } from '../candidateUtils'
import { getCandidateVacancyId } from '../utils'
import type { AugmentedCandidate, UICandidate } from '../types'
import { CandidatesTableCheckboxCell } from './CandidatesTableCheckboxCell'
import { CandidatesTableRowNamePreview } from './CandidatesTableRowNamePreview'
import { CandidatesTableRowStageCell } from './CandidatesTableRowStageCell'

export interface CandidatesTableRowCellsCtx {
  // ---- i18n / locale -------------------------------------------------
  t: TranslateFn
  locale: LocaleCode

  // ---- selection / focus / work-panel --------------------------------
  focusedRowIndex: number | null
  workPanelOpen: boolean
  selectedCandidateId: string | null
  setSelectedCandidateId: Dispatch<SetStateAction<string | null>>
  setSidebarOpen: Dispatch<SetStateAction<boolean>>
  checked: Record<string, boolean>
  toggle: (id: string) => void
  canManage: boolean
  canViewActivities: boolean

  // ---- column visibility / order / width -----------------------------
  orderedVisibleColumns: string[]
  visibleCols: Record<string, boolean>
  getColumnWidth: (key: string) => number

  // ---- catalogs / lookup maps ---------------------------------------
  vacancyLabelMap: Map<string, string>
  preferredChannelLabelMap: Record<string, string>
  inPolandLabelMap: Record<string, string>
  reasonLabelMap: Map<string, string>
  resolveManagerLabel: (c: AugmentedCandidate) => string | null | undefined
  getPolandBasisLabel: (basis: string) => string
  getTrailerTypeLabel: (kind: string) => string
  asTelHref: (display: string | null | undefined) => string | undefined

  // ---- side-effects --------------------------------------------------
  navigate: (to: string) => void
  handleCandidateOpen: (id: string) => void
  setItems: Dispatch<SetStateAction<UICandidate[]>>
  setTaskQuickModal: (m: { id: string; label: string }) => void
  planLimitModal: PlanLimitModalContextValue | null
}

export interface CandidatesTableRowCellsProps {
  index: number
  c: AugmentedCandidate
  ctx: CandidatesTableRowCellsCtx
}

export function CandidatesTableRowCells({ index, c, ctx }: CandidatesTableRowCellsProps) {
  const {
    t, locale,
    focusedRowIndex, workPanelOpen, selectedCandidateId,
    setSelectedCandidateId, setSidebarOpen,
    checked, toggle, canManage, canViewActivities,
    orderedVisibleColumns, visibleCols, getColumnWidth,
    vacancyLabelMap, preferredChannelLabelMap, inPolandLabelMap, reasonLabelMap,
    resolveManagerLabel, getPolandBasisLabel, getTrailerTypeLabel, asTelHref,
    navigate, handleCandidateOpen, setItems, setTaskQuickModal, planLimitModal,
  } = ctx

  const docsMeta = c.__docsMeta
  const reasonTags = c.__reasonCodes
  const fallbackReasons = c.__reasonFallbackLabels
  const isFocused = focusedRowIndex === index
  const isWorkPanelRow = Boolean(workPanelOpen && selectedCandidateId === c.id)

  return (
    <>
      {/* No sticky on body-cells: sticky tbody + sticky thead in Virtuoso broke hit-testing (clicks/mouseup went to the header). */}
      <CandidatesTableCheckboxCell
        c={c}
        isFocused={isFocused}
        isWorkPanelRow={isWorkPanelRow}
        checked={checked}
        canManage={canManage}
        toggle={toggle}
        t={t}
      />
      {orderedVisibleColumns.map((columnKey) => {
        if (!visibleCols[columnKey]) return null

        let cellContent: ReactNode = null

        if (columnKey === 'name') {
          const candidateLabel =
            (c as AugmentedCandidate).masked === true
                  ? (c.short_id
                      ? t('app.candidates.table.masked_label_short_id', {
                          defaultValue: 'Candidate {short_id}',
                          values: { short_id: c.short_id },
                        })
                      : t('app.candidates.table.masked_label', {
                          defaultValue: 'Candidate #{id}',
                          values: { id: (c.id ?? '').slice(0, 8) },
                        }))
                  : `${c.first_name ?? ''} ${c.last_name ?? ''}`.trim() || t('common.labels.not_available')
          const isMasked = (c as AugmentedCandidate).masked === true
          const cardHref = `${CRM_APP_PATHS.candidates}/${c.id}`
          const emailForActions = !isMasked ? String(c.email || '').trim() : ''
          const phoneForTel =
            !isMasked && c.phone && String(c.phone).trim() !== '' ? asTelHref(c.phone) : undefined
          const rowActionBtnClass =
            'inline-flex items-center gap-0.5 rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-slate-800 shadow-sm hover:border-brand-300 hover:bg-brand-50/80'
          cellContent = (
            <div className="group/name flex min-w-0 flex-col gap-1">
              <div className="flex min-w-0 items-center gap-1.5">
                <div className="min-w-0 flex-1 overflow-hidden">
                  <Link
                    to={cardHref}
                    className="block truncate whitespace-nowrap font-medium text-brand-600 hover:text-brand-700 hover:underline"
                    onClick={(e) => {
                      e.preventDefault()
                      handleCandidateOpen(c.id)
                      navigate(cardHref)
                    }}
                    title={
                      (c as AugmentedCandidate).masked === true
                        ? t('app.candidates.table.open_card_masked', {
                            defaultValue: 'Open candidate card',
                          })
                        : t('app.candidates.table.open_card_named', {
                            defaultValue: 'Open candidate card {name}',
                            values: {
                              name: `${c.first_name ?? ''} ${c.last_name ?? ''}`.trim(),
                            },
                          })
                    }
                  >
                    {candidateLabel}
                  </Link>
                </div>
                <CandidatesTableRowNamePreview
                  c={c}
                  isFocused={isFocused}
                  selectedCandidateId={selectedCandidateId}
                  workPanelOpen={workPanelOpen}
                  setSelectedCandidateId={setSelectedCandidateId}
                  setSidebarOpen={setSidebarOpen}
                  t={t}
                />
              </div>
              {isMasked ? (
                <div
                  className="truncate text-xs text-slate-500"
                  title={
                    c.short_id || ((c as AugmentedCandidate).masked && (c.id ?? '').slice(0, 8))
                      ? `Short ID: ${c.short_id || (c.id ?? '').slice(0, 8)}`
                      : undefined
                  }
                >
                  {c.short_id ? `ID ${c.short_id}` : `ID ${(c.id ?? '').slice(0, 8)}`}
                </div>
              ) : null}
              <div className="mt-1 flex flex-wrap gap-1 border-t border-slate-100 pt-1.5">
                {phoneForTel ? (
                  <a href={phoneForTel} className={rowActionBtnClass}>
                    <IconPhone size={11} stroke={2} className="shrink-0 text-slate-600" aria-hidden />
                    {t('app.candidates.pipeline.action_call', { defaultValue: 'Call' })}
                  </a>
                ) : null}
                {emailForActions ? (
                  <a href={`mailto:${emailForActions}`} className={rowActionBtnClass}>
                    <IconMail size={11} stroke={2} className="shrink-0 text-slate-600" aria-hidden />
                    {t('app.candidates.pipeline.action_write', { defaultValue: 'Email' })}
                  </a>
                ) : null}
                <Link
                  to={cardHref}
                  className={rowActionBtnClass}
                  onClick={(e) => {
                    e.preventDefault()
                    handleCandidateOpen(c.id)
                    navigate(cardHref)
                  }}
                >
                  <IconArrowRight size={11} stroke={2} className="shrink-0 text-slate-600" aria-hidden />
                  {t('app.candidates.pipeline.action_open_card', { defaultValue: 'Open' })}
                </Link>
                {canViewActivities ? (
                  <button
                    type="button"
                    className={rowActionBtnClass}
                    onClick={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      setTaskQuickModal({
                        id: String(c.id),
                        label: String(candidateLabel || c.id || '').slice(0, 200),
                      })
                    }}
                  >
                    {t('app.candidates.pipeline.action_tasks', { defaultValue: 'Tasks' })}
                  </button>
                ) : null}
              </div>
            </div>
          )
        } else if (columnKey === 'email') {
          cellContent = (c as AugmentedCandidate).masked === true ? t('common.labels.not_available') : (c.email || t('common.labels.not_available'))
        } else if (columnKey === 'phone') {
          const phoneDisplay = (c as AugmentedCandidate).masked === true ? '—' : (c.phone || '—')
          const href = phoneDisplay && phoneDisplay !== '—' ? asTelHref(phoneDisplay) : undefined
          cellContent = href ? (
            <a
              href={href}
              className="text-brand-600 hover:text-brand-700 hover:underline"
              title={t('app.candidates.table.call_named', {
                defaultValue: 'Call {phone}',
                values: { phone: phoneDisplay },
              })}
            >
              {phoneDisplay}
            </a>
          ) : (
            phoneDisplay
          )
        } else if (columnKey === 'citizenship') {
          const cit = c.__extra.citizenship || ''
          cellContent = cit
            ? (/^[A-Z]{2}$/.test(String(cit).toUpperCase()) ? getRegionDisplayName(cit, locale) : cit)
            : t('common.labels.not_available')
        } else if (columnKey === 'vacancy') {
          const vacancyId = getCandidateVacancyId(c)
          const vacancyName = vacancyId ? vacancyLabelMap.get(vacancyId) : null
          cellContent = vacancyName || t('common.labels.not_available')
        } else if (columnKey === 'short') {
          // For masked candidates, backend sends short_id or id prefix; fallback to id slice for display
          cellContent = (c as AugmentedCandidate).masked === true
            ? (c.short_id || (c.id ?? '').slice(0, 8) || t('common.labels.not_available'))
            : (c.short_id || t('common.labels.not_available'))
        } else if (columnKey === 'manager') {
          const managerName = resolveManagerLabel(c)
          cellContent = managerName || t('app.candidates.table.manager_not_assigned', { defaultValue: 'Not assigned' })
        } else if (columnKey === 'stage') {
          cellContent = <CandidatesTableRowStageCell candidate={c} />
        } else if (columnKey === 'risk') {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const score = (c as any).risk_score
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const bandRaw: string | null | undefined = (c as any).risk_band
          const band =
            bandRaw ||
            (typeof score === 'number'
              ? score >= 85
                ? 'critical'
                : score >= 65
                  ? 'high'
                  : score >= 35
                    ? 'medium'
                    : 'low'
              : null)

          const bandLabel =
            band === 'critical'
              ? t('app.candidates.table.risk_band.critical', { defaultValue: 'Critical' })
              : band === 'high'
                ? t('app.candidates.table.risk_band.high', { defaultValue: 'High' })
                : band === 'medium'
                  ? t('app.candidates.table.risk_band.medium', { defaultValue: 'Medium' })
                  : band === 'low'
                    ? t('app.candidates.table.risk_band.low', { defaultValue: 'Low' })
                    : '—'

          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const drivers: string[] = Array.isArray((c as any).risk_drivers) ? (c as any).risk_drivers : []
          const tooltip = drivers.length ? drivers.join(' | ') : undefined
          const badgeCls =
            band === 'critical'
              ? 'bg-red-50 text-red-700 border-red-200'
              : band === 'high'
                ? 'bg-rose-50 text-rose-700 border-rose-200'
                : band === 'medium'
                  ? 'bg-amber-50 text-amber-700 border-amber-200'
                  : band === 'low'
                    ? 'bg-slate-100 text-slate-700 border-slate-200'
                    : 'bg-slate-50 text-slate-500 border-slate-200'

          cellContent =
            typeof score === 'number' ? (
              <div className="flex items-center gap-2">
                <span className={clsx('text-[11px] px-2 py-0.5 rounded border font-medium truncate', badgeCls)} title={tooltip}>
                  {bandLabel}
                </span>
                <span className="text-[11px] text-slate-500">{score}</span>
              </div>
            ) : (
              <span className="text-slate-400">—</span>
            )
        } else if (columnKey === 'created') {
          cellContent = c.created_at ? formatDateSafe(c.created_at, locale) : t('common.labels.not_available')
        } else if (columnKey === 'firstContact') {
          cellContent = c.__extra.firstContactAt ? formatDateSafe(c.__extra.firstContactAt, locale) : t('common.labels.not_available')
        } else if (columnKey === 'preferredChannel') {
          const channel = c.__extra.preferredContact
          const channelKey = channel ?? EMPTY_OPTION_VALUE
          cellContent = preferredChannelLabelMap[channelKey] || t('common.labels.not_available')
        } else if (columnKey === 'inPoland') {
          const inPoland = c.__extra.inPoland
          const key = inPoland === true ? 'yes' : inPoland === false ? 'no' : 'unknown'
          cellContent = inPolandLabelMap[key] || inPolandLabelMap.unknown
        } else if (columnKey === 'polandBasis') {
          const basis = c.__extra.polandStayBasis
          cellContent = basis ? getPolandBasisLabel(basis) : t('common.labels.not_available')
        } else if (columnKey === 'trailerTypes') {
          const trailers = c.__extra.trailerTypes
          if (Array.isArray(trailers) && trailers.length > 0) {
            cellContent = (
              <div className="flex flex-wrap gap-1">
                {trailers.map((label: string, idx: number) => (
                  <span key={idx} className="text-xs bg-slate-100 px-2 py-0.5 rounded">
                    {getTrailerTypeLabel(label)}
                  </span>
                ))}
              </div>
            )
          } else {
            cellContent = t('common.labels.not_available')
          }
        } else if (columnKey === 'reasons') {
          if (reasonTags && reasonTags.length > 0) {
            cellContent = (
              <div className="flex flex-wrap gap-1">
                {reasonTags.slice(0, 2).map((code) => (
                  <span key={code} className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded">
                    {reasonLabelMap.get(code) || code}
                  </span>
                ))}
                {reasonTags.length > 2 && (
                  <span className="text-xs text-slate-500">+{reasonTags.length - 2}</span>
                )}
              </div>
            )
          } else if (fallbackReasons && fallbackReasons.length > 0) {
            cellContent = (
              <div className="flex flex-wrap gap-1">
                {fallbackReasons.slice(0, 2).map((label, idx) => (
                  <span key={idx} className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded">
                    {label}
                  </span>
                ))}
                {fallbackReasons.length > 2 && (
                  <span className="text-xs text-slate-500">+{fallbackReasons.length - 2}</span>
                )}
              </div>
            )
          } else {
            cellContent = t('common.labels.not_available')
          }
        } else if (columnKey === 'intakeKind') {
          const masked = (c as AugmentedCandidate).masked === true
          const kind = (c as AugmentedCandidate).intake_application_kind
          if (masked) {
            cellContent = t('common.labels.not_available')
          } else if (kind === 'client') {
            cellContent = (
              <span
                className="text-[11px] inline-flex items-center rounded-md border border-sky-200 bg-sky-50 px-2 py-0.5 font-semibold text-sky-800"
                title={t('app.candidate_card.labels.client_intake_badge_hint')}
              >
                {t('app.candidate_card.labels.client_intake_badge')}
              </span>
            )
          } else if (kind === 'candidate') {
            cellContent = (
              <span className="text-xs text-slate-600">
                {t('app.candidates.table.intake_kind_standard', { defaultValue: 'Standard' })}
              </span>
            )
          } else {
            cellContent = <span className="text-slate-400">—</span>
          }
        } else if (columnKey === 'tags') {
          const candidateTags = Array.isArray(c.tags) ? c.tags : []
          if (candidateTags.length > 0) {
            cellContent = (
              <div className="flex flex-wrap gap-1">
                {candidateTags.slice(0, 3).map((tag, idx) => (
                  <span key={idx} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded border border-blue-200">
                    {tag}
                  </span>
                ))}
                {candidateTags.length > 3 && (
                  <span className="text-xs text-slate-500">+{candidateTags.length - 3}</span>
                )}
              </div>
            )
          } else {
            cellContent = t('common.labels.not_available')
          }
        } else if (columnKey === 'is_favorite') {
          const isFavorite = c.is_favorite ?? false
          cellContent = (
            <button
              type="button"
              onClick={async (e) => {
                e.stopPropagation()
                if (!c.id || !canManage) return
                try {
                  const newFavoriteValue = !isFavorite
                  await api.patch(`/candidates/${c.id}`, { is_favorite: newFavoriteValue })
                  setItems((prev) => prev.map(item => item.id === c.id ? { ...item, is_favorite: newFavoriteValue } : item))
                  try {
                    window.dispatchEvent(new CustomEvent('candidate-updated', { detail: { candidateId: c.id } }))
                    localStorage.setItem('hf:candidate-updated', JSON.stringify({ candidateId: c.id, timestamp: Date.now() }))
                  } catch {
                    /* ignore */
                  }
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                } catch (err: any) {
                  console.error('[Candidates] Favorite toggle error:', err)
                  if (
                    planLimitModal?.showPlanLimitIfNeeded(
                      err,
                      t('app.candidates.messages.favorite_toggle_failed'),
                    )
                  ) {
                    return
                  }
                  const errorMessage = formatErrorForDisplay(err, { fallback: t('app.candidates.messages.favorite_toggle_failed') })
                  alert(errorMessage)
                }
              }}
              disabled={!canManage}
              className={clsx(
                'text-lg transition-all hover:scale-110',
                isFavorite ? 'text-yellow-400' : 'text-slate-300 hover:text-yellow-300',
                !canManage && 'opacity-50 cursor-not-allowed'
              )}
              title={isFavorite ? t('app.candidate_card.actions.remove_favorite') : t('app.candidate_card.actions.add_favorite')}
            >
              {isFavorite ? <IconBookmarkFilled size={18} /> : <IconBookmark size={18} />}
            </button>
          )
        } else if (columnKey === 'docsStatus') {
          if (docsMeta?.readinessState) {
            const readinessKey = String(docsMeta.readinessState)
            const meta = DOC_READINESS_META[readinessKey] || DOC_READINESS_META.pending
            const docsRequestTitle = t('app.candidate_card.next_action.docs_request_title', {
              defaultValue: 'Request documents',
            })

            // Operational hint: when docs are not ready, the next loop is typically requesting/processing documents.
            const showNextHint = readinessKey !== 'ready' && readinessKey !== 'ordered'

            cellContent = (
              <div className="flex flex-col gap-0.5 min-w-0">
                <span className={clsx('text-xs px-2 py-0.5 rounded', meta.className)}>
                  {t(meta.labelKey)}
                </span>
                {showNextHint ? (
                  <span className="text-[10px] text-slate-500 truncate">→ {docsRequestTitle}</span>
                ) : null}
              </div>
            )
          } else {
            cellContent = t('common.labels.not_available')
          }
        } else if (columnKey === 'docsOrdered') {
          cellContent = docsMeta?.orderDate ? formatDateSafe(docsMeta.orderDate, locale) : t('common.labels.not_available')
        } else if (columnKey === 'docsValid') {
          cellContent = docsMeta?.validFrom ? formatDateSafe(docsMeta.validFrom, locale) : t('common.labels.not_available')
        } else if (columnKey === 'docsFiles') {
          const hasFiles = docsMeta?.hasFiles
          cellContent = hasFiles !== undefined ? (hasFiles ? '✓' : '—') : t('common.labels.not_available')
        }

        return (
          <td
            key={columnKey}
            className={clsx(
              'border-r border-slate-200',
              // Name column: quick actions stay inside the cell (no bleed into neighbors).
              'overflow-hidden',
              // Compact operational defaults: reduce padding in the most-used columns.
              ['stage', 'docsStatus', 'vacancy', 'manager'].includes(columnKey)
                ? 'px-3 py-2.5 align-middle'
                : 'px-4 py-2.5 align-middle',
              isFocused ? 'bg-brand-100' : isWorkPanelRow ? 'bg-brand-50/90' : 'bg-white',
              columnKey === 'name' && "font-medium"
            )}
            style={{
              width: `${getColumnWidth(columnKey)}px`,
              minWidth: `${getColumnWidth(columnKey)}px`,
              maxWidth: `${getColumnWidth(columnKey)}px`
            } as React.CSSProperties}
          >
            <div
              className="min-w-0 overflow-hidden"
              title={typeof cellContent === 'string' ? cellContent : undefined}
            >
              {cellContent}
            </div>
          </td>
        )
      })}
    </>
  )
}
