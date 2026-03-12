import { useState } from 'react'
import { useI18n } from '../../i18n'

type DocumentType = {
  code: string
  labelKey: string
  requiresUpload: boolean
}

const MOCK_TYPES: DocumentType[] = [
  { code: 'passport', labelKey: 'admin.documents.mock.passport', requiresUpload: true },
  { code: 'license', labelKey: 'admin.documents.mock.license', requiresUpload: true },
  { code: 'insurance', labelKey: 'admin.documents.mock.insurance', requiresUpload: false },
]

export default function DocumentTypesPage() {
  const [types] = useState(MOCK_TYPES)
  const { t } = useI18n()

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <header className="mb-4">
          <h2 className="text-xl font-semibold text-slate-900">{t('admin.documents.types.title')}</h2>
          <p className="text-sm text-slate-500">{t('admin.documents.types.description')}</p>
        </header>

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500">
                <th className="px-4 py-2 font-medium">{t('admin.documents.types.table.code')}</th>
                <th className="px-4 py-2 font-medium">{t('admin.documents.types.table.name')}</th>
                <th className="px-4 py-2 font-medium">{t('admin.documents.types.table.required')}</th>
              </tr>
            </thead>
            <tbody>
              {types.map((type) => (
                <tr key={type.code} className="border-t">
                  <td className="px-4 py-2 font-mono text-xs uppercase text-slate-500">{type.code}</td>
                  <td className="px-4 py-2">{t(type.labelKey)}</td>
                  <td className="px-4 py-2">
                    {type.requiresUpload ? (
                      <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
                        {t('admin.documents.types.badge.required')}
                      </span>
                    ) : (
                      <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                        {t('admin.documents.types.badge.optional')}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
