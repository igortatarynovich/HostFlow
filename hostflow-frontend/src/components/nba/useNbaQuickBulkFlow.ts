import { useCallback, useState } from 'react'

import {
  bulkProcessNewMetaLeads,
  createBulkActivities,
  listCandidatesNoNextAction,
  listLeads,
  listReminders,
} from '../../api/client'
import type { NextActionGroup } from '../../api/nextActions'
import type { LeadListResponse } from '../../api/types'
import type { ReminderRecord } from '../../api/types/notification'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import {
  NBA_CANDIDATE_OVERDUE_REMINDER_STATUSES,
  NBA_QUICK_BATCH_LIMIT,
  NBA_QUICK_PROCESS_NEW_GROUP_IDS,
  NBA_QUICK_REMINDER_GROUP_IDS,
} from './nbaQuickConstants'

export type UseNbaQuickBulkFlowOptions = {
  /** After a successful NBA-origin bulk apply (e.g. refresh snapshot + reload list). */
  onNbaSuccess?: () => void | Promise<void>
  /** After a successful bulk apply from row selection (e.g. clear checkboxes). */
  onSelectionSuccess?: () => void
}

export function useNbaQuickBulkFlow(options: UseNbaQuickBulkFlowOptions = {}) {
  const { onNbaSuccess, onSelectionSuccess } = options
  const { t } = useI18n()
  const { notify } = useToast()
  const planLimitModal = usePlanLimitModal()

  const [bulkActivitiesOpen, setBulkActivitiesOpen] = useState(false)
  const [bulkActivitiesSource, setBulkActivitiesSource] = useState<'selection' | 'nba'>('selection')
  const [nbaBulkEntityIds, setNbaBulkEntityIds] = useState<string[]>([])
  const [nbaBulkEntityType, setNbaBulkEntityType] = useState<'lead' | 'candidate'>('lead')
  const [bulkActivitiesHint, setBulkActivitiesHint] = useState<string | null>(null)
  const [nbaQuickLoadingGroupId, setNbaQuickLoadingGroupId] = useState<string | null>(null)
  const [bulkActivityTitle, setBulkActivityTitle] = useState('')
  const [bulkActivityDueAt, setBulkActivityDueAt] = useState(() =>
    new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16),
  )
  const [bulkActivityOffsetMinutes, setBulkActivityOffsetMinutes] = useState(60)
  const [bulkActivityType, setBulkActivityType] = useState('custom')
  const [bulkActivitiesLoading, setBulkActivitiesLoading] = useState(false)

  const closeBulkActivitiesModal = useCallback(() => {
    if (bulkActivitiesLoading) return
    setBulkActivitiesOpen(false)
    setBulkActivitiesSource('selection')
    setNbaBulkEntityIds([])
    setNbaBulkEntityType('lead')
    setBulkActivitiesHint(null)
  }, [bulkActivitiesLoading])

  const openSelectionBulkActivities = useCallback(() => {
    setBulkActivitiesSource('selection')
    setNbaBulkEntityIds([])
    setNbaBulkEntityType('lead')
    setBulkActivitiesHint(null)
    setBulkActivityTitle(t('app.leads.bulk.activities.default_title'))
    setBulkActivityDueAt(new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16))
    setBulkActivityOffsetMinutes(60)
    setBulkActivitiesOpen(true)
  }, [t])

  const openNbaQuickFollowUp = useCallback(
    async (g: NextActionGroup) => {
      if (g.locked || g.count <= 0 || !NBA_QUICK_REMINDER_GROUP_IDS.has(g.id)) return
      setNbaQuickLoadingGroupId(g.id)
      try {
        let ids: string[] = []
        let bulkEt: 'lead' | 'candidate' = 'lead'

        if (g.id === 'leads_no_next_action' || g.id === 'leads_next_overdue') {
          const res = (await listLeads({
            status: g.query.status || undefined,
            stage: g.query.stage || undefined,
            nextAction: g.query.next_action || undefined,
            limit: NBA_QUICK_BATCH_LIMIT,
            offset: 0,
          })) as LeadListResponse
          ids = (res.items || []).map((l) => l.id).filter(Boolean)
          bulkEt = 'lead'
          if (!ids.length) {
            notify({
              title: t('app.leads.nba.quick_no_leads'),
              variant: 'warning',
            })
            return
          }
        } else if (g.id === 'leads_funnel_weak_step' || g.id === 'leads_funnel_slow_stage') {
          const cr = (g.query.conversion_root || '').trim().toLowerCase()
          const res = (await listLeads({
            status: g.query.status || undefined,
            conversionRoot: cr || undefined,
            limit: NBA_QUICK_BATCH_LIMIT,
            offset: 0,
          })) as LeadListResponse
          ids = (res.items || []).map((l) => l.id).filter(Boolean)
          bulkEt = 'lead'
          if (!ids.length) {
            notify({
              title: t('app.leads.nba.quick_no_leads'),
              variant: 'warning',
            })
            return
          }
        } else if (g.id === 'candidates_no_next_action') {
          const res = (await listCandidatesNoNextAction({
            limit: NBA_QUICK_BATCH_LIMIT,
            offset: 0,
          })) as { items?: Array<{ id?: string }> }
          ids = (res.items || []).map((c) => String(c.id || '').trim()).filter(Boolean)
          bulkEt = 'candidate'
          if (!ids.length) {
            notify({
              title: t('app.leads.nba.quick_no_candidates'),
              variant: 'warning',
            })
            return
          }
        } else if (g.id === 'candidates_next_overdue') {
          const raw = (await listReminders({
            assigneeScope: 'mine',
            entityType: 'candidate',
            status: [...NBA_CANDIDATE_OVERDUE_REMINDER_STATUSES],
            dueTo: new Date().toISOString(),
            limit: 200,
          })) as { items?: ReminderRecord[] }
          const seen = new Set<string>()
          for (const r of raw.items || []) {
            const eid = String(r.entity_id || '').trim()
            if (!eid || r.entity_type !== 'candidate') continue
            if (seen.has(eid)) continue
            seen.add(eid)
            ids.push(eid)
            if (ids.length >= NBA_QUICK_BATCH_LIMIT) break
          }
          bulkEt = 'candidate'
          if (!ids.length) {
            notify({
              title: t('app.leads.nba.quick_no_candidates'),
              variant: 'warning',
            })
            return
          }
        } else {
          return
        }

        setBulkActivitiesSource('nba')
        setNbaBulkEntityType(bulkEt)
        setNbaBulkEntityIds(ids)
        setBulkActivityTitle(
          g.id === 'leads_funnel_weak_step' || g.id === 'leads_funnel_slow_stage'
            ? t('app.leads.nba.quick_title_funnel_insight')
            : g.id === 'leads_next_overdue'
              ? t('app.leads.nba.quick_title_overdue')
              : g.id === 'leads_no_next_action'
                ? t('app.leads.nba.quick_title_no_next')
                : g.id === 'candidates_next_overdue'
                  ? t('app.leads.nba.quick_title_candidate_overdue')
                  : t('app.leads.nba.quick_title_candidate_no_next'),
        )
        setBulkActivityType('follow_up')
        setBulkActivityDueAt(new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().slice(0, 16))
        setBulkActivityOffsetMinutes(60)
        setBulkActivitiesHint(
          t('app.leads.nba.quick_batch_hint', {
            values: { count: ids.length, max: NBA_QUICK_BATCH_LIMIT },
          }),
        )
        setBulkActivitiesOpen(true)
      } catch (err: unknown) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.nba.quick_action_failed'))) {
          return
        }
        const info = getFriendlyErrorInfo(err, t('app.leads.nba.quick_action_failed'), t)
        notify({
          title: info.title,
          description: [info.detail, info.hint].filter(Boolean).join(' '),
          variant: 'error',
        })
      } finally {
        setNbaQuickLoadingGroupId(null)
      }
    },
    [notify, planLimitModal, t],
  )

  const openNbaQuickProcessNewLeads = useCallback(
    async (g: NextActionGroup) => {
      if (!NBA_QUICK_PROCESS_NEW_GROUP_IDS.has(g.id) || g.count <= 0) return
      setNbaQuickLoadingGroupId(g.id)
      try {
        const maxItems = Math.min(NBA_QUICK_BATCH_LIMIT, Math.max(1, g.count))
        const res = await bulkProcessNewMetaLeads({ max_items: maxItems })
        await onNbaSuccess?.()
        const ok = res.succeeded
        const fail = res.failed
        const att = res.attempted
        if (fail > 0 && ok === 0) {
          notify({
            title: t('app.leads.nba.process_new_error_title'),
            description: t('app.leads.nba.process_new_done', { values: { ok, fail, attempted: att } }),
            variant: 'error',
          })
        } else if (fail > 0) {
          notify({
            title: t('app.leads.nba.process_new_partial_title'),
            description: t('app.leads.nba.process_new_done', { values: { ok, fail, attempted: att } }),
            variant: 'warning',
          })
        } else {
          notify({
            title: t('app.leads.nba.process_new_success_title'),
            description: t('app.leads.nba.process_new_done', { values: { ok, fail, attempted: att } }),
            variant: 'success',
          })
        }
      } catch (err: unknown) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.nba.quick_action_failed'))) {
          return
        }
        const info = getFriendlyErrorInfo(err, t('app.leads.nba.quick_action_failed'), t)
        notify({
          title: info.title,
          description: [info.detail, info.hint].filter(Boolean).join(' '),
          variant: 'error',
        })
      } finally {
        setNbaQuickLoadingGroupId(null)
      }
    },
    [notify, onNbaSuccess, planLimitModal, t],
  )

  const applyBulkActivities = useCallback(
    async (selectionLeadIds: string[]) => {
      const ids = bulkActivitiesSource === 'nba' ? nbaBulkEntityIds : selectionLeadIds
      const wasNba = bulkActivitiesSource === 'nba'
      const entityType = wasNba ? nbaBulkEntityType : 'lead'
      if (ids.length === 0 || !bulkActivityTitle.trim() || !bulkActivityDueAt) return
      setBulkActivitiesLoading(true)
      try {
        const due = new Date(bulkActivityDueAt)
        const remindAt = new Date(due.getTime() - bulkActivityOffsetMinutes * 60 * 1000)
        const res = await createBulkActivities({
          title: bulkActivityTitle.trim(),
          description: '',
          type: bulkActivityType,
          entity_type: entityType,
          entity_ids: ids,
          due_at: due.toISOString(),
          remind_at: remindAt.toISOString(),
          source: wasNba ? 'nba_quick' : 'bulk',
          priority: 'normal',
        })
        const results: Array<{ entity_id?: string; ok?: boolean }> = Array.isArray(res?.results) ? res.results : []
        const failures = results.filter((r) => r && r.ok === false)
        setBulkActivitiesOpen(false)
        setBulkActivitiesSource('selection')
        setNbaBulkEntityIds([])
        setNbaBulkEntityType('lead')
        setBulkActivitiesHint(null)
        if (failures.length > 0) {
          notify({
            title: t('app.leads.bulk.activities.partial'),
            description: `${failures.length} / ${ids.length}`,
            variant: 'error',
          })
        } else {
          notify({ title: t('app.leads.bulk.activities.created'), variant: 'success' })
          if (wasNba) {
            await onNbaSuccess?.()
          } else {
            onSelectionSuccess?.()
          }
        }
      } catch (err: unknown) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.bulk.activities.failed'))) {
          return
        }
        const detail =
          (err as { response?: { data?: { detail?: unknown } }; message?: string })?.response?.data?.detail ??
          (err as { message?: string })?.message ??
          'Failed'
        notify({
          title: t('app.leads.bulk.activities.failed'),
          description: String(detail),
          variant: 'error',
        })
      } finally {
        setBulkActivitiesLoading(false)
      }
    },
    [
      bulkActivitiesSource,
      bulkActivityDueAt,
      bulkActivityOffsetMinutes,
      bulkActivityTitle,
      bulkActivityType,
      nbaBulkEntityIds,
      nbaBulkEntityType,
      notify,
      onNbaSuccess,
      onSelectionSuccess,
      planLimitModal,
      t,
    ],
  )

  return {
    bulkActivitiesOpen,
    bulkActivitiesLoading,
    bulkActivitiesHint,
    bulkActivityTitle,
    setBulkActivityTitle,
    bulkActivityDueAt,
    setBulkActivityDueAt,
    bulkActivityOffsetMinutes,
    setBulkActivityOffsetMinutes,
    bulkActivityType,
    setBulkActivityType,
    nbaQuickLoadingGroupId,
    openNbaQuickFollowUp,
    openNbaQuickProcessNewLeads,
    openSelectionBulkActivities,
    closeBulkActivitiesModal,
    applyBulkActivities,
  }
}
