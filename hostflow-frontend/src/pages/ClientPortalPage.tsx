import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  getClientPortalByToken,
  portalAcceptHandoff,
  portalRejectHandoff,
  portalRequestClarification,
  type ClientPortalData,
  type ClientPortalHandoff,
  type ClientPortalPresentedBy,
} from '../api/tenantLinks'
import { useI18n } from '../i18n'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { useRobotsMeta } from '../hooks/useRobotsMeta'

type ModalKind = 'reject' | 'clarify' | null

function presentedByLabel(pb: ClientPortalPresentedBy | undefined, t: ReturnType<typeof useI18n>['t']): string {
  if (!pb || pb.kind === 'generic') {
    return t('app.client_portal.handoff.from_agency', { defaultValue: 'Your agency contact' })
  }
  return t('app.client_portal.handoff.from_named', {
    defaultValue: 'From {{name}}',
    values: { name: pb.first_name },
  })
}

function waitingLabel(hours: number | null | undefined, t: ReturnType<typeof useI18n>['t']): string | null {
  if (hours == null) return null
  if (hours < 24) {
    return t('app.client_portal.handoff.waiting_hours', {
      defaultValue: 'Waiting ~{{hours}} h',
      values: { hours },
    })
  }
  const days = Math.floor(hours / 24)
  return t('app.client_portal.handoff.waiting_days', {
    defaultValue: 'Waiting ~{{days}} d',
    values: { days },
  })
}

export default function ClientPortalPage() {
  useRobotsMeta({ index: false, follow: false })
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const { t } = useI18n()
  const [data, setData] = useState<ClientPortalData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retryKey, setRetryKey] = useState(0)
  const [busyHandoffId, setBusyHandoffId] = useState<string | null>(null)
  const [modal, setModal] = useState<{ kind: ModalKind; handoffId: string } | null>(null)
  const [modalText, setModalText] = useState('')
  const [banner, setBanner] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  const reload = useCallback(async () => {
    if (!token.trim()) return
    const d = await getClientPortalByToken(token)
    setData(d)
  }, [token])

  useEffect(() => {
    if (!token.trim()) {
      setError(t('app.client_portal.errors.missing_token', { defaultValue: 'Отсутствует ссылка.' }))
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    getClientPortalByToken(token)
      .then((d) => {
        if (!cancelled) setData(d)
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          const msg =
            (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
            (e as Error)?.message ??
            'Error'
          setError(typeof msg === 'string' ? msg : 'Error')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [token, t, retryKey])

  const onAccept = async (handoffId: string) => {
    if (!token.trim()) return
    setBusyHandoffId(handoffId)
    setBanner(null)
    try {
      await portalAcceptHandoff(token, handoffId)
      setBanner({
        type: 'ok',
        text: t('app.client_portal.actions.accept_ok', { defaultValue: 'Candidate accepted.' }),
      })
      await reload()
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (e as Error)?.message ??
        'Error'
      setBanner({ type: 'err', text: typeof msg === 'string' ? msg : 'Error' })
    } finally {
      setBusyHandoffId(null)
    }
  }

  const submitModal = async () => {
    if (!modal || !token.trim()) return
    const text = modalText.trim()
    if (!text) return
    setBusyHandoffId(modal.handoffId)
    setBanner(null)
    try {
      if (modal.kind === 'reject') {
        await portalRejectHandoff(token, modal.handoffId, text)
        setBanner({
          type: 'ok',
          text: t('app.client_portal.actions.reject_ok', { defaultValue: 'Decision recorded.' }),
        })
      } else {
        await portalRequestClarification(token, modal.handoffId, text)
        setBanner({
          type: 'ok',
          text: t('app.client_portal.actions.clarify_ok', { defaultValue: 'Request sent to the agency.' }),
        })
      }
      setModal(null)
      setModalText('')
      await reload()
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (e as Error)?.message ??
        'Error'
      setBanner({ type: 'err', text: typeof msg === 'string' ? msg : 'Error' })
    } finally {
      setBusyHandoffId(null)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-slate-500">{t('common.loading', { defaultValue: 'Загрузка...' })}</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <ErrorRecoveryBanner
            info={{
              title: error,
              hint: t('app.client_portal.errors.bad_link', { defaultValue: 'Ссылка недействительна или истекла.' }),
            }}
            onRetry={() => setRetryKey((prev) => prev + 1)}
            retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
            compact
          />
        </div>
      </div>
    )
  }

  const name = data?.company_name ?? t('app.client_portal.title', { defaultValue: 'Client portal' })
  const candidates = data?.candidates ?? []
  const summary = data?.summary
  const activity = data?.activity ?? []

  const statusLabel = (s: string) =>
    t(`app.client_portal.activity.status.${s}`, { defaultValue: s.replace(/_/g, ' ') })

  const renderHandoffBlock = (h: ClientPortalHandoff | undefined) => {
    if (!h) return null
    const wait = waitingLabel(h.waiting_hours, t)
    return (
      <div className="mt-3 rounded-lg border border-slate-200 bg-white/80 p-3 text-sm">
        <div className="font-medium text-slate-800">
          {h.status === 'pending_review'
            ? t('app.client_portal.handoff.action_required', { defaultValue: 'Your decision is required' })
            : t('app.client_portal.handoff.in_progress', { defaultValue: 'In progress with your team' })}
        </div>
        <div className="mt-1 text-slate-600">{presentedByLabel(h.presented_by, t)}</div>
        {wait ? <div className="mt-1 text-slate-500">{wait}</div> : null}
        <div className="mt-3 flex flex-wrap gap-2">
          {h.status === 'pending_review' ? (
            <>
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={busyHandoffId === h.id}
                onClick={() => onAccept(h.id)}
              >
                {busyHandoffId === h.id
                  ? t('common.loading', { defaultValue: 'Loading…' })
                  : t('app.client_portal.actions.accept', { defaultValue: 'Accept' })}
              </button>
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={busyHandoffId === h.id}
                onClick={() => {
                  setModal({ kind: 'reject', handoffId: h.id })
                  setModalText('')
                }}
              >
                {t('app.client_portal.actions.reject', { defaultValue: 'Reject' })}
              </button>
            </>
          ) : null}
          {h.status === 'pending_review' || h.status === 'accepted' ? (
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={busyHandoffId === h.id}
              onClick={() => {
                setModal({ kind: 'clarify', handoffId: h.id })
                setModalText('')
              }}
            >
              {t('app.client_portal.actions.request_clarification', { defaultValue: 'Request clarification' })}
            </button>
          ) : null}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 py-8">
      <div className="mx-auto max-w-2xl px-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h1 className="text-xl font-semibold text-slate-900">{name}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {t('app.client_portal.subtitle', {
              defaultValue: 'Review candidates shared by your agency and record your decision.',
            })}
          </p>

          {summary ? (
            <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-amber-900/80">
                  {t('app.client_portal.home.pending', { defaultValue: 'Action required' })}
                </div>
                <div className="mt-1 text-2xl font-semibold text-amber-950">{summary.pending_decisions}</div>
                <div className="mt-1 text-sm text-amber-900/70">
                  {t('app.client_portal.home.pending_hint', { defaultValue: 'Pending decisions on shared candidates' })}
                </div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                  {t('app.client_portal.home.in_progress', { defaultValue: 'In progress' })}
                </div>
                <div className="mt-1 text-2xl font-semibold text-slate-900">{summary.candidates_in_progress}</div>
                <div className="mt-1 text-sm text-slate-600">
                  {t('app.client_portal.home.in_progress_hint', { defaultValue: 'Accepted candidates you are working with' })}
                </div>
              </div>
            </div>
          ) : null}

          {banner ? (
            <div
              className={`mt-4 rounded-lg px-3 py-2 text-sm ${
                banner.type === 'ok' ? 'bg-green-50 text-green-900' : 'bg-red-50 text-red-900'
              }`}
            >
              {banner.text}
            </div>
          ) : null}

          {activity.length > 0 ? (
            <div className="mt-6">
              <h2 className="text-sm font-semibold text-slate-800">
                {t('app.client_portal.home.recent_activity', { defaultValue: 'Recent activity' })}
              </h2>
              <ul className="mt-2 space-y-1 text-sm text-slate-600">
                {activity.slice(0, 6).map((row) => (
                  <li key={`${row.handoff_id}-${row.at}`} className="flex justify-between gap-2 border-b border-slate-100 py-1">
                    <span>{statusLabel(row.status)}</span>
                    <span className="shrink-0 text-slate-400">{row.at ? row.at.slice(0, 10) : '—'}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {candidates.length === 0 ? (
            <p className="mt-6 text-sm text-slate-500">
              {t('app.client_portal.empty', { defaultValue: 'No shared candidates right now.' })}
            </p>
          ) : (
            <ul className="mt-6 space-y-4">
              {candidates.map((c) => (
                <li key={c.id} className="rounded-xl border border-slate-100 bg-slate-50/50 p-4">
                  <div className="font-medium text-slate-900">
                    {[c.first_name, c.last_name].filter(Boolean).join(' ') || c.short_id || c.id}
                  </div>
                  {(c.stage || c.status) && (
                    <div className="mt-1 text-sm text-slate-500">{c.stage ?? c.status}</div>
                  )}
                  {(c.email || c.phone) && (
                    <div className="mt-1 text-sm text-slate-600">
                      {c.email}
                      {c.email && c.phone ? ' · ' : ''}
                      {c.phone}
                    </div>
                  )}
                  {renderHandoffBlock(c.handoff)}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {modal ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-5 shadow-lg">
            <h3 className="text-lg font-semibold text-slate-900">
              {modal.kind === 'reject'
                ? t('app.client_portal.modal.reject_title', { defaultValue: 'Reject candidate' })
                : t('app.client_portal.modal.clarify_title', { defaultValue: 'Request clarification' })}
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              {modal.kind === 'reject'
                ? t('app.client_portal.modal.reject_hint', {
                    defaultValue: 'Briefly explain why this candidate is not a fit. The agency will be notified.',
                  })
                : t('app.client_portal.modal.clarify_hint', {
                    defaultValue: 'Describe what you need from the agency. The handoff will return to them.',
                  })}
            </p>
            <textarea
              className="input mt-3 min-h-[100px] w-full"
              value={modalText}
              onChange={(e) => setModalText(e.target.value)}
              placeholder={
                modal.kind === 'reject'
                  ? t('app.client_portal.modal.reject_placeholder', { defaultValue: 'Reason…' })
                  : t('app.client_portal.modal.clarify_placeholder', { defaultValue: 'Your message…' })
              }
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => {
                  setModal(null)
                  setModalText('')
                }}
              >
                {t('common.actions.cancel', { defaultValue: 'Cancel' })}
              </button>
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={!modalText.trim() || busyHandoffId === modal.handoffId}
                onClick={() => submitModal()}
              >
                {busyHandoffId === modal.handoffId
                  ? t('common.loading', { defaultValue: 'Loading…' })
                  : t('app.client_portal.modal.send', { defaultValue: 'Send' })}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
