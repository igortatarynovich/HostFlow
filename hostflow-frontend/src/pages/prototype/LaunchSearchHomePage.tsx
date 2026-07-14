import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconPlus, IconSearch } from '@tabler/icons-react'
import { loadPrototypeSearches, type PrototypeSearch } from './launchSearchPrototype'
import { LaunchSearchLeadCard } from '../../components/prototype/LaunchSearchLeadCard'

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat('ru-RU', {
      day: 'numeric',
      month: 'long',
    }).format(new Date(iso))
  } catch {
    return 'сегодня'
  }
}

export default function LaunchSearchHomePage() {
  const [searches, setSearches] = useState<PrototypeSearch[]>([])
  const [previewId, setPreviewId] = useState<string | null>(null)

  useEffect(() => {
    setSearches(loadPrototypeSearches())
  }, [])

  const previewSearch = searches.find((s) => s.id === previewId)

  return (
    <div className="mx-auto max-w-3xl space-y-6" data-testid="launch-search-home">
      <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1 rounded-md bg-brand-50 px-2 py-1 text-xs font-medium text-brand-700">
              <IconSearch size={14} stroke={1.9} />
              Recruitment
            </div>
            <h1 className="mt-3 text-2xl font-semibold text-slate-900">Активные поиски</h1>
            <p className="mt-2 text-sm text-slate-600">
              Здесь видны все запущенные поиски сотрудников. Отсюда начинается работа с заявками.
            </p>
          </div>
          <Link
            to="/app/recruitment/searches/new"
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
            data-testid="launch-search-start"
          >
            <IconPlus size={16} />
            Запустить поиск
          </Link>
        </div>
      </section>

      {searches.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/50 p-10 text-center">
          <p className="text-sm text-slate-600">Пока нет активных поисков.</p>
          <p className="mt-1 text-sm text-slate-500">
            Запустите первый поиск водителей — это займёт около 10 минут.
          </p>
          <Link
            to="/app/recruitment/searches/new"
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            <IconPlus size={16} />
            Запустить поиск
          </Link>
        </section>
      ) : (
        <div className="space-y-3">
          {searches.map((search) => (
            <article
              key={search.id}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
              data-testid="launch-search-card"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-semibold text-slate-900">{search.name}</h2>
                    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
                      Активен
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-600">{search.channels.join(' · ')}</p>
                  <p className="mt-2 text-sm text-slate-500">
                    {search.stats.leads} заявок · {search.stats.candidates} кандидатов ·{' '}
                    {search.stats.interviews} интервью
                  </p>
                  <p className="mt-1 text-xs text-slate-400">Запущен {formatDate(search.createdAt)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setPreviewId(search.id)}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  data-testid="launch-search-demo-lead"
                >
                  Пример заявки
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {previewSearch ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-slate-900">Как выглядит заявка</h3>
            <button
              type="button"
              onClick={() => setPreviewId(null)}
              className="text-sm text-slate-500 hover:text-slate-700"
            >
              Закрыть
            </button>
          </div>
          <LaunchSearchLeadCard
            searchName={previewSearch.name}
            clientName={previewSearch.clientName}
          />
        </section>
      ) : null}

      <p className="text-center text-xs text-slate-400">Прототип · без подключения к серверу</p>
    </div>
  )
}
