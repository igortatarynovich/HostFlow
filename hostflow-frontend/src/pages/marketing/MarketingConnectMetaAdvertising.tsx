/**
 * Connect Meta Advertising wizard — pick Meta Campaign (+ optional Ad Set),
 * preview Lead Forms + Ads, connect-all to current Flight.
 */
import { useEffect, useMemo, useState } from 'react'
import {
  connectMetaAdvertising,
  parseMetaAdvertisingIds,
  previewMetaAdvertising,
  type MetaAdvertisingPreview,
} from '../../api/platformCampaigns'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

type Props = {
  campaignId: string
  open: boolean
  onClose: () => void
  onConnected: () => Promise<void> | void
  t: (key: string, opts?: Record<string, unknown>) => string
}

type Step = 'ids' | 'preview'

function toggleId(list: string[], id: string): string[] {
  return list.includes(id) ? list.filter((x) => x !== id) : [...list, id]
}

export function MarketingConnectMetaAdvertising({
  campaignId,
  open,
  onClose,
  onConnected,
  t,
}: Props) {
  const [step, setStep] = useState<Step>('ids')
  const [campaignInput, setCampaignInput] = useState('')
  const [adsetInput, setAdsetInput] = useState('')
  const [preview, setPreview] = useState<MetaAdvertisingPreview | null>(null)
  const [selectedForms, setSelectedForms] = useState<string[]>([])
  const [selectedAds, setSelectedAds] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [summary, setSummary] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setStep('ids')
    setPreview(null)
    setSelectedForms([])
    setSelectedAds([])
    setError(null)
    setSummary(null)
    setBusy(false)
  }, [open])

  const resolvedIds = useMemo(() => {
    const fromCampaign = parseMetaAdvertisingIds(campaignInput)
    const fromAdset = parseMetaAdvertisingIds(adsetInput)
    const meta_campaign_id =
      fromCampaign.meta_campaign_id ||
      (campaignInput.trim().match(/^\d{5,}$/) ? campaignInput.trim() : undefined)
    const meta_adset_id =
      fromAdset.meta_adset_id ||
      fromCampaign.meta_adset_id ||
      (adsetInput.trim().match(/^\d{5,}$/) ? adsetInput.trim() : undefined)
    return { meta_campaign_id, meta_adset_id }
  }, [campaignInput, adsetInput])

  if (!open) return null

  async function loadPreview() {
    const cid = resolvedIds.meta_campaign_id
    if (!cid || busy) return
    setBusy(true)
    setError(null)
    setSummary(null)
    try {
      const data = await previewMetaAdvertising(campaignId, {
        meta_campaign_id: cid,
        meta_adset_id: resolvedIds.meta_adset_id,
      })
      setPreview(data)
      setSelectedForms(data.forms.map((f) => f.form_id))
      setSelectedAds(data.ads.map((a) => a.ad_id))
      setStep('preview')
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.detail.errors.meta_preview', {
            defaultValue: 'Не удалось загрузить формы и объявления Meta',
          }),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  async function submitConnect() {
    const cid = resolvedIds.meta_campaign_id || preview?.meta_campaign_id
    if (!cid || busy) return
    if (!selectedForms.length && !selectedAds.length) {
      setError(
        getFriendlyErrorInfo(
          new Error('empty'),
          t('app.marketing.detail.errors.meta_connect_empty', {
            defaultValue: 'Выберите хотя бы одну форму или объявление',
          }),
          t,
        ),
      )
      return
    }
    setBusy(true)
    setError(null)
    setSummary(null)
    try {
      const result = await connectMetaAdvertising(campaignId, {
        meta_campaign_id: cid,
        meta_adset_id: resolvedIds.meta_adset_id || preview?.meta_adset_id || undefined,
        form_ids: selectedForms,
        ad_ids: selectedAds,
      })
      const parts = [
        `форм: +${result.forms_attached.length}`,
        result.forms_skipped.length ? `пропущено ${result.forms_skipped.length}` : null,
        `объявлений: +${result.ads_attached.length}`,
        result.ads_skipped.length ? `пропущено ${result.ads_skipped.length}` : null,
      ].filter(Boolean)
      setSummary(parts.join(' · '))
      await onConnected()
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.detail.errors.meta_connect', {
            defaultValue: 'Не удалось подключить Meta-рекламу',
          }),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-40 flex items-end justify-center bg-slate-900/40 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="meta-adv-wizard-title"
      data-testid="marketing-meta-advertising-wizard"
    >
      <div className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-xl">
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-4 py-3">
          <div>
            <h2 id="meta-adv-wizard-title" className="text-sm font-semibold text-slate-900">
              Подключить Meta-рекламу
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Выберите рекламную кампанию Meta под эту вакансию. Мы подключим её формы и объявления к
              Flight.
            </p>
          </div>
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={onClose}
            disabled={busy}
            data-testid="marketing-meta-advertising-close"
          >
            Закрыть
          </button>
        </div>

        <div className="space-y-4 px-4 py-4">
          {error ? (
            <div
              className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-900"
              role="alert"
              data-testid="marketing-meta-advertising-error"
            >
              {error.title}
              {error.detail ? <div className="mt-0.5 opacity-90">{error.detail}</div> : null}
            </div>
          ) : null}

          {summary ? (
            <div
              className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900"
              role="status"
              data-testid="marketing-meta-advertising-summary"
            >
              Подключено: {summary}
            </div>
          ) : null}

          {step === 'ids' ? (
            <div className="space-y-3" data-testid="marketing-meta-advertising-step-ids">
              <label className="block text-xs text-slate-600">
                Meta Campaign ID или ссылка Ads Manager
                <input
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-900"
                  value={campaignInput}
                  onChange={(e) => setCampaignInput(e.target.value)}
                  placeholder="120253341522370547"
                  disabled={busy}
                  data-testid="marketing-meta-advertising-campaign-input"
                  autoComplete="off"
                />
              </label>
              <label className="block text-xs text-slate-600">
                Ad Set ID (необязательно)
                <input
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-900"
                  value={adsetInput}
                  onChange={(e) => setAdsetInput(e.target.value)}
                  placeholder="120253342594270547"
                  disabled={busy}
                  data-testid="marketing-meta-advertising-adset-input"
                  autoComplete="off"
                />
              </label>
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={busy || !resolvedIds.meta_campaign_id}
                onClick={() => void loadPreview()}
                data-testid="marketing-meta-advertising-preview"
              >
                {busy ? '…' : 'Показать формы и объявления'}
              </button>
            </div>
          ) : null}

          {step === 'preview' && preview ? (
            <div className="space-y-4" data-testid="marketing-meta-advertising-step-preview">
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
                <div className="font-medium text-slate-900">
                  {preview.meta_campaign_name || `Campaign ${preview.meta_campaign_id}`}
                </div>
                <div className="mt-0.5 font-mono text-slate-500">{preview.meta_campaign_id}</div>
                {preview.meta_adset_id ? (
                  <div className="mt-0.5 font-mono text-slate-500">
                    Ad Set {preview.meta_adset_id}
                  </div>
                ) : null}
                {preview.warning ? (
                  <p className="mt-2 text-amber-800" data-testid="marketing-meta-advertising-warning">
                    {preview.warning}
                  </p>
                ) : null}
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between gap-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Lead Forms ({preview.forms.length})
                  </h3>
                  <button
                    type="button"
                    className="text-xs font-medium text-brand-600"
                    onClick={() =>
                      setSelectedForms(
                        selectedForms.length === preview.forms.length
                          ? []
                          : preview.forms.map((f) => f.form_id),
                      )
                    }
                  >
                    {selectedForms.length === preview.forms.length ? 'Снять все' : 'Выбрать все'}
                  </button>
                </div>
                {preview.forms.length === 0 ? (
                  <p className="text-xs text-slate-500">Формы не найдены для этой кампании.</p>
                ) : (
                  <ul className="space-y-2">
                    {preview.forms.map((form) => (
                      <li key={form.form_id}>
                        <label className="flex cursor-pointer items-start gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm">
                          <input
                            type="checkbox"
                            className="mt-1"
                            checked={selectedForms.includes(form.form_id)}
                            onChange={() => setSelectedForms((prev) => toggleId(prev, form.form_id))}
                            data-testid={`marketing-meta-form-${form.form_id}`}
                          />
                          <span className="min-w-0">
                            <span className="block font-medium text-slate-900">
                              {form.form_name || `Form ${form.form_id}`}
                            </span>
                            <span className="block font-mono text-xs text-slate-500">
                              {form.form_id}
                            </span>
                          </span>
                        </label>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between gap-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Ads ({preview.ads.length})
                  </h3>
                  <button
                    type="button"
                    className="text-xs font-medium text-brand-600"
                    onClick={() =>
                      setSelectedAds(
                        selectedAds.length === preview.ads.length
                          ? []
                          : preview.ads.map((a) => a.ad_id),
                      )
                    }
                  >
                    {selectedAds.length === preview.ads.length ? 'Снять все' : 'Выбрать все'}
                  </button>
                </div>
                {preview.ads.length === 0 ? (
                  <p className="text-xs text-slate-500">Объявления не найдены.</p>
                ) : (
                  <ul className="space-y-2">
                    {preview.ads.map((ad) => (
                      <li key={ad.ad_id}>
                        <label className="flex cursor-pointer items-start gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm">
                          <input
                            type="checkbox"
                            className="mt-1"
                            checked={selectedAds.includes(ad.ad_id)}
                            onChange={() => setSelectedAds((prev) => toggleId(prev, ad.ad_id))}
                            data-testid={`marketing-meta-ad-${ad.ad_id}`}
                          />
                          <span className="min-w-0">
                            <span className="block font-medium text-slate-900">
                              {ad.ad_name || `Ad ${ad.ad_id}`}
                            </span>
                            <span className="block font-mono text-xs text-slate-500">{ad.ad_id}</span>
                          </span>
                        </label>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  disabled={busy}
                  onClick={() => setStep('ids')}
                  data-testid="marketing-meta-advertising-back"
                >
                  Назад
                </button>
                <button
                  type="button"
                  className="btn-primary btn-sm"
                  disabled={busy || (!selectedForms.length && !selectedAds.length)}
                  onClick={() => void submitConnect()}
                  data-testid="marketing-meta-advertising-connect"
                >
                  {busy ? '…' : 'Подключить к Flight'}
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
