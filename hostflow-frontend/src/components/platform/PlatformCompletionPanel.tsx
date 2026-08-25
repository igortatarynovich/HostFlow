import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { IconCircleCheck } from '@tabler/icons-react'
import { resolvePlatformCompletion, type PlatformCompletionResolution } from '../../api/platformCompletion'
import { clientAcquisitionChannelPath } from '../../app/clientAcquisitionPaths'
import { SALES_CLIENT_ACTIVE_EVENT, clientDetailPath, executePlatformHandoff } from '../../services/platformHandoff'
import type { SearchRole } from '../../utils/launchSearchRoleDefaults'
import { useToast } from '../Toast'

type PlatformCompletionPanelProps = {
  event: string
  context: Record<string, unknown>
  onHandoffComplete?: () => void
}

export function PlatformCompletionPanel({ event, context, onHandoffComplete }: PlatformCompletionPanelProps) {
  const navigate = useNavigate()
  const { notify } = useToast()
  const [resolution, setResolution] = useState<PlatformCompletionResolution | null>(null)
  const [loading, setLoading] = useState(true)
  const [handoffRunning, setHandoffRunning] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    void resolvePlatformCompletion({ event, context })
      .then((data) => {
        if (!cancelled) setResolution(data)
      })
      .catch(() => {
        if (!cancelled) setResolution(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [event, context])

  async function handleHandoff() {
    if (!resolution?.handoff) return
    setHandoffRunning(true)
    try {
      const result = await executePlatformHandoff(resolution.handoff)
      onHandoffComplete?.()
      notify({ title: resolution.handoff.label, variant: 'success' })
      if (result?.navigateTo) navigate(result.navigateTo)
    } finally {
      setHandoffRunning(false)
    }
  }

  if (loading) {
    return (
      <section className="rounded-xl border border-emerald-200 bg-emerald-50/80 p-6 shadow-sm">
        <p className="text-sm text-emerald-900">Загрузка…</p>
      </section>
    )
  }

  if (!resolution) {
    return (
      <section className="rounded-xl border border-emerald-200 bg-emerald-50/80 p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <IconCircleCheck size={24} className="shrink-0 text-emerald-600" aria-hidden />
          <div>
            <p className="text-sm font-semibold text-emerald-900">Готово</p>
            <p className="mt-1 text-sm text-emerald-800">Работа завершена.</p>
          </div>
        </div>
      </section>
    )
  }

  const clientId = String(context.client_id || resolution.done?.client_id || '').trim()
  const channelId = String(context.channel_id || '').trim()

  return (
    <section className="rounded-xl border border-emerald-200 bg-emerald-50/80 p-6 shadow-sm" data-testid="platform-completion">
      <div className="flex items-start gap-3">
        <IconCircleCheck size={24} className="shrink-0 text-emerald-600" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-emerald-900">{resolution.completion.title}</p>
          <p className="mt-1 text-sm text-emerald-800">{resolution.completion.message}</p>

          {resolution.handoffs && resolution.handoffs.length > 1 ? (
            <div className="mt-4 space-y-3">
              <p className="text-sm font-medium text-slate-800">Следующие действия по договору</p>
              {resolution.handoffs.map((ho) => (
                <button
                  key={ho.action}
                  type="button"
                  className="flex w-full items-center justify-center rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm font-semibold text-brand-800 hover:bg-brand-50 disabled:opacity-60"
                  disabled={handoffRunning}
                  onClick={async () => {
                    setHandoffRunning(true)
                    try {
                      const result = await executePlatformHandoff(ho)
                      onHandoffComplete?.()
                      notify({ title: ho.label, variant: 'success' })
                      if (result?.navigateTo) navigate(result.navigateTo)
                    } finally {
                      setHandoffRunning(false)
                    }
                  }}
                >
                  {ho.label}
                </button>
              ))}
            </div>
          ) : null}

          {resolution.handoff && (!resolution.handoffs || resolution.handoffs.length <= 1) ? (
            <div className="mt-4 space-y-3">
              {resolution.handoff.hint ? (
                <p className="text-sm text-slate-700">{resolution.handoff.hint}</p>
              ) : null}
              <div className="flex flex-col gap-3 sm:flex-row">
                <button
                  type="button"
                  className="inline-flex flex-1 items-center justify-center rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
                  disabled={handoffRunning}
                  onClick={() => void handleHandoff()}
                >
                  {handoffRunning ? 'Создаём…' : resolution.handoff.label}
                </button>
                {clientId ? (
                  <Link
                    to={clientDetailPath(clientId)}
                    className="inline-flex flex-1 items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-800 hover:bg-slate-50"
                  >
                    Открыть клиента
                  </Link>
                ) : null}
              </div>
            </div>
          ) : null}

          {!resolution.handoff && resolution.done ? (
            <div className="mt-4 space-y-3">
              <p className="text-sm text-slate-700">{resolution.done.message}</p>
              <div className="flex flex-col gap-2 sm:flex-row">
                {clientId ? (
                  <Link
                    to={clientDetailPath(clientId)}
                    className="inline-flex flex-1 items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-800 hover:bg-slate-50"
                  >
                    {resolution.done.action_label || 'Открыть клиента'}
                  </Link>
                ) : null}
                {channelId ? (
                  <Link
                    to={clientAcquisitionChannelPath(channelId)}
                    className="inline-flex flex-1 items-center justify-center rounded-xl border border-emerald-300 bg-white px-4 py-3 text-sm font-semibold text-emerald-900 hover:bg-emerald-50/80"
                  >
                    К привлечению клиентов
                  </Link>
                ) : null}
              </div>
            </div>
          ) : null}

          {resolution.handoff && channelId ? (
            <Link
              to={clientAcquisitionChannelPath(channelId)}
              className="mt-4 inline-flex text-sm font-medium text-emerald-800 hover:underline"
            >
              Вернуться к привлечению клиентов
            </Link>
          ) : null}
        </div>
      </div>
    </section>
  )
}

export function buildSalesClientActiveContext(input: {
  clientId: string
  clientName: string
  leadId?: string
  channelId?: string | null
  searchRole?: SearchRole
}): Record<string, unknown> {
  return {
    client_id: input.clientId,
    client_name: input.clientName,
    lead_id: input.leadId,
    channel_id: input.channelId,
    search_role: input.searchRole,
  }
}

export { SALES_CLIENT_ACTIVE_EVENT }
