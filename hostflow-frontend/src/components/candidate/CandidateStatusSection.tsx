import { memo, useState, useCallback } from 'react'
import { IconChevronDown, IconIdBadge2 } from '@tabler/icons-react'
import type { CandidateExtra } from '../../api/types'
import type { RefObject } from 'react'
import type { CandidateProfile } from '../../api/candidate_profiles'
import { useI18n } from '../../i18n'
import { isFieldVisible, isFieldRequired, getFieldLabel } from '../../utils/profileUtils'

type Option = { value: string; label: string; extra?: any }

interface CandidateStatusSectionProps {
  extra: CandidateExtra
  statusRef: RefObject<HTMLDivElement>
  polandBasisOptions: Option[]
  selectTexts: {
    empty: string
    multiNone: string
  }
  onExtraChange: (patch: Partial<CandidateExtra>) => void
  candidateProfile?: CandidateProfile | null
  candidateDataReadOnly?: boolean
}

function CandidateStatusSection({
  extra,
  statusRef,
  polandBasisOptions,
  selectTexts,
  onExtraChange,
  candidateProfile,
  candidateDataReadOnly = false,
}: CandidateStatusSectionProps) {
  const { t } = useI18n()
  const addressCountry = String(extra.address?.country || '').trim().toUpperCase()
  const isInPoland = addressCountry === 'PL' || extra.current_location === 'in_poland'
  const [collapsed, setCollapsed] = useState(() => {
    try { const s = JSON.parse(localStorage.getItem('hf:card-sections') || '{}'); return !!s.status } catch { return false }
  })
  const toggle = useCallback(() => {
    setCollapsed((p) => {
      const next = !p
      try { const s = JSON.parse(localStorage.getItem('hf:card-sections') || '{}'); s.status = next; localStorage.setItem('hf:card-sections', JSON.stringify(s)) } catch {}
      return next
    })
  }, [])

  return (
    <section
      ref={statusRef}
      id="section-status"
      className="group app-surface p-6 scroll-mt-24 transition-all hover:-translate-y-0.5 hover:shadow-xl"
    >
      <button type="button" onClick={toggle} className="flex w-full items-center justify-between gap-3 text-left">
        <div className="flex items-center gap-3">
          <IconIdBadge2 size={22} className="text-slate-600" />
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{t('app.candidate_card.sections.status.title')}</h2>
            <p className="text-sm text-slate-500">{t('app.candidate_card.sections.status.description')}</p>
          </div>
        </div>
        <IconChevronDown size={16} className={`shrink-0 text-slate-400 transition-transform ${collapsed ? '' : 'rotate-180'}`} />
      </button>
      {!collapsed && <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        {(!candidateProfile || isFieldVisible(candidateProfile, 'poland_stay_basis')) && (
          <label className="block">
            <div className="label">
              {getFieldLabel(candidateProfile, 'poland_stay_basis', t('app.candidate_card.fields.poland_basis'))}
              {(isFieldRequired(candidateProfile, 'poland_stay_basis') || isInPoland) && <span className="text-red-600">*</span>}
            </div>
            <select
              className={`input ${isInPoland && !extra.poland_stay_basis ? 'border-amber-500 ring-1 ring-amber-500' : ''}`}
              value={extra.poland_stay_basis || ''}
              disabled={candidateDataReadOnly}
              onChange={(e) => onExtraChange({ poland_stay_basis: e.target.value })}
            >
              {polandBasisOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            {isInPoland && !extra.poland_stay_basis && (
              <p className="mt-1 text-xs text-amber-600">{t('app.candidate_card.validation.poland_basis_required')}</p>
            )}
          </label>
        )}
      </div>}

      {!collapsed && (!candidateProfile || isFieldVisible(candidateProfile, 'has_adr')) && (
        <div className="mt-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">{t('app.candidate_card.sections.status.qualifications')}</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {(!candidateProfile || isFieldVisible(candidateProfile, 'has_adr')) && (
              <label className="block">
                <div className="label">
                  {getFieldLabel(candidateProfile, 'has_adr', t('app.candidate_card.fields.has_adr'))}
                  {isFieldRequired(candidateProfile, 'has_adr') && <span className="text-red-600">*</span>}
                </div>
                <select
                  className="input"
                  disabled={candidateDataReadOnly}
                  value={extra.has_adr === true ? 'yes' : extra.has_adr === false ? 'no' : ''}
                  onChange={(e) => {
                    const value = e.target.value
                    onExtraChange({ has_adr: value === 'yes' ? true : value === 'no' ? false : null })
                  }}
                >
                  <option value="">{t('app.candidate_card.fields.unset')}</option>
                  <option value="yes">{t('common.words.yes')}</option>
                  <option value="no">{t('common.words.no')}</option>
                </select>
              </label>
            )}
          </div>
        </div>
      )}
    </section>
  )
}

export default memo(CandidateStatusSection)
