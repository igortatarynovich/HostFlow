import { useMemo, useState } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { usePublicStatus } from '../../modules/public-intake/usePublicStatus'
import { requestPublicDocumentsAccess } from '../../api/publicIntake'
import { useToast } from '../../components/Toast'
import { PublicLocaleSwitcher } from '../../components/public/PublicLocaleSwitcher'
import { getDocumentTitle, formatDocumentStatus } from './utils/documents'
import { useRobotsMeta } from '../../hooks/useRobotsMeta'

export default function PublicDocumentsUploadPage() {
  useRobotsMeta({ index: false, follow: false })
  const { token } = useParams<{ token: string }>()
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const { loading, error, state } = usePublicStatus(token)
  const [email, setEmail] = useState('')
  const [phoneCountryCode, setPhoneCountryCode] = useState('+48')
  const [phone, setPhone] = useState('')
  const [verifying, setVerifying] = useState(false)
  const [accessUrl, setAccessUrl] = useState<string | null>(null)

  const docTypes = useMemo(() => (state?.documents?.doc_types ?? {}) as Record<string, any>, [state?.documents?.doc_types])
  const docs = state?.documents?.documents ?? []

  if (!token) return <Navigate to="/public" replace />

  const onVerify = async () => {
    if (!email.trim() && !phone.trim()) {
      notify({
        title: t('public.documents_upload.contact_required', { defaultValue: 'Enter phone or email to continue' }),
        variant: 'error',
      })
      return
    }
    try {
      setVerifying(true)
      const data = await requestPublicDocumentsAccess(token, {
        email: email.trim() || undefined,
        phone_country_code: phone.trim() ? phoneCountryCode.trim() : undefined,
        phone: phone.trim() || undefined,
      })
      setAccessUrl(data.upload_url)
      notify({
        title: t('public.documents_upload.verified', { defaultValue: 'Identity verified. You can upload documents now.' }),
        variant: 'success',
      })
    } catch (err: any) {
      const detail = err?.response?.data?.detail || t('public.documents_upload.verify_failed', { defaultValue: 'Verification failed' })
      notify({ title: t('public.documents_upload.verify_failed', { defaultValue: 'Verification failed' }), description: detail, variant: 'error' })
    } finally {
      setVerifying(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8">
      <div className="mx-auto max-w-4xl space-y-4">
        <div className="flex justify-end">
          <PublicLocaleSwitcher />
        </div>
        <section className="card p-6">
          <h1 className="text-2xl font-semibold text-slate-900">
            {t('public.documents_upload.title', { defaultValue: 'Upload requested documents' })}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {t('public.documents_upload.description', {
              defaultValue: 'Enter your phone or email first. We will open document upload without re-filling the questionnaire.',
            })}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <input
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
              placeholder={t('public.intake.forms.contacts.email')}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <input
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
              placeholder={t('public.intake.forms.contacts.phone_country_code', { defaultValue: 'Country code' })}
              value={phoneCountryCode}
              onChange={(e) => setPhoneCountryCode(e.target.value)}
            />
            <input
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
              placeholder={t('public.intake.forms.contacts.phone')}
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>
          <div className="mt-4">
            <button
              type="button"
              className="btn-primary"
              onClick={() => void onVerify()}
              disabled={verifying}
            >
              {verifying
                ? t('public.documents_upload.verifying', { defaultValue: 'Verifying...' })
                : t('public.documents_upload.verify_button', { defaultValue: 'Verify and open upload' })}
            </button>
          </div>
          {accessUrl ? (
            <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
              <p className="font-semibold">
                {t('public.documents_upload.ready', { defaultValue: 'Access granted' })}
              </p>
              <Link className="mt-2 inline-flex text-emerald-900 underline" to={accessUrl}>
                {t('public.documents_upload.open_upload', { defaultValue: 'Open document upload' })}
              </Link>
            </div>
          ) : null}
        </section>

        {error ? <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p> : null}

        {loading && !state ? (
          <p className="text-sm text-slate-500">{t('common.loading')}</p>
        ) : (
          <section className="card p-6">
            <h2 className="text-lg font-semibold text-slate-900">
              {t('public.documents_upload.required_list', { defaultValue: 'Requested documents' })}
            </h2>
            <div className="mt-4 divide-y divide-slate-100 rounded-2xl border border-slate-100">
              {docs.map((doc) => (
                <div key={doc.id} className="flex items-center justify-between gap-3 p-3">
                  <div className="text-sm font-medium text-slate-900">
                    {getDocumentTitle(docTypes[doc.doc_type], doc.doc_type, locale)}
                  </div>
                  <div className="text-xs text-slate-600">
                    {formatDocumentStatus(doc.status, t, true)}
                  </div>
                </div>
              ))}
              {!docs.length ? (
                <div className="p-3 text-sm text-slate-500">
                  {t('public.documents_upload.no_docs', { defaultValue: 'No requested documents yet.' })}
                </div>
              ) : null}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

