import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { StatusBadge } from '../../components/ui/StatusBadge'
import type { StatusBadgeSemantic } from '../../components/ui/statusBadgeSemantics'
import { useI18n } from '../../i18n'
import {
  presentVacancyEligibility,
  type EligibilityProjection,
  type EligibilityView,
} from './vacancyEligibilityPresentation'

const STATUS_SEMANTIC: Record<string, StatusBadgeSemantic> = {
  match: 'success',
  no_match: 'warning',
  needs_info: 'neutral',
  needs_review: 'info',
}

export function VacancyEligibilityBlock({ view }: { view: EligibilityView }) {
  const [open, setOpen] = useState(false)
  return (
    <section className="border-t border-slate-100 px-3 py-3" data-testid="vacancy-eligibility" data-eligibility={view.status}>
      <p className="text-xs text-slate-500">{view.caption}</p>
      <p className="mt-0.5 text-sm font-medium text-slate-900">{view.heading}</p>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <StatusBadge size="sm" semantic={STATUS_SEMANTIC[view.status] || 'neutral'} label={view.statusLabel} />
        <span className="text-xs text-slate-600">{view.countLabel}</span>
      </div>
      <Button
        variant="link"
        size="sm"
        className="mt-1"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {view.detailsLabel}
      </Button>
      {open ? (
        <ul className="mt-2 space-y-2">
          {view.rows.map((row) => (
            <li key={`${row.requirement}-${row.result}`} className="text-sm text-slate-800">
              <p>
                <span className="font-medium">{row.requirement}</span>
                <span className="text-slate-500"> — {row.result}</span>
              </p>
              {row.evidence ? <p className="text-xs text-slate-600">{row.evidence}</p> : null}
              {row.source ? <p className="text-xs text-slate-500">{row.source}</p> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}

export function CandidateVacancyEligibility({
  candidateId,
  vacancyId,
  refreshKey = 0,
}: {
  candidateId: string
  vacancyId: string | null
  refreshKey?: number
}) {
  const { locale } = useI18n()
  const [projection, setProjection] = useState<EligibilityProjection | null>(null)

  useEffect(() => {
    if (!vacancyId) {
      setProjection(null)
      return
    }
    let cancelled = false
    void api.get<EligibilityProjection>(
      `/candidates/${candidateId}/vacancies/${vacancyId}/professional-eligibility`,
    ).then((response) => {
      if (!cancelled) setProjection(response.data)
    }).catch(() => {
      if (!cancelled) setProjection(null)
    })
    return () => {
      cancelled = true
    }
  }, [candidateId, vacancyId, refreshKey])

  if (!vacancyId) return null
  const view = presentVacancyEligibility(projection, locale)
  if (!view) return null
  return <VacancyEligibilityBlock view={view} />
}
