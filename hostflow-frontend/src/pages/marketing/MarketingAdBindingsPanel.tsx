/**
 * Meta Ad ID → Flight bind panel for Campaign Detail.
 * Override for multi-Flight split of one form; Connect Source alone still routes when no bind.
 */
import { useState, type FormEvent } from 'react'
import {
  attachFlightAdBinding,
  detachCampaignAdBinding,
  patchCampaignAdBinding,
  type CampaignAdBinding,
  type CampaignFlight,
} from '../../api/platformCampaigns'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

type Props = {
  campaignId: string
  flight: CampaignFlight
  onChanged: () => Promise<void> | void
  t: (key: string, opts?: Record<string, unknown>) => string
}

function reprocessHint(
  binding: CampaignAdBinding,
  t: (key: string, opts?: Record<string, unknown>) => string,
): string | null {
  const r = binding.reprocess
  if (!r) return null
  const matched = Number(r.matched || 0)
  const processed = Number(r.processed || 0)
  const errors = Array.isArray(r.errors) ? r.errors.length : 0
  if (!matched && !processed && !errors) return null
  let msg = t('app.marketing.ad_bindings.reprocessed', { values: { matched, processed } })
  if (errors) msg += t('app.marketing.ad_bindings.reprocessed_errors', { values: { errors } })
  return msg
}

export function MarketingAdBindingsPanel({ campaignId, flight, onChanged, t }: Props) {
  const [adId, setAdId] = useState('')
  const [busy, setBusy] = useState(false)
  const [localError, setLocalError] = useState<FriendlyErrorInfo | null>(null)
  const [lastHint, setLastHint] = useState<string | null>(null)

  const bindings = [...(flight.ad_bindings || [])].sort((a, b) => {
    if (a.is_active !== b.is_active) return a.is_active ? -1 : 1
    return String(a.provider_ad_id).localeCompare(String(b.provider_ad_id))
  })

  async function onAttach(e: FormEvent) {
    e.preventDefault()
    const trimmed = adId.trim()
    if (!trimmed || busy) return
    setBusy(true)
    setLocalError(null)
    setLastHint(null)
    try {
      const created = await attachFlightAdBinding(campaignId, flight.id, trimmed, 'meta')
      setAdId('')
      setLastHint(reprocessHint(created, t))
      await onChanged()
    } catch (err: unknown) {
      setLocalError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.detail.errors.ad_bind'),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  async function onToggle(link: CampaignAdBinding) {
    if (busy) return
    setBusy(true)
    setLocalError(null)
    setLastHint(null)
    try {
      const next = await patchCampaignAdBinding(campaignId, link.id, !link.is_active)
      setLastHint(reprocessHint(next, t))
      await onChanged()
    } catch (err: unknown) {
      setLocalError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.detail.errors.ad_bind_patch'),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  async function onDetach(link: CampaignAdBinding) {
    if (busy) return
    if (!window.confirm(t('app.marketing.ad_bindings.confirm_unbind', { values: { id: link.provider_ad_id } }))) return
    setBusy(true)
    setLocalError(null)
    setLastHint(null)
    try {
      await detachCampaignAdBinding(campaignId, link.id)
      await onChanged()
    } catch (err: unknown) {
      setLocalError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.detail.errors.ad_unbind'),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <section
      className="mt-4 border-t border-slate-100 pt-4"
      data-testid="marketing-ad-bindings"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{t('app.marketing.ad_bindings.title')}</h3>
          <p className="mt-1 text-xs text-slate-500">
            {t('app.marketing.ad_bindings.help')}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {t('app.marketing.ad_bindings.flight')}: <span className="font-medium text-slate-700">{flight.name || flight.code}</span>
          </p>
        </div>
      </div>

      {localError ? (
        <div
          className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-900"
          data-testid="marketing-ad-bindings-error"
          role="alert"
        >
          {localError.title}
          {localError.detail ? <div className="mt-0.5 opacity-90">{localError.detail}</div> : null}
        </div>
      ) : null}

      {lastHint ? (
        <p
          className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900"
          data-testid="marketing-ad-bindings-reprocess"
          role="status"
        >
          {lastHint}
        </p>
      ) : null}

      {bindings.length === 0 ? (
        <p className="mt-3 text-xs text-slate-500" data-testid="marketing-ad-bindings-empty">
          {t('app.marketing.ad_bindings.empty')}
        </p>
      ) : (
        <ul className="mt-3 space-y-2" data-testid="marketing-ad-bindings-list">
          {bindings.map((link) => (
            <li
              key={link.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2"
              data-testid={`marketing-ad-binding-${link.id}`}
            >
              <div className="min-w-0">
                <div className="truncate font-mono text-sm text-slate-900">{link.provider_ad_id}</div>
                <div className="mt-0.5 text-xs text-slate-500">
                  {String(link.provider || 'meta').toUpperCase()} ·{' '}
                  {link.is_active ? t('app.marketing.ad_bindings.active') : t('app.marketing.ad_bindings.disabled')}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  disabled={busy}
                  onClick={() => void onToggle(link)}
                  data-testid={`marketing-ad-binding-toggle-${link.id}`}
                >
                  {link.is_active ? t('app.marketing.ad_bindings.disable') : t('app.marketing.ad_bindings.enable')}
                </button>
                <button
                  type="button"
                  className="btn-secondary btn-sm text-rose-700"
                  disabled={busy}
                  onClick={() => void onDetach(link)}
                  data-testid={`marketing-ad-binding-detach-${link.id}`}
                >
                  {t('app.marketing.ad_bindings.unbind')}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <form
        className="mt-3 flex flex-wrap items-end gap-2"
        onSubmit={(e) => void onAttach(e)}
        data-testid="marketing-ad-bindings-form"
      >
        <label className="min-w-[14rem] flex-1 text-xs text-slate-600">
          {t('app.marketing.ad_bindings.ad_id')}
          <input
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-900"
            value={adId}
            onChange={(e) => setAdId(e.target.value)}
            placeholder="120249011467340547"
            disabled={busy}
            data-testid="marketing-ad-bindings-input"
            autoComplete="off"
          />
        </label>
        <button
          type="submit"
          className="btn-primary btn-sm"
          disabled={busy || !adId.trim()}
          data-testid="marketing-ad-bindings-submit"
        >
          {busy ? '…' : t('app.marketing.ad_bindings.bind')}
        </button>
      </form>
    </section>
  )
}
