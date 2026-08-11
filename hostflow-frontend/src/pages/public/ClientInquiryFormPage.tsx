import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCompanyIntakeConfig, submitCompanyIntake } from '../../api/companyIntake'
import { useI18n } from '../../i18n'
import { PublicPageShell } from './components/PublicPageShell'
import { buildPublicClientInquiryUrl } from '../../utils/clientInquiryUrl'

type NeedRole = 'drivers' | 'warehouse' | 'office' | 'other'
type PeopleCount = '1-2' | '3-5' | '6-10' | '10+'
type NeededWhen = 'urgent' | 'week' | 'month' | 'anytime'

const ROLE_IDS: NeedRole[] = ['drivers', 'warehouse', 'office', 'other']
const COUNT_OPTIONS: { id: PeopleCount; label: string }[] = [
  { id: '1-2', label: '1–2' },
  { id: '3-5', label: '3–5' },
  { id: '6-10', label: '6–10' },
  { id: '10+', label: '10+' },
]
const WHEN_IDS: NeededWhen[] = ['urgent', 'week', 'month', 'anytime']

function ChipGroup<T extends string>({
  value,
  options,
  onChange,
  name,
}: {
  value: T | ''
  options: { id: T; label: string }[]
  onChange: (v: T) => void
  name: string
}) {
  return (
    <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={name}>
      {options.map((opt) => (
        <button
          key={opt.id}
          type="button"
          role="radio"
          aria-checked={value === opt.id}
          onClick={() => onChange(opt.id)}
          className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
            value === opt.id
              ? 'border-brand-500 bg-brand-50 text-brand-800'
              : 'border-slate-200 text-slate-700 hover:border-slate-300'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

export default function ClientInquiryFormPage() {
  const { publicToken = '' } = useParams<{ publicToken: string }>()
  const { t, locale } = useI18n()
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [companyName, setCompanyName] = useState('')
  const [contactName, setContactName] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [needRole, setNeedRole] = useState<NeedRole | ''>('')
  const [peopleCount, setPeopleCount] = useState<PeopleCount | ''>('')
  const [neededWhen, setNeededWhen] = useState<NeededWhen | ''>('')
  const [comment, setComment] = useState('')

  const roleOptions = useMemo(
    () =>
      ROLE_IDS.map((id) => ({
        id,
        label: t(`public.client_inquiry.roles.${id}`, {
          defaultValue:
            id === 'drivers'
              ? 'Drivers'
              : id === 'warehouse'
                ? 'Warehouse'
                : id === 'office'
                  ? 'Office'
                  : 'Other',
        }),
      })),
    [t],
  )

  const whenOptions = useMemo(
    () =>
      WHEN_IDS.map((id) => ({
        id,
        label: t(`public.client_inquiry.when.${id}`, {
          defaultValue:
            id === 'urgent'
              ? 'Urgent'
              : id === 'week'
                ? 'Week'
                : id === 'month'
                  ? 'Month'
                  : 'Anytime',
        }),
      })),
    [t],
  )

  useEffect(() => {
    if (!publicToken) return
    void getCompanyIntakeConfig(publicToken).catch(() => undefined)
  }, [publicToken])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!publicToken || !companyName.trim() || !contactName.trim()) return
    if (!phone.trim() && !email.trim()) {
      setError(
        t('public.client_inquiry.errors.contact_required', {
          defaultValue: 'Enter a phone or email',
        }),
      )
      return
    }
    if (!needRole || !peopleCount || !neededWhen) {
      setError(
        t('public.client_inquiry.errors.required', {
          defaultValue: 'Fill in all required fields',
        }),
      )
      return
    }

    setLoading(true)
    setError(null)
    try {
      const roleLabel = roleOptions.find((o) => o.id === needRole)?.label ?? needRole
      await submitCompanyIntake(publicToken, {
        company: { name: companyName.trim() },
        contact: {
          full_name: contactName.trim(),
          phone: phone.trim() || null,
          email: email.trim() || null,
        },
        need: {
          what_needed: `${roleLabel} · ${peopleCount}`,
          needed_when: whenOptions.find((o) => o.id === neededWhen)?.label ?? neededWhen,
          requirements: comment.trim() || null,
        },
        consent: {
          terms_accepted: true,
          privacy_accepted: true,
          data_processing_accepted: true,
          accuracy_confirmed: true,
          terms_version: 'client-inquiry-v1',
          privacy_version: 'client-inquiry-v1',
        },
        language: locale.startsWith('pl') ? 'pl' : locale.startsWith('ru') ? 'ru' : 'en',
        source: 'website',
        source_context: {
          landing_page: buildPublicClientInquiryUrl(publicToken),
          submitted_flow: 'client_inquiry_short',
        },
      })
      setSubmitted(true)
    } catch {
      setError(
        t('public.client_inquiry.errors.submit_failed', {
          defaultValue: 'Could not submit the inquiry. Please try again.',
        }),
      )
    } finally {
      setLoading(false)
    }
  }

  if (!publicToken) return null

  if (submitted) {
    return (
      <PublicPageShell maxWidth="md" showBrand>
        <div className="rounded-3xl border border-white/70 bg-white/90 p-8 text-center shadow-xl shadow-slate-900/5">
          <h1 className="text-2xl font-semibold text-slate-900">
            {t('public.client_inquiry.success_title', { defaultValue: 'Thank you!' })}
          </h1>
          <p className="mt-3 text-slate-600">
            {t('public.client_inquiry.success_body', {
              defaultValue: 'We received your inquiry and will contact you shortly.',
            })}
          </p>
          <Link
            to={buildPublicClientInquiryUrl(publicToken)}
            className="mt-6 inline-block text-sm font-medium text-brand-700 hover:underline"
          >
            {t('public.client_inquiry.back_to_page', { defaultValue: 'Back to the page' })}
          </Link>
        </div>
      </PublicPageShell>
    )
  }

  return (
    <PublicPageShell maxWidth="md" showBrand>
      <form
        onSubmit={(e) => void onSubmit(e)}
        className="space-y-6 rounded-3xl border border-white/70 bg-white/90 p-6 shadow-xl shadow-slate-900/5 sm:p-8"
        data-testid="client-inquiry-form"
      >
        <header>
          <h1 className="text-2xl font-semibold text-slate-900">
            {t('public.client_inquiry.title', { defaultValue: 'Submit an inquiry' })}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {t('public.client_inquiry.subtitle', {
              defaultValue: 'Tell us who you need — we will call you back.',
            })}
          </p>
        </header>

        <fieldset className="space-y-3">
          <legend className="text-sm font-semibold text-slate-900">
            {t('public.client_inquiry.company_legend', { defaultValue: 'Company' })}
          </legend>
          <input
            type="text"
            required
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder={t('public.client_inquiry.company_placeholder', {
              defaultValue: 'Company name',
            })}
            className="w-full rounded-lg border border-slate-200 px-3 py-3 text-sm"
          />
        </fieldset>

        <fieldset className="space-y-3">
          <legend className="text-sm font-semibold text-slate-900">
            {t('public.client_inquiry.contact_legend', { defaultValue: 'Contact person' })}
          </legend>
          <input
            type="text"
            required
            value={contactName}
            onChange={(e) => setContactName(e.target.value)}
            placeholder={t('public.client_inquiry.name_placeholder', { defaultValue: 'Name' })}
            className="w-full rounded-lg border border-slate-200 px-3 py-3 text-sm"
          />
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder={t('public.client_inquiry.phone_placeholder', { defaultValue: 'Phone' })}
            className="w-full rounded-lg border border-slate-200 px-3 py-3 text-sm"
          />
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t('public.client_inquiry.email_placeholder', { defaultValue: 'Email' })}
            className="w-full rounded-lg border border-slate-200 px-3 py-3 text-sm"
          />
        </fieldset>

        <fieldset className="space-y-3">
          <legend className="text-sm font-semibold text-slate-900">
            {t('public.client_inquiry.need_legend', { defaultValue: 'What is needed' })}
          </legend>
          <p className="text-xs text-slate-500">
            {t('public.client_inquiry.need_hint', { defaultValue: 'Who are you looking for?' })}
          </p>
          <ChipGroup value={needRole} options={roleOptions} onChange={setNeedRole} name="need-role" />
        </fieldset>

        <fieldset className="space-y-3">
          <legend className="text-sm font-semibold text-slate-900">
            {t('public.client_inquiry.count_legend', { defaultValue: 'How many people?' })}
          </legend>
          <ChipGroup
            value={peopleCount}
            options={COUNT_OPTIONS}
            onChange={setPeopleCount}
            name="people-count"
          />
        </fieldset>

        <fieldset className="space-y-3">
          <legend className="text-sm font-semibold text-slate-900">
            {t('public.client_inquiry.when_legend', { defaultValue: 'When do you need them?' })}
          </legend>
          <ChipGroup value={neededWhen} options={whenOptions} onChange={setNeededWhen} name="needed-when" />
        </fieldset>

        <label className="block space-y-2">
          <span className="text-sm font-semibold text-slate-900">
            {t('public.client_inquiry.comment_label', { defaultValue: 'Comment' })}
          </span>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={3}
            placeholder={t('public.client_inquiry.comment_placeholder', {
              defaultValue: 'Additional details',
            })}
            className="w-full rounded-lg border border-slate-200 px-3 py-3 text-sm"
          />
        </label>

        {error ? <p className="text-sm text-rose-600">{error}</p> : null}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {loading
            ? t('public.client_inquiry.submitting', { defaultValue: 'Submitting…' })
            : t('public.client_inquiry.submit', { defaultValue: 'Submit' })}
        </button>
      </form>
    </PublicPageShell>
  )
}
