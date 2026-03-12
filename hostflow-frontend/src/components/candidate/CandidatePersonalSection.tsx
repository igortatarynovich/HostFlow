import { memo, useRef, useState, useCallback } from 'react'
import { IconChevronDown, IconUser } from '@tabler/icons-react'
import type { Candidate, CandidateExtra } from '../../api/types'
import type { RefObject } from 'react'
import type { CandidateProfile } from '../../api/candidate_profiles'
import { useI18n } from '../../i18n'
import { Input, SearchableSelect, CheckboxMultiSelect, Checkbox } from './shared/FormComponents'
import { isFieldVisible, isFieldRequired, getFieldLabel } from '../../utils/profileUtils'

type Option = { value: string; label: string; extra?: any }

interface CandidatePersonalSectionProps {
  candidate: Candidate
  extra: CandidateExtra
  personalRef: RefObject<HTMLDivElement>
  countries: Option[]
  languages: Option[]
  selectTexts: {
    empty: string
    search: string
    noResults: string
    multiNone: string
    multiSelected: (count: number) => string
  }
  onModelChange: (updater: (prev: Candidate) => Candidate) => void
  onExtraChange: (patch: Partial<CandidateExtra>) => void
  onAddressFieldChange: (which: 'address' | 'reg_address', key: keyof NonNullable<CandidateExtra['address']>, value: string) => void
  candidateProfile?: CandidateProfile | null
  candidateDataReadOnly?: boolean
}

function CandidatePersonalSection({
  candidate,
  extra,
  personalRef,
  countries,
  languages,
  selectTexts,
  onModelChange,
  onExtraChange,
  onAddressFieldChange,
  candidateProfile,
  candidateDataReadOnly = false,
}: CandidatePersonalSectionProps) {
  const { t } = useI18n()
  const [collapsed, setCollapsed] = useState(() => {
    try {
      const s = JSON.parse(localStorage.getItem('hf:card-sections') || '{}')
      return !!s.personal
    } catch { return false }
  })
  const toggle = useCallback(() => {
    setCollapsed((p) => {
      const next = !p
      try {
        const s = JSON.parse(localStorage.getItem('hf:card-sections') || '{}')
        s.personal = next
        localStorage.setItem('hf:card-sections', JSON.stringify(s))
      } catch {}
      return next
    })
  }, [])

  return (
    <section
      ref={personalRef}
      id="section-personal"
      className="group app-surface p-6 scroll-mt-24 transition-all hover:-translate-y-0.5 hover:shadow-xl"
    >
      <button type="button" onClick={toggle} className="flex w-full items-center justify-between gap-3 text-left">
        <div className="flex items-center gap-3">
          <IconUser size={22} className="text-slate-600" />
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{t('app.candidate_card.sections.personal.title')}</h2>
            <p className="text-sm text-slate-500">{t('app.candidate_card.sections.personal.description')}</p>
          </div>
        </div>
        <IconChevronDown size={16} className={`shrink-0 text-slate-400 transition-transform ${collapsed ? '' : 'rotate-180'}`} />
      </button>

      {!collapsed && <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {(!candidateProfile || isFieldVisible(candidateProfile, 'birth_date')) && (
          <div>
            <Input
              label={getFieldLabel(candidateProfile, 'birth_date', t('app.candidate_card.fields.birth_date'))}
              type="date"
              value={(extra.birth_date as any) || ''}
              onChange={(e) => onExtraChange({ birth_date: e.target.value })}
              readOnly={candidateDataReadOnly}
              required={isFieldRequired(candidateProfile, 'birth_date')}
            />
            {(extra.birth_date as string) && (() => {
              const bd = (extra.birth_date as string).slice(0, 10)
              const d = /^\d{4}-\d{2}-\d{2}$/.test(bd) ? new Date(bd) : null
              const age = d && !isNaN(d.getTime())
                ? Math.floor((Date.now() - d.getTime()) / (365.25 * 24 * 60 * 60 * 1000))
                : null
              return age != null && age >= 0 && age <= 120 ? (
                <p className="mt-1 text-xs text-slate-500">{t('app.candidate_card.fields.age_hint', { values: { age } })}</p>
              ) : null
            })()}
          </div>
        )}
        {(!candidateProfile || isFieldVisible(candidateProfile, 'citizenship')) && (
          <label className="block">
            <div className="label">{getFieldLabel(candidateProfile, 'citizenship', t('app.candidate_card.fields.citizenship'))} {isFieldRequired(candidateProfile, 'citizenship') && <span className="text-red-600">*</span>}</div>
          <SearchableSelect
            options={countries}
            value={(extra.citizenship as any) || ''}
            onChange={(v) => onExtraChange({ citizenship: v })}
            disabled={candidateDataReadOnly}
            placeholder={selectTexts.empty}
            searchPlaceholder={selectTexts.search}
            noResultsLabel={selectTexts.noResults}
          />
        </label>
        )}
        {(!candidateProfile || isFieldVisible(candidateProfile, 'country_code')) && (
          <label className="block">
            <div className="label">{getFieldLabel(candidateProfile, 'country_code', t('app.candidate_card.fields.country_code'))} {isFieldRequired(candidateProfile, 'country_code') && <span className="text-red-600">*</span>}</div>
          <SearchableSelect
            options={countries}
            value={(candidate.country_code as any) || ''}
            onChange={(v) => onModelChange((m) => ({ ...m, country_code: v || null }))}
            disabled={candidateDataReadOnly}
            placeholder={selectTexts.empty}
            searchPlaceholder={selectTexts.search}
            noResultsLabel={selectTexts.noResults}
          />
          <p className="mt-1 text-xs text-slate-500">{t('app.candidate_card.fields.country_code_hint')}</p>
          {!candidate.country_code && extra.phone_country && (
            <button
              type="button"
              className="mt-1 text-xs text-brand-600 hover:underline"
              disabled={candidateDataReadOnly}
              onClick={() => {
                onModelChange((m) => ({ ...m, country_code: extra.phone_country }))
                onExtraChange({ country_code: extra.phone_country })
              }}
            >
              {t('app.candidate_card.fields.fill_from_phone')}
            </button>
          )}
        </label>
        )}
        {(!candidateProfile || isFieldVisible(candidateProfile, 'languages')) && (
          <div className="lg:col-span-2">
            <div className="label">{getFieldLabel(candidateProfile, 'languages', t('app.candidate_card.fields.languages'))} {isFieldRequired(candidateProfile, 'languages') && <span className="text-red-600">*</span>}</div>
          <CheckboxMultiSelect
            options={languages}
            values={candidate.languages || []}
            onChange={(vals) => onModelChange((m) => ({ ...m, languages: vals }))}
            disabled={candidateDataReadOnly}
            placeholder={selectTexts.multiNone}
            searchPlaceholder={selectTexts.search}
            noResultsLabel={selectTexts.noResults}
            multiSelectedLabel={selectTexts.multiSelected}
          />
          </div>
        )}
      </div>}

      {!collapsed && <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-dashed border-slate-300 bg-white/60 p-4">
          <div className="font-semibold text-slate-800">{t('app.candidate_card.sections.personal.address_current')}</div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <label className="block md:col-span-2">
              <div className="label">{t('app.candidate_card.fields.address.country')}</div>
              <SearchableSelect
                options={countries}
                value={extra.address?.country || ''}
                onChange={(v) => onAddressFieldChange('address', 'country', v)}
                disabled={candidateDataReadOnly}
                placeholder={selectTexts.empty}
                searchPlaceholder={selectTexts.search}
                noResultsLabel={selectTexts.noResults}
              />
            </label>
            <Input
              label={t('app.candidate_card.fields.address.city')}
              value={extra.address?.city || ''}
              onChange={(e) => onAddressFieldChange('address', 'city', e.target.value)}
              readOnly={candidateDataReadOnly}
            />
            <Input
              label={t('app.candidate_card.fields.address.zip')}
              value={extra.address?.zip || ''}
              onChange={(e) => onAddressFieldChange('address', 'zip', e.target.value)}
              readOnly={candidateDataReadOnly}
            />
            <Input
              label={t('app.candidate_card.fields.address.street')}
              containerClassName="md:col-span-2"
              value={extra.address?.street || ''}
              onChange={(e) => onAddressFieldChange('address', 'street', e.target.value)}
              readOnly={candidateDataReadOnly}
            />
            <Input
              label={t('app.candidate_card.fields.address.house')}
              value={extra.address?.house || ''}
              onChange={(e) => onAddressFieldChange('address', 'house', e.target.value)}
              readOnly={candidateDataReadOnly}
            />
            <Input
              label={t('app.candidate_card.fields.address.apt')}
              value={extra.address?.apt || ''}
              onChange={(e) => onAddressFieldChange('address', 'apt', e.target.value)}
              readOnly={candidateDataReadOnly}
            />
          </div>

          <div className="mt-3 rounded-lg bg-slate-50 px-3 py-2">
            <Checkbox
              label={t('app.candidate_card.fields.address.diff')}
              checked={!!(extra as any).reg_address_diff}
              onChange={candidateDataReadOnly ? undefined : (v) => onExtraChange({ reg_address_diff: v })}
            />
          </div>
        </div>

        {(extra as any).reg_address_diff && (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white/60 p-4">
            <div className="font-semibold text-slate-800">{t('app.candidate_card.sections.personal.address_registered')}</div>
            <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
              <label className="block md:col-span-2">
                <div className="label">{t('app.candidate_card.fields.address.country')}</div>
                <SearchableSelect
                  options={countries}
                  value={extra.reg_address?.country || ''}
                  onChange={(v) => onAddressFieldChange('reg_address', 'country', v)}
                  disabled={candidateDataReadOnly}
                  placeholder={selectTexts.empty}
                  searchPlaceholder={selectTexts.search}
                  noResultsLabel={selectTexts.noResults}
                />
              </label>
              <Input
                label={t('app.candidate_card.fields.address.city')}
                value={extra.reg_address?.city || ''}
                onChange={(e) => onAddressFieldChange('reg_address', 'city', e.target.value)}
                readOnly={candidateDataReadOnly}
              />
              <Input
                label={t('app.candidate_card.fields.address.zip')}
                value={extra.reg_address?.zip || ''}
                onChange={(e) => onAddressFieldChange('reg_address', 'zip', e.target.value)}
                readOnly={candidateDataReadOnly}
              />
              <Input
                label={t('app.candidate_card.fields.address.street')}
                containerClassName="md:col-span-2"
                value={extra.reg_address?.street || ''}
                onChange={(e) => onAddressFieldChange('reg_address', 'street', e.target.value)}
                readOnly={candidateDataReadOnly}
              />
              <Input
                label={t('app.candidate_card.fields.address.house')}
                value={extra.reg_address?.house || ''}
                onChange={(e) => onAddressFieldChange('reg_address', 'house', e.target.value)}
                readOnly={candidateDataReadOnly}
              />
              <Input
                label={t('app.candidate_card.fields.address.apt')}
                value={extra.reg_address?.apt || ''}
                onChange={(e) => onAddressFieldChange('reg_address', 'apt', e.target.value)}
                readOnly={candidateDataReadOnly}
              />
            </div>
          </div>
        )}
      </div>}

    </section>
  )
}

export default memo(CandidatePersonalSection)
