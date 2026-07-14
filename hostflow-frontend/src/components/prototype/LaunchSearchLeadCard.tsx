import { IconPhone } from '@tabler/icons-react'

type LaunchSearchLeadCardProps = {
  searchName: string
  clientName: string
}

export function LaunchSearchLeadCard({ searchName, clientName }: LaunchSearchLeadCardProps) {
  return (
    <div className="space-y-6" data-testid="launch-search-lead-preview">
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        <span className="font-medium">Первая заявка</span> · {searchName}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">Jan Kowalski</h2>
            <p className="mt-1 text-sm text-slate-600">
              Водитель C+E · {clientName}
            </p>
          </div>
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
            Новая заявка
          </span>
        </div>

        <dl className="mt-6 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Телефон</dt>
            <dd className="mt-0.5 font-medium text-slate-900">+48 512 345 678</dd>
          </div>
          <div>
            <dt className="text-slate-500">Email</dt>
            <dd className="mt-0.5 font-medium text-slate-900">jan.kowalski@example.com</dd>
          </div>
          <div>
            <dt className="text-slate-500">Права</dt>
            <dd className="mt-0.5 font-medium text-slate-900">C+E</dd>
          </div>
          <div>
            <dt className="text-slate-500">Гражданство</dt>
            <dd className="mt-0.5 font-medium text-slate-900">Польша</dd>
          </div>
          <div>
            <dt className="text-slate-500">Опыт</dt>
            <dd className="mt-0.5 font-medium text-slate-900">3 года</dd>
          </div>
          <div>
            <dt className="text-slate-500">Источник</dt>
            <dd className="mt-0.5 font-medium text-slate-900">Meta</dd>
          </div>
        </dl>

        <div className="mt-6 rounded-xl border border-brand-100 bg-brand-50/50 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-brand-700">Следующий шаг</p>
          <p className="mt-1 text-sm text-slate-800">Позвонить кандидату</p>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            <IconPhone size={16} />
            Позвонить
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Отклонить
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            В работу
          </button>
        </div>
      </div>

      <p className="text-xs text-slate-500">
        Так будет выглядеть заявка после заполнения анкеты. Без ручного маппинга и настроек.
      </p>
    </div>
  )
}

function QrPlaceholder() {
  const cells = [
    [1, 1, 1, 0, 1, 0, 1, 1, 1],
    [1, 0, 1, 0, 0, 1, 1, 0, 1],
    [1, 1, 1, 0, 1, 1, 0, 1, 1],
    [0, 0, 0, 1, 0, 1, 0, 0, 0],
    [1, 0, 1, 1, 0, 0, 1, 0, 1],
    [0, 1, 0, 0, 1, 1, 0, 1, 0],
    [1, 1, 1, 0, 1, 0, 1, 1, 1],
    [1, 0, 1, 1, 0, 1, 0, 1, 0],
    [1, 1, 1, 0, 1, 1, 1, 0, 1],
  ]

  return (
    <div className="inline-grid grid-cols-9 gap-0.5 rounded-lg border border-slate-200 bg-white p-2">
      {cells.flat().map((filled, i) => (
        <div key={i} className={`h-3 w-3 ${filled ? 'bg-slate-900' : 'bg-white'}`} />
      ))}
    </div>
  )
}

export function LaunchSearchReadyAssets({
  searchName,
  formUrl,
  channels,
  metaConnected,
}: {
  searchName: string
  formUrl: string
  channels: { meta: boolean; link: boolean; qr: boolean }
  metaConnected: boolean
}) {
  const showLink = channels.link || channels.qr
  const showMeta = channels.meta

  return (
    <div className="space-y-4" data-testid="launch-search-ready-assets">
      {showLink ? (
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Ссылка на анкету</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <code className="flex-1 break-all rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-800">
              {formUrl}
            </code>
            <button
              type="button"
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              onClick={() => void navigator.clipboard.writeText(formUrl)}
            >
              Копировать
            </button>
          </div>
        </div>
      ) : null}

      {channels.qr ? (
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">QR-код</p>
          <div className="mt-3 flex flex-wrap items-center gap-4">
            <QrPlaceholder />
            <button
              type="button"
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Скачать PNG
            </button>
          </div>
        </div>
      ) : null}

      {showMeta ? (
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Meta</p>
          {metaConnected ? (
            <div className="mt-2 space-y-2 text-sm text-slate-700">
              <p>
                Форма готова для рекламы. ID: <span className="font-mono">482910563017294</span>
              </p>
              <button
                type="button"
                className="text-sm font-medium text-brand-700 hover:underline"
              >
                Как привязать форму к рекламе в Meta →
              </button>
            </div>
          ) : (
            <p className="mt-2 text-sm text-slate-600">
              Подключите Meta, чтобы получать заявки из рекламы Facebook и Instagram.
            </p>
          )}
        </div>
      ) : null}

      <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4 text-sm text-emerald-900">
        <p className="font-medium">Поиск «{searchName}» готов</p>
        <p className="mt-1 text-emerald-800">
          Люди заполняют анкету — заявки появляются в HostFlow автоматически.
        </p>
      </div>
    </div>
  )
}
