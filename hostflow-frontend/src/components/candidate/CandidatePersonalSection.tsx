import { memo, useState, useCallback, useEffect } from 'react'
import clsx from 'clsx'
import { IconChevronDown, IconUser } from '@tabler/icons-react'
import type { Candidate, CandidateExtra } from '../../api/types'
import type { RefObject } from 'react'
import type { CandidateProfile } from '../../api/candidate_profiles'
import type { EffectiveCardLayout } from '../../api/fieldRegistry'
import { useI18n } from '../../i18n'
import { Input, SearchableSelect, CheckboxMultiSelect, Checkbox } from './shared/FormComponents'
import { isFieldVisible, isFieldRequired, getFieldLabel } from '../../utils/profileUtils'
import { InlineFieldRow } from '../ui/InlineFieldRow'
import { countryFlag } from '../../modules/candidate-card/utils'

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
  effectiveLayout?: EffectiveCardLayout | null
  candidateDataReadOnly?: boolean
  embedded?: boolean
  /** Citizenship is edited in Operator Facts. This section only shows the stored value. */
  citizenshipReadOnly?: boolean
  /** Split location (country, languages) from the address block. */
  focus?: 'location' | 'address'
  plain?: boolean
  showBirthDate?: boolean
  /** Filled values stay in view until the operator opens that row or address group. */
  rowEdit?: boolean
  canEdit?: boolean
  onRequestUnlock?: () => void
  /** Rows participate in a parent two-column workspace grid. */
  flow?: boolean
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
  effectiveLayout,
  candidateDataReadOnly = false,
  embedded = false,
  citizenshipReadOnly = false,
  focus,
  plain = false,
  showBirthDate = false,
  rowEdit = false,
  canEdit = true,
  onRequestUnlock,
  flow = false,
}: CandidatePersonalSectionProps) {
  const { t } = useI18n()
  const [openField, setOpenField] = useState<string | null>(null)
  const [pendingField, setPendingField] = useState<string | null>(null)
  const fieldVisible = (fieldKey: string) => isFieldVisible(candidateProfile, fieldKey, effectiveLayout)
  const fieldRequired = (fieldKey: string) => isFieldRequired(candidateProfile, fieldKey, effectiveLayout)
  const fieldLabel = (fieldKey: string, defaultLabel: string) =>
    getFieldLabel(candidateProfile, fieldKey, defaultLabel, effectiveLayout)
  const beginRow = (key: string) => {
    if (candidateDataReadOnly) {
      setPendingField(key)
      onRequestUnlock?.()
      return
    }
    setOpenField(key)
  }
  useEffect(() => {
    if (!candidateDataReadOnly && pendingField) {
      setOpenField(pendingField)
      setPendingField(null)
    }
  }, [candidateDataReadOnly, pendingField])
  const countryLabel = (code?: string | null) => countries.find((item) => item.value === code)?.label || code || ''
  const flagged = (code?: string | null) => {
    const label = countryLabel(code)
    const flag = countryFlag(code)
    return flag && label ? `${flag} ${label}` : label
  }
  const formatAddress = (address?: { country?: string | null; city?: string | null; zip?: string | null; street?: string | null; house?: string | null; apt?: string | null } | null) =>
    [flagged(address?.country), address?.city, address?.zip, address?.street, address?.house, address?.apt]
      .map((part) => (typeof part === 'string' ? part.trim() : ''))
      .filter(Boolean)
      .join(', ')
  const languageValue = (candidate.languages || [])
    .map((code) => languages.find((item) => item.value === code)?.label || code)
    .filter(Boolean)
    .join(', ')
  const [collapsed, setCollapsed] = useState(() => {
    if (plain || embedded) return false
    try {
      const s = JSON.parse(localStorage.getItem('hf:card-sections') || '{}')
      return !!s.personal
    } catch { return false }
  })
  const [addressCollapsed, setAddressCollapsed] = useState(() => {
    if (embedded) return false
    try {
      const s = JSON.parse(localStorage.getItem('hf:card-sections') || '{}')
      // Address is heavy; default collapsed unless explicitly opened before.
      return s.personal_address == null ? true : !!s.personal_address
    } catch { return true }
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
  const toggleAddress = useCallback(() => {
    setAddressCollapsed((p) => {
      const next = !p
      try {
        const s = JSON.parse(localStorage.getItem('hf:card-sections') || '{}')
        s.personal_address = next
        localStorage.setItem('hf:card-sections', JSON.stringify(s))
      } catch {}
      return next
    })
  }, [])
  if (rowEdit) {
    const showLocation = focus !== 'address'
    const showAddress = focus !== 'location'
    const regDiff = Boolean((extra as { reg_address_diff?: boolean }).reg_address_diff)
    const residence = formatAddress(extra.address)
    const registered = regDiff
      ? formatAddress(extra.reg_address)
      : t('app.candidate_card.ia.same_as_residence', { defaultValue: 'Same as the residence address' })
    const col = (side: 1 | 2) => (flow ? side : undefined)
    return (
      <section ref={personalRef} id={focus === 'address' ? undefined : 'section-personal'} className={flow ? 'contents' : 'scroll-mt-24'}>
        {showLocation ? (
          <div className={flow ? 'contents' : 'grid grid-cols-1 gap-x-8 md:grid-cols-2'}>
            {(!candidateProfile || fieldVisible('citizenship')) && !citizenshipReadOnly ? (
              <InlineFieldRow
                label={fieldLabel('citizenship', t('app.candidate_card.fields.citizenship'))}
                value={flagged(extra.citizenship)}
                editing={openField === 'citizenship'}
                canEdit={canEdit}
                onEdit={() => beginRow('citizenship')}
                onDone={() => setOpenField(null)}
                column={col(1)}
              >
                <div className="label">{fieldLabel('citizenship', t('app.candidate_card.fields.citizenship'))}</div>
                <SearchableSelect
                  options={countries}
                  value={(extra.citizenship as string) || ''}
                  onChange={(v) => onExtraChange({ citizenship: v })}
                  disabled={candidateDataReadOnly}
                  placeholder={selectTexts.empty}
                  searchPlaceholder={selectTexts.search}
                  noResultsLabel={selectTexts.noResults}
                />
              </InlineFieldRow>
            ) : null}
            {(!candidateProfile || fieldVisible('languages')) ? (
              <InlineFieldRow
                label={fieldLabel('languages', t('app.candidate_card.fields.languages'))}
                value={languageValue}
                editing={openField === 'languages'}
                canEdit={canEdit}
                onEdit={() => beginRow('languages')}
                onDone={() => setOpenField(null)}
                column={col(2)}
                row={flow ? 2 : undefined}
              >
                <div className="label">{fieldLabel('languages', t('app.candidate_card.fields.languages'))}</div>
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
              </InlineFieldRow>
            ) : null}
            {(!candidateProfile || fieldVisible('country_code')) ? (
              <InlineFieldRow
                label={fieldLabel('country_code', t('app.candidate_card.fields.country_code'))}
                value={flagged(candidate.country_code)}
                editing={openField === 'country_code'}
                canEdit={canEdit}
                onEdit={() => beginRow('country_code')}
                onDone={() => setOpenField(null)}
                column={col(2)}
                row={flow ? 3 : undefined}
              >
                <div className="label">{fieldLabel('country_code', t('app.candidate_card.fields.country_code'))}</div>
                <SearchableSelect
                  options={countries}
                  value={(candidate.country_code as string) || ''}
                  onChange={(v) => onModelChange((m) => ({ ...m, country_code: v || null }))}
                  disabled={candidateDataReadOnly}
                  placeholder={selectTexts.empty}
                  searchPlaceholder={selectTexts.search}
                  noResultsLabel={selectTexts.noResults}
                />
                {!candidate.country_code && extra.phone_country ? (
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
                ) : null}
              </InlineFieldRow>
            ) : null}
          </div>
        ) : null}
        {showAddress ? (
          <div className={flow ? 'contents' : 'grid grid-cols-1 gap-x-8 md:grid-cols-2'}>
            <InlineFieldRow
              label={t('app.candidate_card.sections.personal.address_current')}
              value={residence}
              editing={openField === 'address'}
              canEdit={canEdit}
              onEdit={() => beginRow('address')}
              onDone={() => setOpenField(null)}
              variant="summary"
              emptyLabel={t('app.candidate_card.ia.not_filled', { defaultValue: 'Not filled' })}
              wide={!flow}
            >
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
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
                <Input label={t('app.candidate_card.fields.address.city')} value={extra.address?.city || ''} onChange={(e) => onAddressFieldChange('address', 'city', e.target.value)} readOnly={candidateDataReadOnly} />
                <Input label={t('app.candidate_card.fields.address.zip')} value={extra.address?.zip || ''} onChange={(e) => onAddressFieldChange('address', 'zip', e.target.value)} readOnly={candidateDataReadOnly} />
                <Input label={t('app.candidate_card.fields.address.street')} containerClassName="md:col-span-2" value={extra.address?.street || ''} onChange={(e) => onAddressFieldChange('address', 'street', e.target.value)} readOnly={candidateDataReadOnly} />
                <Input label={t('app.candidate_card.fields.address.house')} value={extra.address?.house || ''} onChange={(e) => onAddressFieldChange('address', 'house', e.target.value)} readOnly={candidateDataReadOnly} />
                <Input label={t('app.candidate_card.fields.address.apt')} value={extra.address?.apt || ''} onChange={(e) => onAddressFieldChange('address', 'apt', e.target.value)} readOnly={candidateDataReadOnly} />
              </div>
            </InlineFieldRow>
            <InlineFieldRow
              label={t('app.candidate_card.sections.personal.address_registered')}
              value={registered}
              editing={openField === 'reg_address'}
              canEdit={canEdit}
              onEdit={() => beginRow('reg_address')}
              onDone={() => setOpenField(null)}
              variant="summary"
              emptyLabel={t('app.candidate_card.ia.not_filled', { defaultValue: 'Not filled' })}
              wide={!flow}
            >
              <Checkbox
                label={t('app.candidate_card.fields.address.diff')}
                checked={regDiff}
                onChange={candidateDataReadOnly ? undefined : (v) => onExtraChange({ reg_address_diff: v })}
              />
              {regDiff ? (
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
                  <Input label={t('app.candidate_card.fields.address.city')} value={extra.reg_address?.city || ''} onChange={(e) => onAddressFieldChange('reg_address', 'city', e.target.value)} readOnly={candidateDataReadOnly} />
                  <Input label={t('app.candidate_card.fields.address.zip')} value={extra.reg_address?.zip || ''} onChange={(e) => onAddressFieldChange('reg_address', 'zip', e.target.value)} readOnly={candidateDataReadOnly} />
                  <Input label={t('app.candidate_card.fields.address.street')} containerClassName="md:col-span-2" value={extra.reg_address?.street || ''} onChange={(e) => onAddressFieldChange('reg_address', 'street', e.target.value)} readOnly={candidateDataReadOnly} />
                  <Input label={t('app.candidate_card.fields.address.house')} value={extra.reg_address?.house || ''} onChange={(e) => onAddressFieldChange('reg_address', 'house', e.target.value)} readOnly={candidateDataReadOnly} />
                  <Input label={t('app.candidate_card.fields.address.apt')} value={extra.reg_address?.apt || ''} onChange={(e) => onAddressFieldChange('reg_address', 'apt', e.target.value)} readOnly={candidateDataReadOnly} />
                </div>
              ) : null}
            </InlineFieldRow>
          </div>
        ) : null}
      </section>
    )
  }

  return (
    <section
      ref={personalRef}
      id={focus === 'address' ? undefined : 'section-personal'}
      className={clsx(
        'scroll-mt-24',
        plain
          ? undefined
          : embedded
            ? 'rounded-2xl border border-slate-200 bg-white p-4'
            : 'group app-surface p-4 transition-shadow hover:shadow-xl',
      )}
    >
      {plain ? null : (
      <button
        type="button"
        onClick={embedded ? undefined : toggle}
        className={clsx('flex w-full items-center justify-between gap-3 text-left', embedded && 'cursor-default')}
      >
        <div className="flex items-center gap-2">
          <IconUser size={18} className="text-slate-600" />
          <div className="text-sm font-semibold text-slate-900">{t('app.candidate_card.sections.personal.title')}</div>
        </div>
        {!embedded ? (
          <IconChevronDown size={16} className={`shrink-0 text-slate-400 transition-transform ${collapsed ? '' : 'rotate-180'}`} />
        ) : null}
      </button>
      )}

      {!collapsed && focus !== 'address' && <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {(!candidateProfile || fieldVisible('citizenship')) && !citizenshipReadOnly && (
          <label className="block">
            <div className="label">{fieldLabel('citizenship', t('app.candidate_card.fields.citizenship'))} {fieldRequired('citizenship') && <span className="text-red-600">*</span>}</div>
          {citizenshipReadOnly ? (
            <p className="mt-1 text-sm text-slate-800" data-testid="candidate-citizenship-readonly">
              {String(extra.citizenship || '').trim() || '—'}
            </p>
          ) : (
          <SearchableSelect
            options={countries}
            value={String(candidate.personal_data?.citizenship || extra.citizenship || '')}
            onChange={(v) => {
              onModelChange((current) => ({
                ...current,
                personal_data: { ...(current.personal_data || {}), citizenship: v || null },
              }))
              onExtraChange({ citizenship: v })
            }}
            disabled={candidateDataReadOnly}
            placeholder={selectTexts.empty}
            searchPlaceholder={selectTexts.search}
            noResultsLabel={selectTexts.noResults}
          />
          )}
        </label>
        )}
        {(!candidateProfile || fieldVisible('country_code')) && (
          <label className="block">
            <div className="label">{fieldLabel('country_code', t('app.candidate_card.fields.country_code'))} {fieldRequired('country_code') && <span className="text-red-600">*</span>}</div>
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
        {(!candidateProfile || fieldVisible('languages')) && (
          <div className="lg:col-span-2">
            <div className="label">{fieldLabel('languages', t('app.candidate_card.fields.languages'))} {fieldRequired('languages') && <span className="text-red-600">*</span>}</div>
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

      {!collapsed && focus !== 'location' && (
        <div className="mt-4">
          {showBirthDate ? (
            <div className="mb-4 max-w-xs">
              <Input
                label={fieldLabel('birth_date', t('app.candidate_card.fields.birth_date'))}
                type="date"
                value={(extra.birth_date as string) || ''}
                onChange={(e) => onExtraChange({ birth_date: e.target.value })}
                readOnly={candidateDataReadOnly}
                required={fieldRequired('birth_date')}
              />
            </div>
          ) : null}
          {!embedded && (
            <button
              type="button"
              onClick={toggleAddress}
              className="btn-secondary btn-sm"
              title={t('app.candidate_card.sections.personal.address_current')}
            >
              {addressCollapsed ? t('common.actions.expand') : t('common.actions.collapse')} ·{' '}
              {t('app.candidate_card.sections.personal.address_current')}
            </button>
          )}

          {(embedded || !addressCollapsed) && (
            <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
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
            </div>
          )}
        </div>
      )}

    </section>
  )
}

export default memo(CandidatePersonalSection)
