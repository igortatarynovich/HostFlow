import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCompanyIntakeConfig } from '../../api/companyIntake'
import { PublicPageShell } from './components/PublicPageShell'
import type { ClientChannelLanding } from '../../utils/clientAcquisitionDefaults'

const DEFAULT_LANDING: ClientChannelLanding = {
  headline: 'Нужен персонал?',
  subheadline: 'Оставьте заявку — мы свяжемся с вами и предложим решение по подбору персонала.',
  cta: 'Оставить заявку',
}

export default function ClientInquiryLandingPage() {
  const { publicToken = '' } = useParams<{ publicToken: string }>()
  const [landing, setLanding] = useState<ClientChannelLanding>(DEFAULT_LANDING)
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
          <p className="text-center text-sm text-slate-500">Загрузка…</p>
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
