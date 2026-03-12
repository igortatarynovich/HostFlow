import { useMemo } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import type { PublicDocumentEntry, PublicDocumentType } from '../../api/publicIntake'
import { usePublicStatus } from '../../modules/public-intake/usePublicStatus'
import { useI18n } from '../../i18n'
import { PublicTimeline } from './components/PublicTimeline'
import { NotificationSettings } from './components/NotificationSettings'
import { formatDocumentStatus, getDocumentTitle } from './utils/documents'
import { PublicLocaleSwitcher } from '../../components/public/PublicLocaleSwitcher'

type DocCard = {
  code: string
  required: boolean
  meta?: PublicDocumentType
  entry?: PublicDocumentEntry
}

export default function PublicStatusPage() {
  const { token } = useParams<{ token: string }>()
  const { t, locale } = useI18n()
  const { loading, error, state, refreshing } = usePublicStatus(token)

  const checklist = state?.checklist
  const docs: PublicDocumentEntry[] = state?.documents?.documents ?? []
  const docTypes = state?.documents?.doc_types
  const docTypeMap = useMemo<Record<string, PublicDocumentType>>(
    () => (docTypes ?? {}) as Record<string, PublicDocumentType>,
    [docTypes]
  )

  const docCards = useMemo<DocCard[]>(() => {
    const entries: DocCard[] = []
    const byType = new Map(docs.map((doc) => [doc.doc_type, doc]))
    const append = (codes: string[] | undefined, required: boolean) => {
      if (!codes) return
      codes.forEach((code) => {
        entries.push({
          code,
          required,
          meta: docTypeMap[code],
          entry: byType.get(code),
        })
      })
    }
    append(checklist?.requiredTypes, true)
    append(checklist?.optionalTypes, false)
    docs.forEach((doc) => {
      if (!entries.find((item) => item.code === doc.doc_type)) {
        entries.push({
          code: doc.doc_type,
          required: false,
          meta: docTypeMap[doc.doc_type],
          entry: doc,
        })
      }
    })
    return entries
  }, [checklist, docTypeMap, docs])

  const requiredDocCards = useMemo(() => docCards.filter((card) => card.required), [docCards])
  const readyRequiredCount = useMemo(
    () => requiredDocCards.filter((card) => Boolean(card.entry?.has_files)).length,
    [requiredDocCards]
  )

  const timelineEntries = state?.timeline ?? []

  const stageTranslation = state?.stage
    ? t(`public.intake.stage.${state.stage}`, { defaultValue: state.stage })
    : null
  const statusFallback = state?.status
    ? t(`public.intake.status.${state.status}`, { defaultValue: state.status })
    : null
  const stageLabel = stageTranslation || statusFallback || t('public.intake.status.draft')
  const documentSummary = state?.documents?.summary
  const requiredSummary = documentSummary?.required
  const summaryReady = requiredSummary?.ready ?? 0
  const summaryPending = requiredSummary?.in_progress ?? 0
  const summaryMissing = requiredSummary?.missing_count ?? requiredSummary?.missing?.length ?? 0

  if (!token) {
    return <Navigate to="/public" replace />
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8">
      <div className="mx-auto max-w-4xl space-y-4">
        <div className="flex justify-end">
          <PublicLocaleSwitcher />
        </div>
        <header className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">HostFlow</p>
          <h1 className="mt-2 text-2xl font-semibold text-slate-900">{t('public.status_page.title')}</h1>
          <p className="mt-2 text-sm text-slate-600">{t('public.status_page.description')}</p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <span className="rounded-full bg-blue-50 px-3 py-1 text-blue-700">
              {t('public.status_page.current_status', { values: { status: stageLabel } })}
            </span>
            {state?.expires_at && (
              <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">
                {t('public.status_page.expires_at', {
                  values: { date: new Date(state.expires_at).toLocaleDateString(locale) },
                })}
              </span>
            )}
            {refreshing && (
              <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-700 flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
                {t('public.status_page.updating', { defaultValue: 'Обновляется...' })}
              </span>
            )}
          </div>
          {state?.expires_at && (
            <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <p className="font-semibold">{t('public.status_page.temporary_notice.title')}</p>
              <p className="text-xs">
                {t('public.status_page.temporary_notice.body', {
                  values: { datetime: new Date(state.expires_at).toLocaleString(locale) },
                })}
              </p>
            </div>
          )}
        </header>

        {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}

        {loading && !state ? (
          <p className="text-sm text-slate-500">{t('common.loading')}</p>
        ) : state ? (
          <>
            <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">{t('public.status_page.timeline.title')}</h2>
                  <p className="text-sm text-slate-500">{t('public.status_page.timeline.subtitle')}</p>
              </div>
              {state?.contacts && (
                <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                  <p className="text-xs uppercase tracking-wide text-slate-500">{t('public.status_page.contacts')}</p>
                  {state.contacts.email && <p className="text-sm font-semibold text-slate-900">{state.contacts.email}</p>}
                  {state.contacts.phone && (
                    <p className="text-sm text-slate-700">
                      {state.contacts.phone_country_code} {state.contacts.phone}
                    </p>
                  )}
                </div>
              )}
            </div>
              <div className="mt-4">
                <PublicTimeline entries={timelineEntries} />
              </div>
            </section>

            <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
              <h2 className="text-lg font-semibold text-slate-900">{t('public.status_page.documents.title')}</h2>
              <div className="mt-2 flex flex-wrap gap-3 text-sm text-slate-600">
                <span className="rounded-full bg-slate-100 px-3 py-1">
                  {t('public.status_page.documents.required_badge', {
                    values: { ready: readyRequiredCount, total: requiredDocCards.length || '—' },
                  })}
                </span>
                {documentSummary && (
                  <>
                    <span className="rounded-full bg-green-50 px-3 py-1 text-green-700">
                      {t('public.status_page.documents.summary.completed', {
                        values: { count: summaryReady },
                      })}
                    </span>
                    <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-700">
                      {t('public.status_page.documents.summary.pending', {
                        values: { count: summaryPending },
                      })}
                    </span>
                    <span className="rounded-full bg-slate-100 px-3 py-1">
                      {t('public.status_page.documents.summary.missing', {
                        values: { count: summaryMissing },
                      })}
                    </span>
                  </>
                )}
              </div>
              <div className="mt-4 divide-y divide-slate-100 border border-slate-100 rounded-2xl">
                {docCards.map((card) => {
                  const title = getDocumentTitle(card.meta, card.code, locale)
                  const statusLabel = formatDocumentStatus(card.entry?.status, t, card.required)
                  return (
                    <div key={card.code} className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{title}</p>
                        <p className="text-xs text-slate-500">
                          {card.required
                            ? t('public.status_page.documents.required')
                            : t('public.status_page.documents.optional')}
                        </p>
                      </div>
                      <div className="text-sm text-slate-700">
                        {statusLabel}
                        {card.entry?.download_url && (
                          <a
                            href={card.entry.download_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="ml-3 text-xs text-blue-600 hover:underline"
                          >
                            {t('public.status_page.documents.open_file')}
                          </a>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>

            <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
              <NotificationSettings
                token={token}
                initialEmail={state?.contacts?.email}
                initialPhone={state?.contacts?.phone}
              />
            </section>
          </>
        ) : (
          <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
            {t('public.status_page.errors.invalid_link')}{' '}
            <Link className="underline" to="/public">
              {t('public.status_page.cta.get_new')}
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
