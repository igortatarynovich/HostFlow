import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listSalesInquiryPossibleDuplicates, type SalesInquiryDuplicateHint } from '../../api/applications'
import { salesInquiryPath } from '../../app/salesPaths'
import { useI18n } from '../../i18n'

type Props = {
  applicationId: string
}

function matchLabel(
  reason: SalesInquiryDuplicateHint['match_reason'],
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  if (reason === 'phone_and_email') {
    return t('app.sales_inquiry.duplicates.match_phone_email', {
      defaultValue: 'тот же телефон и email',
    })
  }
  if (reason === 'phone') {
    return t('app.sales_inquiry.duplicates.match_phone', { defaultValue: 'тот же телефон' })
  }
  return t('app.sales_inquiry.duplicates.match_email', { defaultValue: 'тот же email' })
}

/** Operator hint: other client inquiries sharing phone/email. */
export default function SalesInquiryPossibleDuplicatesSection({ applicationId }: Props) {
  const { t } = useI18n()
  const [items, setItems] = useState<SalesInquiryDuplicateHint[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    void listSalesInquiryPossibleDuplicates(applicationId)
      .then((res) => {
        if (!mounted) return
        setItems(Array.isArray(res.items) ? res.items : [])
      })
      .catch(() => {
        if (mounted) setItems([])
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [applicationId])

  if (loading || items.length === 0) return null

  return (
    <div
      className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5"
      data-testid="sales-inquiry-possible-duplicates"
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-amber-900">
        {t('app.sales_inquiry.duplicates.title', { defaultValue: 'Возможные дубли' })}
      </p>
      <p className="mt-1 text-[11px] text-amber-800/90">
        {t('app.sales_inquiry.duplicates.hint', {
          defaultValue: 'Другие обращения с тем же телефоном или email. Обычно одна фирма — один клиент.',
        })}
      </p>
      <ul className="mt-2 space-y-1.5">
        {items.map((hit) => {
          const app = hit.application
          return (
            <li key={app.id}>
              <Link
                to={salesInquiryPath(app.id)}
                className="block rounded-md border border-amber-200/80 bg-white/80 px-2.5 py-1.5 text-sm hover:border-brand-300 hover:bg-brand-50/40"
              >
                <span className="font-medium text-slate-900">{app.title}</span>
                <span className="mt-0.5 block text-[11px] text-slate-500">
                  {app.contact.name}
                  {app.contact.phone ? ` · ${app.contact.phone}` : ''}
                  {app.contact.email ? ` · ${app.contact.email}` : ''}
                  {' · '}
                  {matchLabel(hit.match_reason, t)}
                </span>
              </Link>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
