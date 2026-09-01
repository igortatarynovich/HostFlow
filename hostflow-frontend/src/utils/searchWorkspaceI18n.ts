import type { SearchDayItem } from '../api/searchWorkspace'
import type { TranslateFn } from '../i18n'

const KNOWN_COPY_CODES = new Set([
  'candidates_awaiting_call',
  'candidates_missing_docs',
  'candidates_stale_interview',
  'acquisition_launch',
  'acquisition_expand',
  'search_filled',
  'audience_setup',
  'wait_leads',
  'search_near_goal',
  'later_setup',
  'later_channel',
  'cpl_up',
  'no_recent_leads',
  'spend_no_leads',
])

export function resolveSearchDayCopyCode(item: Pick<SearchDayItem, 'id' | 'kind'>): string {
  const kind = String(item.kind || '').trim()
  if (KNOWN_COPY_CODES.has(kind)) return kind
  const id = String(item.id || '').trim()
  if (KNOWN_COPY_CODES.has(id)) return id
  if (id.startsWith('later_setup_')) return 'later_setup'
  if (id.startsWith('later_channel_')) return 'later_channel'
  if (kind) return kind
  return id
}

export function searchWorkspaceStatusLabel(
  t: TranslateFn,
  vacancyStatus?: string | null,
  isArchived?: boolean | null,
): string {
  if (isArchived) return t('app.search_workspace.status.archived')
  const status = String(vacancyStatus || '').trim().toLowerCase()
  if (status === 'closed' || status === 'filled' || status === 'cancelled') {
    return t(`app.vacancies.list.status.${status}`)
  }
  if (status === 'on_hold' || status === 'paused') {
    return t('app.search_workspace.status.on_hold')
  }
  return t('app.search_workspace.status.active')
}

export function localizeSearchDayItem(
  item: SearchDayItem,
  t: TranslateFn,
  ctx?: { searchTitle?: string },
): SearchDayItem {
  const code = resolveSearchDayCopyCode(item)
  if (!KNOWN_COPY_CODES.has(code)) return item

  const count = Number(item.count ?? 0)
  const name = String(item.activity_name || '').trim() || t('app.search_pulse.activity_fallback')
  const channel = String(item.channel || '').trim()
  const title = String(ctx?.searchTitle || '').trim()
  const localized: SearchDayItem = { ...item }

  switch (code) {
    case 'candidates_awaiting_call': {
      const one = count === 1
      localized.headline = t(
        one
          ? 'app.search_pulse.candidates_awaiting_call.headline_one'
          : 'app.search_pulse.candidates_awaiting_call.headline_many',
        { values: { count } },
      )
      localized.message = t(
        one
          ? 'app.search_pulse.candidates_awaiting_call.message_one'
          : 'app.search_pulse.candidates_awaiting_call.message_many',
        { values: { count } },
      )
      localized.reason = t('app.search_pulse.reason.candidates_awaiting_call')
      localized.action_label = t('app.search_pulse.action.start')
      return localized
    }
    case 'candidates_missing_docs': {
      localized.headline = t('app.search_pulse.candidates_missing_docs.headline')
      localized.message = t(
        count === 1
          ? 'app.search_pulse.candidates_missing_docs.message_one'
          : 'app.search_pulse.candidates_missing_docs.message_many',
        { values: { count } },
      )
      localized.reason = t('app.search_pulse.reason.candidates_missing_docs')
      localized.action_label = t('app.search_pulse.action.start')
      return localized
    }
    case 'candidates_stale_interview': {
      localized.headline = t('app.search_pulse.candidates_stale_interview.headline')
      localized.message = t('app.search_pulse.candidates_stale_interview.message', { values: { count } })
      localized.reason = t('app.search_pulse.reason.candidates_stale_interview')
      localized.action_label = t('app.search_pulse.action.start')
      return localized
    }
    case 'acquisition_launch': {
      localized.headline = t('app.search_pulse.acquisition_launch.headline')
      localized.message = t('app.search_pulse.acquisition_launch.message', { values: { title } })
      localized.reason = t('app.search_pulse.reason.acquisition_launch')
      localized.action_label = t('app.search_pulse.action.launch')
      return localized
    }
    case 'acquisition_expand': {
      localized.headline = t('app.search_pulse.acquisition_expand.headline')
      localized.message = t('app.search_pulse.acquisition_expand.message')
      localized.action_label = t('app.search_pulse.action.marketing')
      return localized
    }
    case 'search_filled': {
      localized.headline = t('app.search_pulse.search_filled.headline')
      localized.message = t('app.search_pulse.search_filled.message')
      localized.reason = t('app.search_pulse.reason.search_filled')
      localized.action_label = t('app.search_pulse.action.acquisition')
      return localized
    }
    case 'audience_setup': {
      localized.headline = t('app.search_pulse.audience_setup.headline')
      localized.message = t('app.search_pulse.audience_setup.message')
      localized.action_label = t('app.search_pulse.action.audience')
      return localized
    }
    case 'wait_leads': {
      localized.headline = t('app.search_pulse.wait_leads.headline')
      localized.message = t('app.search_pulse.wait_leads.message')
      localized.reason = t('app.search_pulse.reason.wait_leads')
      localized.action_label = t('app.search_pulse.action.open_inbox')
      return localized
    }
    case 'search_near_goal': {
      localized.headline = t('app.search_pulse.search_near_goal.headline')
      localized.message = t('app.search_pulse.search_near_goal.message', { values: { count } })
      localized.reason = t('app.search_pulse.reason.search_near_goal')
      localized.action_label = t('app.search_pulse.action.candidates')
      return localized
    }
    case 'later_setup': {
      localized.headline = t('app.search_pulse.later_setup.headline', { values: { name } })
      localized.message = t('app.search_pulse.later_setup.message')
      localized.action_label = t('app.search_pulse.action.setup')
      return localized
    }
    case 'later_channel': {
      localized.headline = t('app.search_pulse.later_channel.headline', { values: { channel } })
      localized.message = t('app.search_pulse.later_channel.message', { values: { name } })
      localized.action_label = t('app.search_pulse.action.open')
      return localized
    }
    case 'cpl_up': {
      localized.headline = t('app.search_pulse.cpl_up.headline', { values: { name } })
      localized.message = t('app.search_pulse.cpl_up.message', { values: { count } })
      localized.action_label = t('app.search_pulse.action.view')
      return localized
    }
    case 'no_recent_leads': {
      localized.headline = t('app.search_pulse.no_recent_leads.headline', { values: { name } })
      localized.message = t('app.search_pulse.no_recent_leads.message', { values: { count } })
      localized.action_label = t('app.search_pulse.action.view')
      return localized
    }
    case 'spend_no_leads': {
      localized.headline = t('app.search_pulse.spend_no_leads.headline', { values: { name } })
      localized.message = t('app.search_pulse.spend_no_leads.message')
      localized.action_label = t('app.search_pulse.action.view')
      return localized
    }
    default:
      return item
  }
}

export function acquisitionActivityStatusLabel(
  activity: { status?: string | null; lifecycle?: string | null },
  t: TranslateFn,
): string {
  const lifecycle = String(activity.lifecycle || 'active')
  const status = String(activity.status || '').trim()
  if (lifecycle === 'paused') return t('app.acquisition.status.paused')
  if (lifecycle === 'archived') return t('app.acquisition.status.archived')
  if (status === 'needs_attention') return t('app.acquisition.status.needs_attention')
  if (status === 'draft') return t('app.acquisition.status.draft')
  if (status === 'paused') return t('app.acquisition.status.no_responses')
  if (lifecycle === 'active' && status === 'active') return t('app.acquisition.status.running')
  if (status === 'active') return t('app.acquisition.status.active')
  if (!status) return t('app.acquisition.status.draft')
  return t(`app.acquisition.status.${status}`, { defaultValue: status })
}

export function acquisitionNextActionTitle(
  next: { kind?: string | null; title?: string | null } | null | undefined,
  t: TranslateFn,
): string {
  const kind = String(next?.kind || '').trim()
  if (kind === 'setup') return t('app.acquisition.next_kind.setup')
  if (kind === 'no_leads') return t('app.acquisition.next_kind.no_leads')
  if (kind === 'cost_increase') return t('app.acquisition.next_kind.cost_increase')
  return String(next?.title || '').trim()
}
