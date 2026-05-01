import { useCallback, useEffect, useMemo, useState } from 'react'
import { useI18n } from '../../i18n'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { listDocumentTemplates, type DocumentTemplate } from '../../api/documents'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo } from '../../utils/friendlyError'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

function summarizeTemplateDocs(template: DocumentTemplate): {
  total: number
  required: number
  processDocs: number
} {
  const docs = Array.isArray(template.documents) ? template.documents : []
  let required = 0
  let processDocs = 0
  docs.forEach((doc) => {
    if (doc?.required) required += 1
    if (doc?.process_type && String(doc.process_type).trim() && String(doc.process_type) !== 'none') {
      processDocs += 1
    }
  })
  return { total: docs.length, required, processDocs }
}

export default function DocumentTypesPage() {
  const { t } = useI18n()
  const [templates, setTemplates] = useState<DocumentTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)

  const loadTemplates = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const rows = await listDocumentTemplates(true)
      setTemplates(rows)
    } catch (err) {
      setError(getFriendlyErrorInfo(err, t('admin.documents.types.error'), t))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    loadTemplates()
  }, [loadTemplates])

  const sortedTemplates = useMemo(
    () =>
      [...templates].sort((a, b) => {
        if (a.is_active !== b.is_active) return a.is_active ? -1 : 1
        return String(a.name || '').localeCompare(String(b.name || ''))
      }),
    [templates],
  )

  return (
    <div className="space-y-4">
      <section className="settings-panel">
        <div className="mb-2">
          <SettingsSubpageHeader
            backLabel={t('admin.settings.subpage.back_all')}
            kicker={t('admin.documents.types.header_kicker')}
            title={t('admin.documents.types.title')}
            subtitle={t('admin.documents.types.description')}
          />
        </div>

        {error ? (
          <ErrorRecoveryBanner
            info={error}
            onRetry={loadTemplates}
            retryLabel={t('common.actions.retry')}
            {...friendlyErrorBannerSecondary(error, CRM_APP_PATHS.settingsDocs, t('admin.documents.types.title'))}
            compact
          />
        ) : null}

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500">
                <th className="px-3 py-2 font-medium">{t('admin.documents.types.table.code')}</th>
                <th className="px-3 py-2 font-medium">{t('admin.documents.types.table.name')}</th>
                <th className="px-3 py-2 font-medium">{t('admin.documents.types.table.required')}</th>
                <th className="px-3 py-2 font-medium">{t('admin.documents.types.table.total')}</th>
                <th className="px-3 py-2 font-medium">{t('admin.documents.types.table.process')}</th>
                <th className="px-3 py-2 font-medium">{t('admin.documents.types.table.status')}</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr className="border-t">
                  <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                    {t('common.loading')}
                  </td>
                </tr>
              ) : null}
              {!loading && !sortedTemplates.length ? (
                <tr className="border-t">
                  <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                    {t('admin.documents.types.empty')}
                  </td>
                </tr>
              ) : null}
              {sortedTemplates.map((template) => {
                const summary = summarizeTemplateDocs(template)
                return (
                  <tr key={template.id} className="border-t">
                    <td className="px-3 py-2 font-mono text-xs uppercase text-slate-500">{template.code}</td>
                    <td className="px-3 py-2">{template.name}</td>
                    <td className="px-3 py-2">{summary.required}</td>
                    <td className="px-3 py-2">{summary.total}</td>
                    <td className="px-3 py-2">{summary.processDocs}</td>
                  <td className="px-3 py-2">
                    {template.is_active ? (
                      <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
                        {t('common.active')}
                      </span>
                    ) : (
                      <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                        {t('common.inactive')}
                      </span>
                    )}
                  </td>
                </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
