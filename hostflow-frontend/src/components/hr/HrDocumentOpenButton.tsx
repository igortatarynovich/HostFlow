import { useState } from 'react'
import clsx from 'clsx'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import { openHrDocumentInNewTab } from '../../utils/hrDocumentOpen'

type Props = {
  openUrl?: string | null
  label?: string
  className?: string
  variant?: 'link' | 'button'
}

export default function HrDocumentOpenButton({
  openUrl,
  label,
  className,
  variant = 'link',
}: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [busy, setBusy] = useState(false)
  const text = label ?? t('app.hr.review.open_docs', { defaultValue: 'Open' })
  const disabled = busy || !String(openUrl || '').trim()

  const onOpen = async () => {
    setBusy(true)
    try {
      await openHrDocumentInNewTab({ openUrl })
    } catch {
      notify({
        variant: 'error',
        title: t('app.hr.employee_detail.doc_open_error', {
          defaultValue: 'Could not open document file',
        }),
      })
    } finally {
      setBusy(false)
    }
  }

  if (variant === 'button') {
    return (
      <button
        type="button"
        className={clsx('btn-secondary btn-sm', className)}
        disabled={disabled}
        onClick={() => void onOpen()}
      >
        {text}
      </button>
    )
  }

  return (
    <button
      type="button"
      className={clsx('font-medium text-brand-700 hover:underline disabled:opacity-50', className)}
      disabled={disabled}
      onClick={() => void onOpen()}
    >
      {text}
    </button>
  )
}
