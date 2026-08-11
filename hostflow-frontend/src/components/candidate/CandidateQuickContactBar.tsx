import { IconMail, IconPhone } from '@tabler/icons-react'
import { useI18n } from '../../i18n'

type CandidateQuickContactBarProps = {
  phone?: string | null
  email?: string | null
  preferredMessenger?: string | null
}

function digitsOnly(value: string): string {
  return value.replace(/\D/g, '')
}

export function CandidateQuickContactBar({
  phone,
  email,
  preferredMessenger,
}: CandidateQuickContactBarProps) {
  const { t } = useI18n()
  const phoneTrimmed = String(phone || '').trim()
  const emailTrimmed = String(email || '').trim()
  if (!phoneTrimmed && !emailTrimmed) return null

  const telHref = phoneTrimmed ? `tel:${phoneTrimmed.replace(/\s/g, '')}` : null
  const waDigits = phoneTrimmed ? digitsOnly(phoneTrimmed) : ''
  const showWhatsApp =
    Boolean(waDigits) &&
    (preferredMessenger === 'whatsapp' || preferredMessenger === 'viber' || !preferredMessenger)

  return (
    <section
      className="rounded-xl border border-brand-200 bg-brand-50/60 p-4 shadow-sm"
      data-testid="m1-candidate-quick-contact"
    >
      <p className="text-sm font-semibold text-slate-900">
        {t('app.candidates.quick_contact.title', { defaultValue: 'Contact the candidate' })}
      </p>
      <p className="mt-1 text-sm text-slate-600">
        {t('app.candidates.quick_contact.subtitle', { defaultValue: 'Next step — first contact.' })}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {telHref ? (
          <a
            href={telHref}
            className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700"
          >
            <IconPhone size={16} stroke={1.8} />
            {t('app.candidates.quick_contact.call', { defaultValue: 'Call' })}
          </a>
        ) : null}
        {showWhatsApp && waDigits ? (
          <a
            href={`https://wa.me/${waDigits}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-900 hover:bg-emerald-100"
          >
            WhatsApp
          </a>
        ) : null}
        {emailTrimmed ? (
          <a
            href={`mailto:${emailTrimmed}`}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-800 hover:bg-slate-50"
          >
            <IconMail size={16} stroke={1.8} />
            Email
          </a>
        ) : null}
      </div>
    </section>
  )
}
