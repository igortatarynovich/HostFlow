import { useCallback, useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import {
  listLegalDocuments,
  createLegalDocument,
  updateLegalDocument,
  fetchBillingLegalDrafts,
  type LegalDocumentOut,
  type LegalDocumentCreate,
  type LegalDocumentKind,
} from '../../api/legalDocuments'
import { useToast } from '../../components/Toast'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'

type DocTypeRow = {
  value: LegalDocumentKind
  labelKey: string
  emptyHintKey: string
}

const CANDIDATE_DOC_TYPES: DocTypeRow[] = [
  { value: 'rodo_clause', labelKey: 'admin.legal.rodo', emptyHintKey: 'admin.legal.no_rodo' },
  { value: 'privacy_policy', labelKey: 'admin.legal.privacy', emptyHintKey: 'admin.legal.no_privacy' },
  { value: 'terms_of_service', labelKey: 'admin.legal.terms', emptyHintKey: 'admin.legal.no_terms' },
  { value: 'cookie_policy', labelKey: 'admin.legal.cookies', emptyHintKey: 'admin.legal.no_cookies' },
]

const BILLING_DOC_TYPES: DocTypeRow[] = [
  { value: 'trial_terms', labelKey: 'admin.legal.billing.trial_terms', emptyHintKey: 'admin.legal.billing.missing' },
  {
    value: 'downgrade_cancellation',
    labelKey: 'admin.legal.billing.downgrade_cancellation',
    emptyHintKey: 'admin.legal.billing.missing',
  },
  { value: 'overage_autodebit', labelKey: 'admin.legal.billing.overage_autodebit', emptyHintKey: 'admin.legal.billing.missing' },
  { value: 'data_retention', labelKey: 'admin.legal.billing.data_retention', emptyHintKey: 'admin.legal.billing.missing' },
  {
    value: 'automation_disclaimer',
    labelKey: 'admin.legal.billing.automation_disclaimer',
    emptyHintKey: 'admin.legal.billing.missing',
  },
  { value: 'mapping_disclaimer', labelKey: 'admin.legal.billing.mapping_disclaimer', emptyHintKey: 'admin.legal.billing.missing' },
]

const BILLING_KINDS = new Set<string>(BILLING_DOC_TYPES.map((r) => r.value))

export default function LegalDocumentsPage() {
  const { t } = useI18n()
  const { notify } = useToast()
  const [docs, setDocs] = useState<LegalDocumentOut[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState<LegalDocumentKind | null>(null)
  const [formVersionId, setFormVersionId] = useState('')
  const [formContentUrl, setFormContentUrl] = useState('')
  const [formContentHtml, setFormContentHtml] = useState('')

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const data = await listLegalDocuments()
      setDocs(data)
    } catch (e: unknown) {
      notify({
        title: (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error',
        variant: 'error',
      })
      setDocs([])
    } finally {
      setLoading(false)
    }
  }, [notify])

  useEffect(() => {
    void load()
  }, [load])

  const handleCreate = async () => {
    if (!showForm || !formVersionId.trim()) return
    setSaving(true)
    try {
      const payload: LegalDocumentCreate = {
        type: showForm,
        version_id: formVersionId.trim(),
        content_url: formContentUrl.trim() || undefined,
        content_html: formContentHtml.trim() || undefined,
        is_active: true,
      }
      await createLegalDocument(payload)
      notify({ title: t('admin.legal.created'), variant: 'success' })
      setShowForm(null)
      setFormVersionId('')
      setFormContentUrl('')
      setFormContentHtml('')
      await load()
    } catch (e: unknown) {
      notify({
        title: (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error',
        variant: 'error',
      })
    } finally {
      setSaving(false)
    }
  }

  const handleSetActive = async (doc: LegalDocumentOut) => {
    setSaving(true)
    try {
      await updateLegalDocument(doc.id, { is_active: true })
      notify({ title: t('admin.legal.activated'), variant: 'success' })
      await load()
    } catch (e: unknown) {
      notify({
        title: (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error',
        variant: 'error',
      })
    } finally {
      setSaving(false)
    }
  }

  const loadBillingDraft = async () => {
    if (!showForm || !BILLING_KINDS.has(showForm)) return
    setSaving(true)
    try {
      const items = await fetchBillingLegalDrafts()
      const hit = items.find((i) => i.type === showForm)
      if (!hit) {
        notify({ title: t('admin.legal.billing.draft_not_found'), variant: 'error' })
        return
      }
      setFormVersionId(hit.version_id)
      setFormContentHtml(hit.content_html)
      notify({ title: t('admin.legal.billing.draft_loaded'), variant: 'success' })
    } catch (e: unknown) {
      notify({
        title: (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error',
        variant: 'error',
      })
    } finally {
      setSaving(false)
    }
  }

  const renderTypeBlock = (row: DocTypeRow) => {
    const { value, labelKey, emptyHintKey } = row
    const typeDocs = docs.filter((d) => d.type === value)
    const activeDoc = typeDocs.find((d) => d.is_active)
    const typeLabel = t(labelKey)
    const isBilling = BILLING_KINDS.has(value)

    return (
      <div key={value} className="mb-4 last:mb-0">
        <h3 className="text-sm font-semibold text-slate-800">{typeLabel}</h3>
        {activeDoc ? (
          <div className="alert-success mt-2">
            <span className="font-medium">
              {t('admin.legal.active')}: {activeDoc.version_id}
              {activeDoc.content_url && (
                <a
                  href={activeDoc.content_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-2 text-brand-600 hover:underline"
                >
                  {t('admin.legal.link')}
                </a>
              )}
            </span>
          </div>
        ) : (
          <p className="mt-1 text-sm text-amber-600">{t(emptyHintKey)}</p>
        )}

        {typeDocs.length > 0 && (
          <ul className="mt-2 space-y-1">
            {typeDocs.map((d) => (
              <li
                key={d.id}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50/90 px-3 py-2 text-sm"
              >
                <span>
                  {d.version_id}
                  {d.is_active && (
                    <span className="badge ml-2 bg-emerald-100 text-emerald-800">
                      {t('admin.legal.active')}
                    </span>
                  )}
                  {d.content_url && (
                    <a
                      href={d.content_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-2 text-brand-600 hover:underline"
                    >
                      {d.content_url}
                    </a>
                  )}
                </span>
                {!d.is_active && (
                  <button
                    type="button"
                    onClick={() => handleSetActive(d)}
                    disabled={saving}
                    className="btn-secondary btn-sm"
                  >
                    {t('admin.legal.set_active')}
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}

        {showForm === value ? (
          <div className="mt-3 rounded-lg border border-slate-200 bg-white p-3">
            <label className="label">{t('admin.legal.version_id')}</label>
            <input
              type="text"
              value={formVersionId}
              onChange={(e) => setFormVersionId(e.target.value)}
              placeholder="2025-01-01"
              className="input mt-1"
            />
            <label className="label mt-3">{t('admin.legal.content_url')}</label>
            <input
              type="url"
              value={formContentUrl}
              onChange={(e) => setFormContentUrl(e.target.value)}
              placeholder="https://..."
              className="input mt-1"
            />
            <label className="label mt-3">{t('admin.legal.content_html')}</label>
            <textarea
              value={formContentHtml}
              onChange={(e) => setFormContentHtml(e.target.value)}
              rows={6}
              className="input mt-1 font-mono text-xs"
            />
            {isBilling && (
              <button type="button" onClick={() => void loadBillingDraft()} disabled={saving} className="btn-secondary btn-sm mt-2">
                {t('admin.legal.billing.load_draft')}
              </button>
            )}
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => void handleCreate()}
                disabled={saving || !formVersionId.trim()}
                className="btn-primary btn-sm"
              >
                {saving ? t('common.saving') : t('common.actions.save')}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowForm(null)
                  setFormVersionId('')
                  setFormContentUrl('')
                  setFormContentHtml('')
                }}
                disabled={saving}
                className="btn-secondary btn-sm"
              >
                {t('common.actions.cancel')}
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => {
              setShowForm(value)
              setFormVersionId('')
              setFormContentUrl('')
              setFormContentHtml('')
            }}
            className="btn-secondary btn-sm mt-2"
          >
            + {t('admin.legal.add_version')}
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="mb-1">
        <SettingsSubpageHeader
          backLabel={t('admin.settings.subpage.back_all')}
          kicker={t('admin.legal.header_kicker')}
          title={t('admin.legal.title')}
          subtitle={t('admin.legal.subtitle')}
        />
      </div>
      {loading ? (
        <section className="settings-panel">
          <p className="text-sm text-slate-500">{t('common.loading')}</p>
        </section>
      ) : (
        <>
          <section className="settings-panel">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('admin.legal.section_candidates')}
            </h3>
            {CANDIDATE_DOC_TYPES.map(renderTypeBlock)}
          </section>

          <section className="settings-panel">
            <header className="mb-3">
              <h2 className="text-lg font-semibold text-slate-900">{t('admin.legal.billing.section_title')}</h2>
              <p className="mt-1 text-xs text-slate-600">{t('admin.legal.billing.section_subtitle')}</p>
            </header>
            {BILLING_DOC_TYPES.map(renderTypeBlock)}
          </section>
        </>
      )}
    </div>
  )
}
