import { useNavigate } from 'react-router-dom'
import type { SearchDayItem, SearchWorkspacePulse } from '../../api/searchWorkspace'
import { recruitmentSearchPath } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import {
  candidateHref,
  startSearchWorkSession,
} from '../../services/searchWorkSession'
import { localizeSearchDayItem } from '../../utils/searchWorkspaceI18n'

function AfterThatList({ items }: { items: SearchDayItem[] }) {
  if (items.length === 0) return null
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item.id} className="flex items-center justify-between gap-3 text-sm text-slate-700">
          <span>
            {item.icon ? `${item.icon} ` : null}
            {item.headline}
            {item.count != null ? ` (${item.count})` : null}
          </span>
        </li>
      ))}
    </ul>
  )
}

type SearchNextActionPanelProps = {
  pulse: SearchWorkspacePulse | null
  searchId: string
  searchName?: string
  loading?: boolean
}

export function SearchNextActionPanel({
  pulse,
  searchId,
  searchName,
  loading,
}: SearchNextActionPanelProps) {
  const { t } = useI18n()
  const navigate = useNavigate()
  const next = pulse?.next_action ? localizeSearchDayItem(pulse.next_action, t, { searchTitle: searchName }) : null
  const afterThat = (pulse?.after_that ?? []).map((item) =>
    localizeSearchDayItem(item, t, { searchTitle: searchName }),
  )
  const later = (pulse?.later ?? []).map((item) => localizeSearchDayItem(item, t, { searchTitle: searchName }))

  if (loading) {
    return (
      <section className="rounded-lg border border-slate-200 bg-white p-2.5">
        <p className="text-sm text-slate-500">{t('common.loading')}</p>
      </section>
    )
  }

  function handleStart() {
    if (!next) return
    const queue = next.queue ?? []
    if (queue.length > 0 && next.work_kind) {
      startSearchWorkSession({
        searchId,
        kind: next.work_kind,
        queue,
        returnPath: recruitmentSearchPath(searchId),
      })
      navigate(candidateHref(queue[0]))
      return
    }
    navigate(next.href)
  }

  if (!next && later.length === 0) {
    return (
      <section className="rounded-lg border border-emerald-100 bg-emerald-50/40 p-2.5">
        <h2 className="text-sm font-semibold text-slate-900">
          {t('app.search_next.all_clear_title')}
        </h2>
        <p className="mt-2 text-sm text-slate-600">{t('app.search_next.all_clear_body')}</p>
      </section>
    )
  }

  return (
    <section className="space-y-2" data-testid="m1-search-next-action">
      {next ? (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-brand-200 bg-brand-50/60 px-2.5 py-1.5">
          <div className="min-w-0 flex-1">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-brand-800">
              {t('app.search_next.title')}
            </p>
            <h2 className="truncate text-sm font-semibold text-slate-900" title={next.reason || next.message}>
              {next.icon ? `${next.icon} ` : null}
              {next.headline}
            </h2>
          </div>
          <button
            type="button"
            onClick={handleStart}
            className="shrink-0 rounded-md bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700"
          >
            {next.action_label || t('app.search_next.start')}
          </button>
        </div>
      ) : null}

      {afterThat.length > 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white px-2.5 py-2">
          <h3 className="text-xs font-semibold text-slate-900">{t('app.search_next.after_that')}</h3>
          <div className="mt-1.5">
            <AfterThatList items={afterThat} />
          </div>
        </div>
      ) : null}

      {later.length > 0 ? (
        <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50/50 px-2.5 py-2">
          <h3 className="text-xs font-semibold text-slate-700">{t('app.search_day.later_title')}</h3>
          <p className="mt-0.5 text-[11px] text-slate-500">{t('app.search_day.later_hint')}</p>
          <div className="mt-1.5">
            <AfterThatList items={later} />
          </div>
        </div>
      ) : null}
    </section>
  )
}
