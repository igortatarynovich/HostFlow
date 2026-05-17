import type { HrReviewDocumentRow } from '../../api/workforce'
import HrDocumentOpenButton from './HrDocumentOpenButton'
import { useI18n } from '../../i18n'

type Props = {
  documents: HrReviewDocumentRow[]
}

function docStatusLabel(t: ReturnType<typeof useI18n>['t'], d: HrReviewDocumentRow): string {
  const raw = String(d.status || '').toLowerCase()
  if (d.verified || raw === 'verified') {
    return t('app.hr.review.doc_status.verified', { defaultValue: 'Verified' })
  }
  if (raw === 'missing') return t('app.hr.review.doc_status.missing', { defaultValue: 'Missing' })
  if (raw === 'needs_data') return t('app.hr.review.doc_status.needs_data', { defaultValue: 'Needs data' })
  if (raw === 'uploaded' || raw === 'pending') {
    return t('app.hr.review.doc_status.pending', { defaultValue: 'Awaiting verification' })
  }
  return raw.replace(/_/g, ' ') || '—'
}

export default function HrDocumentsForApproval({ documents }: Props) {
  const { t } = useI18n()
  if (documents.length === 0) return null

  return (
    <section id="hr-review-documents" className="scroll-mt-24 rounded-xl border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-slate-900">
        {t('app.hr.review_case.docs_required', { defaultValue: 'Documents required for approval' })}
      </h2>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b text-left text-slate-500">
              <th className="py-1 pr-2">{t('app.hr.review.doc_col', { defaultValue: 'Document' })}</th>
              <th className="py-1 pr-2">{t('app.hr.review.status_col', { defaultValue: 'Status' })}</th>
              <th className="py-1">{t('app.hr.review.action_col', { defaultValue: 'Action' })}</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((d) => {
              const raw = String(d.status || '').toLowerCase()
              const scrollHref = '#hr-employee-linked-documents'
              return (
                <tr key={d.document_key} className="border-b border-slate-50 last:border-0">
                  <td className="py-2 pr-2 font-medium text-slate-800">{d.label}</td>
                  <td className="py-2 pr-2">
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-medium">
                      {docStatusLabel(t, d)}
                    </span>
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap items-center gap-2">
                      {d.open_url || d.file_url ? (
                        <HrDocumentOpenButton openUrl={d.open_url ?? d.file_url} />
                      ) : d.document_id ? (
                        <span className="text-slate-400 text-[10px]">
                          {t('app.hr.employee_detail.doc_open_pending', {
                            defaultValue: 'File link pending',
                          })}
                        </span>
                      ) : (
                        <a href={scrollHref} className="font-medium text-brand-700 hover:underline">
                          {t('app.hr.review.open_docs', { defaultValue: 'Open' })}
                        </a>
                      )}
                      {raw === 'missing' ? (
                        <a href={scrollHref} className="text-brand-700 hover:underline">
                          {t('app.hr.review.upload_docs', { defaultValue: 'Upload' })}
                        </a>
                      ) : null}
                      {!d.verified && raw !== 'missing' && (d.open_url || d.file_url) ? (
                        <HrDocumentOpenButton
                          openUrl={d.open_url ?? d.file_url}
                          label={t('app.hr.review.verify_docs', { defaultValue: 'Verify' })}
                        />
                      ) : null}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
