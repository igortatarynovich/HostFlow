import { useCallback, useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import {
  listLegalDocuments,
  createLegalDocument,
  updateLegalDocument,
  type LegalDocumentOut,
  type LegalDocumentCreate,
} from '../../api/legalDocuments'
import { useToast } from '../../components/Toast'

const DOC_TYPES = [
  { value: 'rodo_clause' as const, labelKey: 'admin.legal.rodo' },
  { value: 'privacy_policy' as const, labelKey: 'admin.legal.privacy' },
]

export default function LegalDocumentsPage() {
  const { t } = useI18n()
  const { notify } = useToast()
  const [docs, setDocs] = useState<LegalDocumentOut[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState<'rodo_clause' | 'privacy_policy' | null>(null)
  const [formVersionId, setFormVersionId] = useState('')
  const [formContentUrl, setFormContentUrl] = useState('')

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
        is_active: true,
      }
      await createLegalDocument(payload)
      notify({ title: t('admin.legal.created', { defaultValue: 'Utworzono' }), variant: 'success' })
      setShowForm(null)
      setFormVersionId('')
      setFormContentUrl('')
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
      notify({ title: t('admin.legal.activated', { defaultValue: 'Ustawiono jako aktywny' }), variant: 'success' })
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

  return (
    <div className="space-y-4">
      <section className="card p-6">
        <header className="mb-4">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('admin.legal.title', { defaultValue: 'Dokumenty prawne (RODO, polityka prywatności)' })}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {t('admin.legal.subtitle', {
              defaultValue:
                'Skonfiguruj aktywną klauzulę RODO i politykę prywatności. Bez aktywnej klauzuli RODO nie można wysyłać informacji RODO do kandydatów.',
            })}
          </p>
        </header>

        {loading ? (
          <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Ładowanie...' })}</p>
        ) : (
          <>
            {DOC_TYPES.map(({ value, labelKey }) => {
              const typeDocs = docs.filter((d) => d.type === value)
              const activeDoc = typeDocs.find((d) => d.is_active)
              const typeLabel = t(labelKey)

              return (
                <div key={value} className="mb-6 last:mb-0">
                  <h3 className="text-sm font-semibold text-slate-700">{typeLabel}</h3>
                  {activeDoc ? (
                    <div className="alert-success mt-2">
                      <span className="font-medium">
                        {t('admin.legal.active', { defaultValue: 'Aktywny' })}: {activeDoc.version_id}
                        {activeDoc.content_url && (
                          <a
                            href={activeDoc.content_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="ml-2 text-brand-600 hover:underline"
                          >
                            {t('admin.legal.link', { defaultValue: 'Link' })}
                          </a>
                        )}
                      </span>
                    </div>
                  ) : (
                    <p className="mt-1 text-sm text-amber-600">
                      {value === 'rodo_clause'
                        ? t('admin.legal.no_rodo', {
                            defaultValue: 'Brak aktywnej klauzuli RODO — nie można wysyłać informacji do kandydatów.',
                          })
                        : t('admin.legal.no_privacy', { defaultValue: 'Brak aktywnej polityki prywatności.' })}
                    </p>
                  )}

                  {typeDocs.length > 0 && (
                    <ul className="mt-2 space-y-1">
                      {typeDocs.map((d) => (
                        <li
                          key={d.id}
                          className="flex items-center justify-between rounded-xl border border-brand-100 bg-brand-50/50 px-3 py-2 text-sm"
                        >
                          <span>
                            {d.version_id}
                            {d.is_active && (
                              <span className="badge ml-2 bg-emerald-100 text-emerald-800">
                                {t('admin.legal.active', { defaultValue: 'Aktywny' })}
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
                              {t('admin.legal.set_active', { defaultValue: 'Ustaw jako aktywny' })}
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}

                  {showForm === value ? (
                    <div className="mt-3 rounded-xl border border-brand-100 bg-white p-4">
                      <label className="label">
                        {t('admin.legal.version_id', { defaultValue: 'Wersja (np. 2025-01-01)' })}
                      </label>
                      <input
                        type="text"
                        value={formVersionId}
                        onChange={(e) => setFormVersionId(e.target.value)}
                        placeholder="2025-01-01"
                        className="input mt-1"
                      />
                      <label className="label mt-3">
                        {t('admin.legal.content_url', { defaultValue: 'URL dokumentu (PDF lub strona)' })}
                      </label>
                      <input
                        type="url"
                        value={formContentUrl}
                        onChange={(e) => setFormContentUrl(e.target.value)}
                        placeholder="https://..."
                        className="input mt-1"
                      />
                      <div className="mt-4 flex gap-2">
                        <button
                          type="button"
                          onClick={handleCreate}
                          disabled={saving || !formVersionId.trim()}
                          className="btn-primary"
                        >
                          {saving ? t('common.saving', { defaultValue: 'Zapisywanie...' }) : t('common.save', { defaultValue: 'Zapisz' })}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setShowForm(null)
                            setFormVersionId('')
                            setFormContentUrl('')
                          }}
                          disabled={saving}
                          className="btn-secondary"
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
                      }}
                      className="btn-secondary btn-sm mt-2"
                    >
                      + {t('admin.legal.add_version', { defaultValue: 'Dodaj wersję' })}
                    </button>
                  )}
                </div>
              )
            })}
          </>
        )}
      </section>
    </div>
  )
}
