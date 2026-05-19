import { useCallback, useEffect, useMemo, useState } from 'react'
import { listMergeDocumentTemplates, type MergeDocumentTemplate } from '../../api/documentMergeTemplates'
import {
  getTrustedIdentityPrepStatus,
  postContractDraftPreview,
  type ContractDraftPreviewOut,
  type TrustedIdentityPrepStatus,
} from '../../api/workforce'
import { useI18n } from '../../i18n'

const CONTRACT_CONSUMER = 'contract_generation'

type Props = {
  employeeId: string
  manage?: boolean
  ownCompanyId?: string | null
}

function formatApiError(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const d = detail as { code?: string; message?: string; placeholders?: string[] }
    if (d.code === 'CONTRACT_TEMPLATE_UNTRUSTED_PLACEHOLDERS' && d.placeholders?.length) {
      return `${d.code}: ${d.placeholders.join(', ')}`
    }
    if (d.code) return d.message ? `${d.code} — ${d.message}` : d.code
  }
  return (err as Error)?.message || 'Request failed'
}

export default function HrContractPreviewPanel({ employeeId, manage = false, ownCompanyId }: Props) {
  const { t } = useI18n()
  const [prep, setPrep] = useState<TrustedIdentityPrepStatus | null>(null)
  const [templates, setTemplates] = useState<MergeDocumentTemplate[]>([])
  const [templateCode, setTemplateCode] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<ContractDraftPreviewOut | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [prepStatus, tpls] = await Promise.all([
        getTrustedIdentityPrepStatus(employeeId),
        listMergeDocumentTemplates({ own_company_id: ownCompanyId ?? undefined }),
      ])
      setPrep(prepStatus)
      const active = tpls.filter((x) => x.is_active)
      setTemplates(active)
      setTemplateCode((prev) => prev || (active[0]?.code ?? ''))
    } catch (e) {
      setPrep(null)
      setError(formatApiError(e))
    } finally {
      setLoading(false)
    }
  }, [employeeId, ownCompanyId])

  useEffect(() => {
    void load()
  }, [load])

  const contractAllowed = useMemo(() => prep?.allowed_consumers.includes(CONTRACT_CONSUMER) ?? false, [prep])

  const contractBlock = useMemo(
    () => prep?.blocked_consumers.find((b) => b.consumer === CONTRACT_CONSUMER),
    [prep],
  )

  const contractConsumer = useMemo(
    () => prep?.consumers.find((c) => c.consumer === CONTRACT_CONSUMER),
    [prep],
  )

  const generate = async () => {
    if (!templateCode.trim()) return
    setBusy(true)
    setError(null)
    setPreview(null)
    try {
      const out = await postContractDraftPreview(employeeId, { template_code: templateCode.trim() })
      setPreview(out)
    } catch (e) {
      setError(formatApiError(e))
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return (
      <section id="hr-contract-preview" className="scroll-mt-24 rounded-xl border border-slate-200 bg-white p-4">
        <p className="text-sm text-slate-500">{t('common.loading')}</p>
      </section>
    )
  }

  return (
    <section id="hr-contract-preview" className="scroll-mt-24 space-y-3">
      <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            {t('app.hr.contract_preview.title', { defaultValue: 'Contract preview' })}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.hr.contract_preview.hint', {
              defaultValue:
                'Draft document from trusted identity only. No send, signature, or ePUAP — preview for HR review.',
            })}
          </p>
        </div>

        {prep ? (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-500">Identity:</span>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-800">
              {prep.projection_status}
            </span>
            {contractAllowed ? (
              <span className="text-emerald-700">contract_generation allowed</span>
            ) : (
              <span className="text-amber-800">
                contract_generation blocked
                {contractBlock?.block_code ? ` (${contractBlock.block_code})` : ''}
              </span>
            )}
          </div>
        ) : null}

        {!contractAllowed && prep ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            <p className="font-medium">
              {t('app.hr.contract_preview.blocked_title', { defaultValue: 'Cannot generate preview yet' })}
            </p>
            <ul className="mt-1 list-disc pl-5 text-xs space-y-0.5">
              {contractBlock?.block_code ? <li>{contractBlock.block_code}</li> : null}
              {prep.missing_fields.length > 0 ? (
                <li>
                  {t('app.hr.contract_preview.missing', { defaultValue: 'Missing' })}:{' '}
                  {prep.missing_fields.join(', ')}
                </li>
              ) : null}
              {prep.conflicted_fields.length > 0 ? (
                <li>
                  {t('app.hr.contract_preview.conflicts', { defaultValue: 'Conflicts' })}:{' '}
                  {prep.conflicted_fields.join(', ')}
                </li>
              ) : null}
              {prep.stale_fields.length > 0 ? (
                <li>
                  {t('app.hr.contract_preview.stale', { defaultValue: 'Stale' })}: {prep.stale_fields.join(', ')}
                </li>
              ) : null}
            </ul>
          </div>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
          <label className="block text-xs font-medium text-slate-600">
            {t('app.hr.contract_preview.template', { defaultValue: 'Template' })}
            <select
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={templateCode}
              onChange={(e) => setTemplateCode(e.target.value)}
              disabled={!manage || templates.length === 0}
            >
              {templates.length === 0 ? (
                <option value="">—</option>
              ) : (
                templates.map((tpl) => (
                  <option key={tpl.id} value={tpl.code}>
                    {tpl.name} ({tpl.code})
                  </option>
                ))
              )}
            </select>
          </label>
          <button
            type="button"
            disabled={!manage || !contractAllowed || !templateCode || busy}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            onClick={() => void generate()}
          >
            {busy
              ? t('common.loading')
              : t('app.hr.contract_preview.generate', { defaultValue: 'Generate preview' })}
          </button>
        </div>

        {templates.length === 0 ? (
          <p className="text-xs text-slate-500">
            {t('app.hr.contract_preview.no_templates', {
              defaultValue: 'No active merge templates. Add one in Settings → Document merge templates.',
            })}
          </p>
        ) : null}

        {error ? (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        ) : null}

        {preview ? (
          <div className="space-y-3 rounded-lg border border-emerald-200 bg-emerald-50/50 p-3">
            <p className="text-sm font-medium text-emerald-900">
              {t('app.hr.contract_preview.ready', { defaultValue: 'Draft preview ready' })} ({preview.status})
            </p>
            {preview.preview_url ? (
              <a
                href={preview.preview_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex text-sm font-medium text-brand-700 hover:underline"
              >
                {t('app.hr.contract_preview.open', { defaultValue: 'Open preview document' })}
              </a>
            ) : null}
            {Object.keys(preview.trusted_identity_bindings || {}).length > 0 ? (
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-600">
                  {t('app.hr.contract_preview.bindings', { defaultValue: 'Trusted fields used' })}
                </p>
                <dl className="mt-1 grid gap-1 sm:grid-cols-2">
                  {Object.entries(preview.trusted_identity_bindings).map(([k, v]) => (
                    <div key={k}>
                      <dt className="text-xs text-slate-500">{k}</dt>
                      <dd className="text-slate-900">{v || '—'}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            ) : null}
          </div>
        ) : null}

        {contractConsumer?.binding_keys?.length && !preview ? (
          <p className="text-xs text-slate-500">
            {t('app.hr.contract_preview.available_fields', { defaultValue: 'Available when ready' })}:{' '}
            {contractConsumer.binding_keys.join(', ')}
          </p>
        ) : null}

        <button type="button" className="text-xs text-slate-600 hover:text-slate-900 underline" onClick={() => void load()}>
          {t('app.hr.contract_preview.refresh', { defaultValue: 'Refresh readiness' })}
        </button>
      </div>
    </section>
  )
}
