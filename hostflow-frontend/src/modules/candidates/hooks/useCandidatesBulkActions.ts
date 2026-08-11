// src/modules/candidates/hooks/useCandidatesBulkActions.ts
//
// Bulk-action handlers for the Candidates page (stage / manager / vacancy /
// handoff / tags / activities / delete). Extracted from
// `src/pages/Candidates.tsx` as Phase 1 #4 step 3 of the god-component split.
//
// All seven handlers share the same shape:
//   1. resolve selected ids,
//   2. set "loading" sentinel for the matching bulk panel,
//   3. POST to backend,
//   4. handle partial failures (typed error codes for stage gate, RODO,
//      handoff-docs, contact-attempt, vacancy gate, pipeline-docs, risk-gate),
//   5. invalidate the in-memory + localStorage list cache and refetch.
//
// The hook receives a single `ctx` object with everything it needs from the
// page (state, setters, derived helpers). This keeps the public surface
// small and stable: callers only have to pass `ctx` once and destructure
// the returned action map.
//
// See `docs/HOSTFLOW_AUDIT_AND_PLAN.md` (Phase 1 #4).

import type { MutableRefObject } from 'react'

import api, { createBulkActivities } from '../../../api/client'
import { createBulkHandoff } from '../../../api/handoffs'
import type { MetaStages } from '../../../api/types'
import type { PlanLimitModalContextValue } from '../../../contexts/PlanLimitModalContext'
import { formatErrorForDisplay, getErrorInfo } from '../../../utils/errorHandling'
import type { TranslateFn } from '../../../i18n'
import { candidateListCache } from '../internal'
import type { UICandidate } from '../types'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type BulkLoadingKind =
  | 'stage'
  | 'manager'
  | 'vacancy'
  | 'handoff'
  | 'tags'
  | 'activities'
  | 'delete'
  | null

export interface CandidatesBulkActionsCtx {
  // ---- selection & list ------------------------------------------------
  allSelected: () => string[]
  items: UICandidate[]
  recentlyUpdatedIdsRef: MutableRefObject<Map<string, number>>

  // ---- list reload + cache invalidation -------------------------------
  load: (opts?: { force?: boolean; allowCache?: boolean }) => Promise<void>
  cacheKey: string
  listStorageKey: string

  // ---- meta / i18n / plan-limit guard ----------------------------------
  meta: MetaStages | null | undefined
  t: TranslateFn
  planLimitModal: PlanLimitModalContextValue | null | undefined

  // ---- shared loading sentinel ----------------------------------------
  setBulkOperationLoading: (kind: BulkLoadingKind) => void

  // ---- per-modal state values + setters --------------------------------
  // stage
  bulkStage: string
  bulkReasons: string[]
  setBulkOpen: (b: boolean) => void
  setBulkReasons: (r: string[]) => void
  setChecked: (m: Record<string, boolean>) => void

  // manager
  bulkManagerId: string
  preferredManagerId: string
  setBulkManagerOpen: (b: boolean) => void
  setBulkManagerId: (id: string) => void

  // vacancy
  bulkVacancyId: string
  setBulkVacancyOpen: (b: boolean) => void
  setBulkVacancyId: (id: string) => void

  // handoff
  bulkHandoffClientId: string
  setBulkHandoffOpen: (b: boolean) => void
  setBulkHandoffClientId: (id: string) => void

  // tags
  bulkTagsList: string
  bulkTagsOperation: 'add' | 'remove'
  setBulkTagsOpen: (b: boolean) => void
  setBulkTagsList: (s: string) => void

  // activities
  bulkActivityTitle: string
  bulkActivityDueAt: string
  bulkActivityOffsetMinutes: number
  bulkActivityType: string
  setBulkActivitiesOpen: (b: boolean) => void

  // delete
  setBulkDeleteOpen: (b: boolean) => void
}

export interface CandidatesBulkActions {
  doBulkActivities: () => Promise<void>
  doBulk: () => Promise<void>
  doBulkAssign: () => Promise<void>
  doBulkAssignVacancy: () => Promise<void>
  doBulkHandoff: () => Promise<void>
  doBulkTags: () => Promise<void>
  doBulkDelete: () => Promise<void>
}

// ---------------------------------------------------------------------------
// Implementation
// ---------------------------------------------------------------------------

/** Best-effort localStorage cleanup used by every bulk handler after success. */
function invalidateCachesFor(ctx: CandidatesBulkActionsCtx): void {
  candidateListCache.delete(ctx.cacheKey)
  try {
    localStorage.removeItem(ctx.listStorageKey)
  } catch {
    /* ignore */
  }
}

/** Parse `error` field that may be a JSON string or a plain object. */
function parseErrorObject(raw: unknown): Record<string, unknown> | null {
  if (raw && typeof raw === 'object') return raw as Record<string, unknown>
  if (typeof raw !== 'string') return null
  const trimmed = raw.trim()
  if (!trimmed.startsWith('{')) return null
  try {
    const parsed = JSON.parse(trimmed)
    return parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : null
  } catch {
    return null
  }
}

/** Build a "name: reason" diagnostic line list for partial-failure alerts. */
function buildFailureDetails(
  ctx: CandidatesBulkActionsCtx,
  failures: Array<{ candidate_id?: string; error?: string }>,
): string {
  return failures
    .map((f) => {
      const candidateId = f.candidate_id || ''
      const candidate = ctx.items.find((c) => c.id === candidateId)
      const name = candidate
        ? `${candidate.first_name} ${candidate.last_name}`.trim() || candidate.short_id || candidateId
        : candidateId
      const reason = f.error || 'unknown error'
      return `${name}: ${reason}`
    })
    .filter(Boolean)
    .join('\n')
}

export function useCandidatesBulkActions(ctx: CandidatesBulkActionsCtx): CandidatesBulkActions {
  // NOTE: handlers intentionally close over the latest `ctx` snapshot per
  // render — that's fine because they're invoked from event handlers, not
  // memoised, and React already passes the most recent closure on each call.

  const doBulkActivities = async () => {
    const ids = ctx.allSelected()
    if (ids.length === 0 || !ctx.bulkActivityTitle.trim() || !ctx.bulkActivityDueAt) return
    ctx.setBulkOperationLoading('activities')
    try {
      const due = new Date(ctx.bulkActivityDueAt)
      const remindAt = new Date(due.getTime() - ctx.bulkActivityOffsetMinutes * 60 * 1000)
      const res = await createBulkActivities({
        title: ctx.bulkActivityTitle.trim(),
        description: '',
        type: ctx.bulkActivityType,
        entity_type: 'candidate',
        entity_ids: ids,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        source: 'bulk',
        priority: 'normal',
      })
      const results: Array<{ entity_id?: string; ok?: boolean; error?: string }> = Array.isArray(res?.results)
        ? res.results
        : []
      const failures = results.filter((r) => r && r.ok === false)
      ctx.setBulkActivitiesOpen(false)
      if (failures.length > 0) {
        alert(
          ctx.t('app.candidates.messages.bulk_activities_partial', {
            defaultValue: 'Created with errors: {{failed}} failed out of {{total}}.',
            values: { failed: failures.length, total: ids.length },
          }),
        )
      } else {
        ctx.setChecked({})
      }
    } catch (e: unknown) {
      if (
        ctx.planLimitModal?.showPlanLimitIfNeeded(
          e,
          ctx.t('app.candidates.messages.bulk_activities_failed', { defaultValue: 'Failed to create activities' }),
        )
      ) {
        return
      }
      alert(
        formatErrorForDisplay(e, {
          fallback: ctx.t('app.candidates.messages.bulk_activities_failed', {
            defaultValue: 'Failed to create activities',
          }),
          includeStatusCode: false,
        }),
      )
    } finally {
      ctx.setBulkOperationLoading(null)
    }
  }

  const doBulk = async () => {
    const ids = ctx.allSelected()
    if (ids.length === 0 || !ctx.bulkStage) return
    const reasonOptions = ctx.meta?.reason_choices?.[ctx.bulkStage] ?? []
    if (reasonOptions.length > 0 && ctx.bulkReasons.length === 0) {
      // reasonOptions is `{code; label}[]` per MetaStages; we only care about
      // length here, not the option shape.
      alert(ctx.t('app.candidates.messages.reason_required'))
      return
    }
    ctx.setBulkOperationLoading('stage')
    try {
      const payload: Record<string, unknown> = { candidate_ids: ids, stage: ctx.bulkStage }
      if (reasonOptions.length > 0) {
        payload.status_reason = ctx.bulkReasons
      }
      const { data } = await api.post('/candidates/bulk-stage', payload)
      const results: Array<{ candidate_id?: string; ok?: boolean; error?: string }> = Array.isArray(data) ? data : []
      const failures = results.filter((item) => item && item.ok === false)
      const successes = results.filter((item) => item && item.ok === true)

      ctx.setBulkOpen(false)
      ctx.setBulkReasons([])

      if (failures.length > 0) {
        const failedIds = new Set(
          failures.map((item) => String(item?.candidate_id || '').trim()).filter(Boolean),
        )
        const nextChecked: Record<string, boolean> = {}
        for (const failedId of failedIds) {
          nextChecked[failedId] = true
        }
        ctx.setChecked(nextChecked)

        const rodoBlockedCount = failures.filter((item) =>
          String(item?.error || '').toLowerCase().includes('rodo must be sent'),
        ).length
        const handoffDocsFailures = failures.filter((item) => {
          const parsed = parseErrorObject(item?.error)
          if (String(parsed?.code || '') === 'handoff_docs_incomplete') return true
          return String(item?.error || '').toLowerCase().includes('handoff_docs_incomplete')
        })
        const contactAttemptFailures = failures.filter((item) => {
          const parsed = parseErrorObject(item?.error)
          return String(parsed?.code || '') === 'stage_blocked_by_contact_attempt'
        })
        const vacancyGateFailures = failures.filter((item) => {
          const parsed = parseErrorObject(item?.error)
          return String(parsed?.code || '') === 'stage_blocked_by_vacancy'
        })
        const pipelineDocFailures = failures.filter((item) => {
          const parsed = parseErrorObject(item?.error)
          return String(parsed?.code || '') === 'stage_blocked_by_documents'
        })
        const riskGateFailures = failures.filter((item) => {
          const parsed = parseErrorObject(item?.error)
          return String(parsed?.code || '') === 'stage_blocked_by_risk_gate'
        })
        if (rodoBlockedCount > 0) {
          alert(
            ctx.t('app.candidates.messages.bulk_stage_rodo_blocked', {
              values: { rodo: rodoBlockedCount, total: failures.length },
            }),
          )
        } else if (handoffDocsFailures.length > 0) {
          const firstParsed = parseErrorObject(handoffDocsFailures[0]?.error)
          const missingFromFirst = Array.isArray(firstParsed?.missing_types)
            ? (firstParsed?.missing_types as unknown[])
                .map((code) => String(code || '').trim())
                .filter(Boolean)
            : []
          const missingLabels = missingFromFirst
            .map((code: string) => ctx.t(`admin.documents.types.${code}`, { defaultValue: code }))
            .join(', ')
          alert(
            ctx.t('app.candidates.messages.bulk_stage_handoff_docs_blocked', {
              values: {
                docs: handoffDocsFailures.length,
                total: failures.length,
                missing: missingLabels || '—',
              },
            }),
          )
        } else if (contactAttemptFailures.length > 0) {
          alert(
            ctx.t('app.candidates.messages.bulk_stage_contact_attempt_blocked', {
              defaultValue:
                '{contact} candidate(s) need a logged contact attempt (client policy) out of {total} failures. Open cards, register an attempt, then retry.',
              values: { contact: contactAttemptFailures.length, total: failures.length },
            }),
          )
        } else if (vacancyGateFailures.length > 0) {
          alert(
            ctx.t('app.candidates.messages.bulk_stage_vacancy_blocked', {
              defaultValue:
                '{vacancy} candidate(s) must be linked to a vacancy before that stage change ({total} failures). Assign vacancy on the card, then retry.',
              values: { vacancy: vacancyGateFailures.length, total: failures.length },
            }),
          )
        } else if (pipelineDocFailures.length > 0) {
          alert(
            ctx.t('app.candidates.messages.bulk_stage_pipeline_docs_blocked', {
              defaultValue:
                '{docs} candidate(s) are blocked by required documents ({total} failures). Fix documents on the card, then retry.',
              values: { docs: pipelineDocFailures.length, total: failures.length },
            }),
          )
        } else if (riskGateFailures.length > 0) {
          alert(
            ctx.t('app.candidates.messages.bulk_stage_risk_gate_blocked', {
              defaultValue:
                '{risk} candidate(s) are blocked by risk policy: add a next-action reminder or adjust risk_model_v1.stage_gate ({total} failures).',
              values: { risk: riskGateFailures.length, total: failures.length },
            }),
          )
        } else {
          alert(
            ctx.t('app.candidates.messages.bulk_stage_partial', {
              values: { failed: failures.length, total: ids.length },
            }),
          )
        }
      } else {
        ctx.setChecked({})
      }

      if (successes.length > 0) {
        const now = Date.now()
        successes.forEach((item) => {
          const cid = String(item?.candidate_id || '').trim()
          if (cid) ctx.recentlyUpdatedIdsRef.current.set(cid, now)
        })
        invalidateCachesFor(ctx)
        await ctx.load({ force: true, allowCache: false })
      }
    } catch (e: unknown) {
      if (
        ctx.planLimitModal?.showPlanLimitIfNeeded(
          e,
          ctx.t('app.candidates.messages.bulk_stage_failed', { defaultValue: 'Failed to change stage.' }),
        )
      ) {
        return
      }
      const errorMessage = formatErrorForDisplay(e, {
        fallback: ctx.t('app.candidates.messages.bulk_stage_failed', { defaultValue: 'Failed to change stage.' }),
        includeStatusCode: false,
      })
      console.error('[Candidates] Bulk stage update failed:', getErrorInfo(e))
      alert(errorMessage)
    } finally {
      ctx.setBulkOperationLoading(null)
    }
  }

  const doBulkAssign = async () => {
    const ids = ctx.allSelected()
    if (ids.length === 0 || !ctx.bulkManagerId) return
    ctx.setBulkOperationLoading('manager')
    try {
      const { data } = await api.post('/candidates/bulk-manager', {
        candidate_ids: ids,
        manager_id: ctx.bulkManagerId,
      })
      const results: Array<{ candidate_id?: string; ok?: boolean; error?: string }> = Array.isArray(data) ? data : []
      const failures = results.filter((item) => item && item.ok === false)
      const successes = results.filter((item) => item && item.ok === true)

      const now = Date.now()
      successes.forEach((result) => {
        if (result.candidate_id) {
          ctx.recentlyUpdatedIdsRef.current.set(result.candidate_id, now)
        }
      })
      ids.forEach((id) => {
        ctx.recentlyUpdatedIdsRef.current.set(id, now)
      })

      if (failures.length) {
        const labelById = new Map(
          ctx.items.map((c) => [c.id, `${c.first_name} ${c.last_name}`.trim() || c.short_id || c.id]),
        )
        const details = failures
          .map((f) => {
            const name = f.candidate_id ? labelById.get(f.candidate_id) || f.candidate_id : ''
            return `${name}: ${f.error || 'failed'}`
          })
          .join('\n')
        const errorMessage = `${ctx.t('app.candidates.messages.bulk_manager_partial', {
          values: { count: failures.length },
        })}\n${details}`
        console.warn('[Candidates] Bulk manager assignment partial failure:', failures)
        alert(errorMessage)
        invalidateCachesFor(ctx)
        await ctx.load({ force: true, allowCache: false })
        return
      }
      ctx.setBulkManagerOpen(false)
      ctx.setChecked({})
      ctx.setBulkManagerId(ctx.preferredManagerId)
      invalidateCachesFor(ctx)
      await ctx.load({ force: true, allowCache: false })
    } catch (e: unknown) {
      if (
        ctx.planLimitModal?.showPlanLimitIfNeeded(
          e,
          ctx.t('app.candidates.messages.bulk_manager_failed', { defaultValue: 'Failed to assign manager.' }),
        )
      ) {
        return
      }
      const errorMessage = formatErrorForDisplay(e, {
        fallback: ctx.t('app.candidates.messages.bulk_manager_failed', { defaultValue: 'Failed to assign manager.' }),
        includeStatusCode: false,
      })
      console.error('[Candidates] Bulk manager assignment failed:', getErrorInfo(e))
      alert(errorMessage)
    } finally {
      ctx.setBulkOperationLoading(null)
    }
  }

  const doBulkAssignVacancy = async () => {
    const ids = ctx.allSelected()
    if (ids.length === 0 || !ctx.bulkVacancyId) return
    ctx.setBulkOperationLoading('vacancy')
    try {
      const results = await Promise.allSettled(
        ids.map((id) => api.patch(`/candidates/${id}`, { vacancy_id: ctx.bulkVacancyId })),
      )
      const failures = results.filter((r) => r.status === 'rejected')
      if (failures.length > 0) {
        const failureCount = failures.length
        const errorDetails = failures
          .map((f, idx) => {
            const candidateId = ids[idx]
            const candidate = ctx.items.find((c) => c.id === candidateId)
            const name = candidate
              ? `${candidate.first_name} ${candidate.last_name}`.trim() || candidate.short_id || candidateId
              : candidateId
            const reason =
              f.status === 'rejected'
                ? (f.reason as { response?: { data?: { detail?: string } }; message?: string })?.response?.data
                    ?.detail ||
                  (f.reason as { message?: string })?.message ||
                  'unknown error'
                : ''
            return `${name}: ${reason}`
          })
          .filter(Boolean)
          .join('\n')
        console.warn('[Candidates] Bulk vacancy assignment partial failure:', failures)
        alert(
          `${
            ctx.t('app.candidates.messages.bulk_vacancy_partial', {
              defaultValue: 'Failed to update {count} of {total} candidates.',
              values: { count: failureCount, total: ids.length },
            })
          }\n${errorDetails}`,
        )
      }
      ctx.setBulkVacancyOpen(false)
      ctx.setChecked({})
      ctx.setBulkVacancyId('')

      const now = Date.now()
      const successfulIds = ids.filter((_, idx) => results[idx]?.status === 'fulfilled')
      successfulIds.forEach((id) => {
        ctx.recentlyUpdatedIdsRef.current.set(id, now)
      })
      invalidateCachesFor(ctx)
      await ctx.load({ force: true, allowCache: false })
    } catch (e: unknown) {
      if (
        ctx.planLimitModal?.showPlanLimitIfNeeded(
          e,
          ctx.t('app.candidates.messages.bulk_vacancy_failed', { defaultValue: 'Failed to assign vacancy.' }),
        )
      ) {
        return
      }
      const errorMessage = formatErrorForDisplay(e, {
        fallback: ctx.t('app.candidates.messages.bulk_vacancy_failed', { defaultValue: 'Failed to assign vacancy.' }),
        includeStatusCode: false,
      })
      console.error('[Candidates] Bulk vacancy assignment failed:', getErrorInfo(e))
      alert(errorMessage)
    } finally {
      ctx.setBulkOperationLoading(null)
    }
  }

  const doBulkHandoff = async () => {
    const ids = ctx.allSelected()
    if (ids.length === 0 || !ctx.bulkHandoffClientId) return
    ctx.setBulkOperationLoading('handoff')
    try {
      const result = await createBulkHandoff({
        candidate_ids: ids,
        client_company_id: ctx.bulkHandoffClientId,
      })
      if (result.failed > 0) {
        const details = result.errors
          .slice(0, 5)
          .map((e) => `${e.candidate_id}: ${e.error}`)
          .join('\n')
        alert(
          (ctx.t('app.candidates.modals.handoff.partial', {
            values: { created: result.created, failed: result.failed, total: ids.length },
            defaultValue: `Przekazano ${result.created} z ${ids.length}. Nie udało się: ${result.failed}.`,
          }) as string) + (details ? `\n\n${details}` : ''),
        )
      }
      if (result.created > 0) {
        ctx.setBulkHandoffOpen(false)
        ctx.setChecked({})
        ctx.setBulkHandoffClientId('')
        const now = Date.now()
        ids.forEach((id) => ctx.recentlyUpdatedIdsRef.current.set(id, now))
        invalidateCachesFor(ctx)
        await ctx.load({ force: true, allowCache: false })
      }
    } catch (e: unknown) {
      if (
        ctx.planLimitModal?.showPlanLimitIfNeeded(
          e,
          ctx.t('app.candidates.modals.handoff.failed', { defaultValue: 'Nie udało się przekazać do klienta' }),
        )
      ) {
        return
      }
      const errorMessage = formatErrorForDisplay(e, {
        fallback: ctx.t('app.candidates.modals.handoff.failed', {
          defaultValue: 'Nie udało się przekazać do klienta',
        }),
        includeStatusCode: false,
      })
      alert(errorMessage)
    } finally {
      ctx.setBulkOperationLoading(null)
    }
  }

  const doBulkTags = async () => {
    const ids = ctx.allSelected()
    if (ids.length === 0 || !ctx.bulkTagsList.trim()) return
    const tagsToProcess = ctx.bulkTagsList
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    if (tagsToProcess.length === 0) return
    ctx.setBulkOperationLoading('tags')
    try {
      const results = await Promise.allSettled(
        ids.map(async (id) => {
          const candidate = ctx.items.find((c) => c.id === id)
          const currentTags = Array.isArray(candidate?.tags) ? candidate.tags : []
          let newTags: string[]
          if (ctx.bulkTagsOperation === 'add') {
            newTags = [...new Set([...currentTags, ...tagsToProcess])].sort()
          } else {
            newTags = currentTags.filter((tag) => !tagsToProcess.includes(tag))
          }
          return api.patch(`/candidates/${id}`, { tags: newTags })
        }),
      )
      const failures = results.filter((r) => r.status === 'rejected')
      if (failures.length > 0) {
        const failureCount = failures.length
        const errorDetails = failures
          .map((f, idx) => {
            const candidateId = ids[idx]
            const candidate = ctx.items.find((c) => c.id === candidateId)
            const name = candidate
              ? `${candidate.first_name} ${candidate.last_name}`.trim() || candidate.short_id || candidateId
              : candidateId
            const reason =
              f.status === 'rejected'
                ? (f.reason as { response?: { data?: { detail?: string } }; message?: string })?.response?.data
                    ?.detail ||
                  (f.reason as { message?: string })?.message ||
                  'unknown error'
                : ''
            return `${name}: ${reason}`
          })
          .filter(Boolean)
          .join('\n')
        console.warn('[Candidates] Bulk tags update partial failure:', failures)
        alert(
          `${
            ctx.t('app.candidates.messages.bulk_tags_partial', {
              defaultValue: 'Failed to update tags for {count} of {total} candidates.',
              values: { count: failureCount, total: ids.length },
            })
          }\n${errorDetails}`,
        )
      }
      ctx.setBulkTagsOpen(false)
      ctx.setChecked({})
      ctx.setBulkTagsList('')

      const now = Date.now()
      const successfulIds = ids.filter((_, idx) => results[idx]?.status === 'fulfilled')
      successfulIds.forEach((id) => {
        ctx.recentlyUpdatedIdsRef.current.set(id, now)
      })
      invalidateCachesFor(ctx)
      await ctx.load({ force: true, allowCache: false })
    } catch (e: unknown) {
      if (
        ctx.planLimitModal?.showPlanLimitIfNeeded(
          e,
          ctx.t('app.candidates.messages.bulk_tags_failed', { defaultValue: 'Failed to update tags.' }),
        )
      ) {
        return
      }
      const errorMessage = formatErrorForDisplay(e, {
        fallback: ctx.t('app.candidates.messages.bulk_tags_failed', { defaultValue: 'Failed to update tags.' }),
        includeStatusCode: false,
      })
      console.error('[Candidates] Bulk tags update failed:', getErrorInfo(e))
      alert(errorMessage)
    } finally {
      ctx.setBulkOperationLoading(null)
    }
  }

  const doBulkDelete = async () => {
    const ids = ctx.allSelected()
    if (ids.length === 0) return
    ctx.setBulkOperationLoading('delete')
    try {
      const { data: results } = await api.post('/candidates/bulk-delete', { candidate_ids: ids })
      const failures = (results as Array<{ candidate_id?: string; ok?: boolean; error?: string }>).filter(
        (r) => !r.ok,
      )
      if (failures.length > 0) {
        const failureCount = failures.length
        const errorDetails = buildFailureDetails(ctx, failures)
        console.warn('[Candidates] Bulk delete operation partial failure:', failures)
        alert(
          `${
            ctx.t('app.candidates.messages.bulk_delete_partial', {
              defaultValue: 'Failed to delete {count} of {total} candidates.',
              values: { count: failureCount, total: ids.length },
            })
          }\n${errorDetails}`,
        )
      }
      ctx.setBulkDeleteOpen(false)
      ctx.setChecked({})
      invalidateCachesFor(ctx)
      await ctx.load({ force: true, allowCache: false })
    } catch (e: unknown) {
      if (
        ctx.planLimitModal?.showPlanLimitIfNeeded(
          e,
          ctx.t('app.candidates.messages.bulk_delete_failed', { defaultValue: 'Failed to delete candidates.' }),
        )
      ) {
        return
      }
      const errorMessage = formatErrorForDisplay(e, {
        fallback: ctx.t('app.candidates.messages.bulk_delete_failed', { defaultValue: 'Failed to delete candidates.' }),
        includeStatusCode: false,
      })
      console.error('[Candidates] Bulk delete operation failed:', getErrorInfo(e))
      alert(errorMessage)
    } finally {
      ctx.setBulkOperationLoading(null)
    }
  }

  return {
    doBulkActivities,
    doBulk,
    doBulkAssign,
    doBulkAssignVacancy,
    doBulkHandoff,
    doBulkTags,
    doBulkDelete,
  }
}
