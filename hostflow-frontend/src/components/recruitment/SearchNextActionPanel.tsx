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
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
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
      <section className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">
          {t('app.search_next.all_clear_title')}
        </h2>
        <p className="mt-2 text-sm text-slate-600">{t('app.search_next.all_clear_body')}</p>
      </section>
    )
  }

  return (
    <section className="space-y-4" data-testid="m1-search-next-action">
      {next ? (
        <div className="rounded-xl border border-brand-200 bg-brand-50/60 p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-800">
            {t('app.search_next.title')}
          </p>
          <h2 className="mt-2 text-lg font-semibold text-slate-900">
            {next.icon ? `${next.icon} ` : null}
            {next.headline}
          </h2>
          <p className="mt-2 text-sm text-slate-700">{next.reason || next.message}</p>
          <button
            type="button"
            onClick={handleStart}
            className="mt-4 rounded-lg bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700"
          >
            {next.action_label || t('app.search_next.start')}
          </button>
        </div>
      ) : null}

      {afterThat.length > 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900">{t('app.search_next.after_that')}</h3>
          <div className="mt-3">
            <AfterThatList items={afterThat} />
          </div>
        </div>
      ) : null}

      {later.length > 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/50 p-4">
          <h3 className="text-sm font-semibold text-slate-700">{t('app.search_day.later_title')}</h3>
          <p className="mt-1 text-xs text-slate-500">{t('app.search_day.later_hint')}</p>
          <div className="mt-3">
            <AfterThatList items={later} />
          </div>
        </div>
      ) : null}
    </section>
  )
}
