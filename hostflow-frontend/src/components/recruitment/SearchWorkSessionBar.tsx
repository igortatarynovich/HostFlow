import { useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import {
  advanceSearchWorkSession,
  cancelSearchWorkSession,
  getSearchWorkSession,
  isActiveWorkSessionForCandidate,
  candidateHref,
} from '../../services/searchWorkSession'

const KIND_LABEL: Record<string, string> = {
  call: 'Звонки',
  docs: 'Документы',
  interview: 'Интервью',
}

export function SearchWorkSessionBar() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const location = useLocation()
  const session = useMemo(() => getSearchWorkSession(), [location.pathname])

  const candidateId = useMemo(() => {
    const prefix = `${CRM_APP_PATHS.candidates}/`
    if (!location.pathname.startsWith(prefix)) return null
    const rest = location.pathname.slice(prefix.length)
    const id = rest.split('/')[0]
    return id || null
  }, [location.pathname])

  if (!session || !candidateId || !isActiveWorkSessionForCandidate(candidateId)) {
    return null
  }

  const total = session.queue.length
  const current = session.index + 1

  function handleNext() {
    const nextId = advanceSearchWorkSession()
    if (nextId) {
      navigate(candidateHref(nextId))
      return
    }
    navigate(session.returnPath)
  }

  function handleStop() {
    cancelSearchWorkSession()
    navigate(session.returnPath)
  }

  return (
    <div
      className="fixed inset-x-0 bottom-0 z-40 border-t border-brand-200 bg-brand-50/95 px-4 py-3 shadow-md backdrop-blur-sm"
      data-testid="m1-search-work-session-bar"
    >
      <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-3">
        <div className="text-sm text-slate-800">
          <span className="font-semibold">{KIND_LABEL[session.kind] || session.kind}</span>
          <span className="mx-2 text-slate-400">·</span>
          {t('app.search_next.session_progress', {
            defaultValue: 'Кандидат {current} из {total}',
            values: { current, total },
          })}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleStop}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {t('app.search_next.session_stop', { defaultValue: 'К подбору' })}
          </button>
          <button
            type="button"
            onClick={handleNext}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
          >
            {current < total
              ? t('app.search_next.session_next', { defaultValue: 'Готово — следующий' })
              : t('app.search_next.session_done', { defaultValue: 'Готово — вернуться' })}
          </button>
        </div>
      </div>
    </div>
  )
}
