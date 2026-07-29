import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconMessageCircle } from '@tabler/icons-react'

import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import {
  resolveEntityCorrespondenceHref,
  type EntityCorrespondenceRef,
} from '../../utils/entityCorrespondence'

type Props = {
  refs: EntityCorrespondenceRef[]
  /** Scopes Inbox hub when no thread found (candidate-only inbox query). */
  candidateId?: string | null
  className?: string
  /** Compact control for rails / headers. */
  size?: 'sm' | 'md'
  testId?: string
}

/**
 * Operator CTA: open the latest Threads conversation for an entity,
 * or Inbox when none is linked yet.
 */
export default function EntityCorrespondenceOpen({
  refs,
  candidateId,
  className,
  size = 'sm',
  testId = 'entity-correspondence-open',
}: Props) {
  const { t } = useI18n()
  const [href, setHref] = useState(CRM_APP_PATHS.inbox)
  const [hasThread, setHasThread] = useState(false)
  const [loading, setLoading] = useState(true)

  const refsKey = refs.map((r) => `${r.entityType}:${r.entityId}`).join('|')
  const cand = String(candidateId || '').trim()

  useEffect(() => {
    const controller = new AbortController()
    let mounted = true
    setLoading(true)
    void resolveEntityCorrespondenceHref(refs, { candidateId: cand || undefined, signal: controller.signal })
      .then((res) => {
        if (!mounted) return
        setHref(res.href)
        setHasThread(Boolean(res.threadId))
      })
      .catch(() => {
        if (!mounted) return
        setHref(cand ? `${CRM_APP_PATHS.inbox}?candidateId=${encodeURIComponent(cand)}` : CRM_APP_PATHS.inbox)
        setHasThread(false)
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
      controller.abort()
    }
    // refsKey captures refs content
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refsKey, cand])

  const label = hasThread
    ? t('app.communications.actions.open_thread', { defaultValue: 'Открыть переписку' })
    : t('app.communications.actions.open_inbox', { defaultValue: 'Переписка' })

  const sizeCls =
    size === 'md'
      ? 'gap-2 rounded-lg px-3 py-2 text-sm font-semibold'
      : 'gap-1.5 rounded-lg px-3 py-2 text-xs font-medium'

  return (
    <Link
      to={href}
      className={
        className ||
        `inline-flex items-center border border-slate-200 bg-white text-slate-800 hover:border-brand-300 hover:bg-brand-50/50 ${sizeCls}`
      }
      data-testid={testId}
      aria-busy={loading || undefined}
    >
      <IconMessageCircle size={size === 'md' ? 18 : 14} stroke={1.8} />
      {label}
    </Link>
  )
}
