import clsx from 'clsx'
import type { DocumentPackProjection } from '../../api/types'
import { useI18n } from '../../i18n'
import { humanizeToken } from './hrEmployeeUiFormat'

const STATUS_META: Record<
  DocumentPackProjection['status'],
  { labelKey: string; defaultLabel: string; className: string }
> = {
  valid: {
    labelKey: 'app.hr.document_packs.status.valid',
    defaultLabel: 'Valid',
    className: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  },
  warnings: {
    labelKey: 'app.hr.document_packs.status.warnings',
    defaultLabel: 'Warnings',
    className: 'border-amber-200 bg-amber-50 text-amber-950',
  },
  gaps: {
    labelKey: 'app.hr.document_packs.status.gaps',
    defaultLabel: 'Gaps',
    className: 'border-rose-200 bg-rose-50 text-rose-950',
  },
  skeleton: {
    labelKey: 'app.hr.document_packs.status.skeleton',
    defaultLabel: 'Skeleton',
    className: 'border-slate-200 bg-slate-50 text-slate-600',
  },
}

function CountChip({
  label,
  value,
  tone = 'slate',
}: {
  label: string
  value: number
  tone?: 'slate' | 'amber' | 'rose' | 'orange'
}) {
  if (value <= 0) return null
  const toneClass =
    tone === 'amber'
      ? 'border-amber-100 bg-amber-50/90 text-amber-950'
      : tone === 'rose'
        ? 'border-rose-100 bg-rose-50/90 text-rose-950'
        : tone === 'orange'
          ? 'border-orange-100 bg-orange-50/90 text-orange-950'
          : 'border-slate-100 bg-slate-50 text-slate-700'
  return (
    <span className={clsx('inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-medium tabular-nums', toneClass)}>
      <span className="text-slate-500">{label}</span>
      <span>{value}</span>
    </span>
  )
}

function DocList({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{title}</div>
      <ul className="mt-1 list-inside list-disc text-xs text-slate-700">
        {items.map((code) => (
          <li key={code}>{humanizeToken(code)}</li>
        ))}
      </ul>
    </div>
  )
}

function PackCard({ pack }: { pack: DocumentPackProjection }) {
  const { t } = useI18n()
  const status = pack.status || 'valid'
  const meta = STATUS_META[status] || STATUS_META.valid
  const missing = pack.missing ?? []
  const expired = pack.expired ?? []
  const expiringSoon = pack.expiring_soon ?? []
  const missingExpiry = pack.missing_expiry ?? []
  const blockers = pack.blockers ?? []
  const warnings = pack.warnings ?? []
  const gaps = pack.gaps ?? []
  const expiringCount = expiringSoon.length

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{pack.label}</h3>
          {pack.skeleton ? (
            <p className="mt-1 text-xs text-slate-500">
              {t('app.hr.document_packs.skeleton_hint', {
                defaultValue: 'Client-specific requirements will appear here later.',
              })}
            </p>
          ) : null}
        </div>
        <span className={clsx('shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide', meta.className)}>
          {t(meta.labelKey, { defaultValue: meta.defaultLabel })}
        </span>
      </div>

      {!pack.skeleton ? (
        <>
          <div className="mt-3 flex flex-wrap gap-1.5">
            <CountChip
              label={t('app.hr.document_packs.count.missing', { defaultValue: 'Missing' })}
              value={missing.length}
              tone="rose"
            />
            <CountChip
              label={t('app.hr.document_packs.count.expired', { defaultValue: 'Expired' })}
              value={expired.length}
              tone="rose"
            />
            <CountChip
              label={t('app.hr.document_packs.count.expiring', { defaultValue: 'Expiring' })}
              value={expiringCount}
              tone="orange"
            />
            <CountChip
              label={t('app.hr.document_packs.count.missing_expiry', { defaultValue: 'No expiry date' })}
              value={missingExpiry.length}
              tone="amber"
            />
          </div>

          <div className="mt-3 space-y-2">
            <DocList
              title={t('app.hr.document_packs.blockers', { defaultValue: 'Blockers' })}
              items={blockers}
            />
            <DocList
              title={t('app.hr.document_packs.warnings', { defaultValue: 'Warnings' })}
              items={warnings}
            />
            <DocList title={t('app.hr.document_packs.gaps', { defaultValue: 'Gaps' })} items={gaps} />
          </div>
        </>
      ) : null}
    </article>
  )
}

type Props = {
  packs?: DocumentPackProjection[] | null
  loading?: boolean
  error?: string | null
  compact?: boolean
}

export function DocumentPackCards({ packs, loading = false, error = null, compact = false }: Props) {
  const { t } = useI18n()

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
  }

  if (error) {
    return <p className="text-sm text-red-600">{error}</p>
  }

  if (!packs?.length) {
    return (
      <p className="text-sm text-slate-500">
        {t('app.hr.document_packs.empty', { defaultValue: 'No document packs for this profile yet.' })}
      </p>
    )
  }

  return (
    <div className={clsx('grid gap-3', compact ? 'sm:grid-cols-2' : 'md:grid-cols-2 xl:grid-cols-2')}>
      {packs.map((pack) => (
        <PackCard key={pack.code} pack={pack} />
      ))}
    </div>
  )
}
