import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCompanyIntakeConfig } from '../../api/companyIntake'
import { useI18n } from '../../i18n'
import { PublicPageShell } from './components/PublicPageShell'
import type { ClientChannelLanding } from '../../utils/clientAcquisitionDefaults'

export default function ClientInquiryLandingPage() {
  const { publicToken = '' } = useParams<{ publicToken: string }>()
  const { t } = useI18n()
  const defaultLanding: ClientChannelLanding = {
    headline: t('app.client_inquiry.landing.headline', { defaultValue: 'Need staff?' }),
    subheadline: t('app.client_inquiry.landing.subheadline', {
      defaultValue: 'Leave a request — we will contact you and propose a recruitment solution.',
    }),
    cta: t('app.client_inquiry.landing.cta', { defaultValue: 'Submit inquiry' }),
  }
  const [landing, setLanding] = useState<ClientChannelLanding>(defaultLanding)
  const [loading, setLoading] = useState(true)

  const applyPath = useMemo(
    () => (publicToken ? `/forms/client-inquiry/${encodeURIComponent(publicToken)}/apply` : '#'),
    [publicToken],
  )

  useEffect(() => {
    if (!publicToken) return
    void getCompanyIntakeConfig(publicToken)
      .then((config) => {
        const fromChannel = config.channel_config?.landing
        if (fromChannel?.headline) setLanding(fromChannel)
      })
      .catch(() => undefined)
      .finally(() => setLoading(false))
  }, [publicToken])

  if (!publicToken) {
    return null
  }

  return (
    <PublicPageShell maxWidth="md" showBrand>
      <div className="rounded-3xl border border-white/70 bg-white/90 p-8 shadow-xl shadow-slate-900/5 sm:p-10">
        {loading ? (
          <p className="text-center text-sm text-slate-500">
            {t('common.loading', { defaultValue: 'Loading…' })}
          </p>
        ) : (
          <div className="space-y-6 text-center">
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-2xl">
              {landing.headline}
            </h1>
            <p className="mx-auto max-w-lg text-base leading-relaxed text-slate-600">{landing.subheadline}</p>
            <Link
              to={applyPath}
              className="inline-flex items-center justify-center rounded-xl bg-brand-600 px-8 py-3 text-base font-semibold text-white shadow-sm hover:bg-brand-700"
              data-testid="client-inquiry-landing-cta"
            >
              {landing.cta}
            </Link>
          </div>
        )}
      </div>
    </PublicPageShell>
  )
}
