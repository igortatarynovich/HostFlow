import { memo, useState, useEffect } from 'react'
import clsx from 'clsx'
import { IconUserCircle } from '@tabler/icons-react'
import type { Candidate, CandidateExtra } from '../../api/types'
import type { RefObject } from 'react'
import type { CandidateProfile } from '../../api/candidate_profiles'
import type { EffectiveCardLayout } from '../../api/fieldRegistry'
import { useI18n } from '../../i18n'
import { CandidateProcessControls } from './card/CandidateProcessControls'
import { Input, SearchableSelect } from './shared/FormComponents'
import { translateStageLabel } from '../../utils/stageLabels'
import { validateEmail, validatePhone } from '../../utils/validation'
import { isFieldVisible, isFieldRequired, getFieldLabel } from '../../utils/profileUtils'
import { hasCyrillic } from '../../utils/transliterate'

type Option = { value: string; label: string; extra?: any }
type PreferredContact = 'viber' | 'whatsapp' | 'telegram' | 'phone' | ''

interface CandidateBasicSectionProps {
  candidate: Candidate
  extra: CandidateExtra
  isNew: boolean
  locale: string
  basicRef: RefObject<HTMLDivElement>
  stageOptions: string[]
  profileStageCodes?: string[]
  meta?: {
    reason_choices?: Record<string, { code: string; label: string }[]>
    labels?: Record<string, string>
  }
  dialCodes: Option[]
  managers: Option[]
  preferredContactOptions: Option[]
  selectTexts: {
    empty: string
    search: string
    noResults: string
  }
  createdAtDisplay: string
  isMetaLead: boolean
  onModelChange: (updater: (prev: Candidate) => Candidate) => void
  onExtraChange: (patch: Partial<CandidateExtra>) => void
  onPhoneInputChange: (value: string) => void
  onFirstContactToggle?: (checked: boolean) => void
  onGenerateShortId: () => Promise<void>
  candidateProfile?: CandidateProfile | null
  effectiveLayout?: EffectiveCardLayout | null
  stageLabelIntl?: (code: string) => string
  candidateDataReadOnly?: boolean
  /** When false, stage dropdown and status_reason cannot be changed (handoff / HR lock). */
  canEdit?: boolean
  /** Allows rejected/declined while general edit is locked (pending handoff). */
  canCloseRecruitment?: boolean
  /** When set, stage and status_reason are persisted immediately (no Save required). */
  onStageChangePersist?: (stage: string, statusReason: string[]) => void | Promise<void>
  embedded?: boolean
  /** Stage, manager and tags live in the overview process widget. */
  hideProcessControls?: boolean
  omitBirthDate?: boolean
  /** Drop the section frame when the parent accordion already provides it. */
  plain?: boolean
}

function CandidateBasicSection({
  candidate,
  extra,
  isNew,
  locale,
  basicRef,
  stageOptions,
  profileStageCodes,
  meta,
  dialCodes,
  managers,
  preferredContactOptions,
  selectTexts,
  createdAtDisplay,
  isMetaLead,
  onModelChange,
  onExtraChange,
  onPhoneInputChange,
  onGenerateShortId,
  candidateProfile,
  effectiveLayout,
  stageLabelIntl: stageLabelIntlProp,
  candidateDataReadOnly = false,
  canEdit = true,
  canCloseRecruitment = true,
  onStageChangePersist,
  embedded = false,
  hideProcessControls = false,
  omitBirthDate = false,
  plain = false,
}: CandidateBasicSectionProps) {
  const { t } = useI18n()
  const [emailError, setEmailError] = useState<string | null>(null)
  const [phoneError, setPhoneError] = useState<string | null>(null)
  const [emailTouched, setEmailTouched] = useState(false)
  const [phoneTouched, setPhoneTouched] = useState(false)

  const stageLabelIntl = stageLabelIntlProp ?? ((code: string) => {
    const fallback = meta?.labels?.[code] || code
    return translateStageLabel(t, code, fallback)
  })
  const fieldVisible = (fieldKey: string) => isFieldVisible(candidateProfile, fieldKey, effectiveLayout)
  const fieldRequired = (fieldKey: string) => isFieldRequired(candidateProfile, fieldKey, effectiveLayout)
  const fieldLabel = (fieldKey: string, defaultLabel: string) =>
    getFieldLabel(candidateProfile, fieldKey, defaultLabel, effectiveLayout)
  const translateValidationError = (error: string) => {
    if (error === 'Invalid email format') {
      return t('app.candidate_card.validation.email_invalid_format')
    }
    if (error === 'Phone number should contain only digits') {
      return t('app.candidate_card.validation.phone_only_digits')
    }
    if (error === 'Phone number is too short') {
      return t('app.candidate_card.validation.phone_too_short')
    }
    if (error === 'Phone number is too long') {
      return t('app.candidate_card.validation.phone_too_long')
    }
    return error
  }

  // Validate email in real-time
  useEffect(() => {
    if (emailTouched || candidate.email) {
      const error = validateEmail(candidate.email)
      setEmailError(error)
    }
  }, [candidate.email, emailTouched])

  // Validate phone in real-time
  useEffect(() => {
    if (phoneTouched || candidate.phone) {
      const error = validatePhone(candidate.phone)
      setPhoneError(error)
    }
  }, [candidate.phone, phoneTouched])

  const Container: any = embedded ? 'div' : 'section'

  return (
    <Container
      ref={basicRef}
      id="section-basic"
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
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <IconUserCircle size={18} className="text-slate-600" />
          <div className="text-sm font-semibold text-slate-900">{t('app.candidate_card.sections.basic.title')}</div>
        </div>
      </div>
      )}

      <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="space-y-4">
          {(!candidateProfile || fieldVisible('first_name')) && (
            <Input
              label={fieldLabel('first_name', t('app.candidate_card.fields.first_name'))}
              value={candidate.first_name}
              onChange={(e) => onModelChange((m) => ({ ...m, first_name: e.target.value }))}
              readOnly={candidateDataReadOnly}
              required={fieldRequired('first_name')}
            />
          )}
          {(!candidateProfile || fieldVisible('last_name')) && (
            <Input
              label={fieldLabel('last_name', t('app.candidate_card.fields.last_name'))}
              value={candidate.last_name}
              onChange={(e) => onModelChange((m) => ({ ...m, last_name: e.target.value }))}
              readOnly={candidateDataReadOnly}
              required={fieldRequired('last_name')}
            />
          )}
          {(!candidateProfile || fieldVisible('birth_date')) && !omitBirthDate && (
            <Input
              label={fieldLabel('birth_date', t('app.candidate_card.fields.birth_date'))}
              type="date"
              value={(extra.birth_date as string) || ''}
              onChange={(e) => onExtraChange({ birth_date: e.target.value })}
              readOnly={candidateDataReadOnly}
              required={fieldRequired('birth_date')}
            />
          )}
          {(hasCyrillic(candidate.first_name) || hasCyrillic(candidate.last_name)) && (
            <p className="text-xs text-amber-700">
              {t('app.candidate_card.hint.cyrillic_translit')}
            </p>
          )}
          {(!candidateProfile || fieldVisible('email')) && (
            <div>
              <Input
                label={fieldLabel('email', t('app.candidate_card.fields.email'))}
                type="email"
                value={candidate.email || ''}
                onChange={(e) => {
                  onModelChange((m) => ({ ...m, email: e.target.value }))
                  setEmailTouched(true)
                }}
                onBlur={() => setEmailTouched(true)}
                className={emailError ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
                readOnly={candidateDataReadOnly}
                required={fieldRequired('email')}
              />
              {emailError && emailTouched && (
                <p className="mt-1 text-xs text-red-600">{translateValidationError(emailError)}</p>
              )}
            </div>
          )}

          {(!candidateProfile || fieldVisible('phone')) && (
            <div>
              <div className="label">{fieldLabel('phone', t('app.candidate_card.fields.phone'))} {fieldRequired('phone') && <span className="text-red-600">*</span>}</div>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start">
                <div className="sm:w-64">
                  <SearchableSelect
                    options={dialCodes}
                    value={(extra as any).phone_country || ''}
                    onChange={(cc) => {
                      const prefix = dialCodes.find((x) => x.value === cc)?.extra?.prefix || ''
                      onExtraChange({ phone_country: cc, phone_prefix: prefix })
                    }}
                    disabled={candidateDataReadOnly}
                    placeholder={selectTexts.empty}
                    searchPlaceholder={t('app.candidate_card.select.search_country')}
                    noResultsLabel={selectTexts.noResults}
                    className="w-full"
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <Input
                    placeholder={t('app.candidate_card.placeholders.phone_number')}
                    value={candidate.phone || ''}
                    onChange={(e) => {
                      onPhoneInputChange(e.target.value)
                      setPhoneTouched(true)
                    }}
                    onBlur={() => setPhoneTouched(true)}
                    containerClassName="min-w-0"
                    className={clsx('w-full', phoneError ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : '')}
                    readOnly={candidateDataReadOnly}
                  />
                  {phoneError && phoneTouched && (
                    <p className="mt-1 text-xs text-red-600">{translateValidationError(phoneError)}</p>
                  )}
                </div>
              </div>
          </div>
          )}

          {(!candidateProfile || fieldVisible('preferred_contact')) && (
            <label className="block">
              <div className="label">{fieldLabel('preferred_contact', t('app.candidate_card.fields.preferred_contact'))} {fieldRequired('preferred_contact') && <span className="text-red-600">*</span>}</div>
            <select
              className="input"
              value={(extra.preferred_contact as PreferredContact) || ''}
              disabled={candidateDataReadOnly}
              onChange={(e) => onExtraChange({ preferred_contact: e.target.value as PreferredContact })}
            >
              {preferredContactOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          )}
          <Input
            label={t('app.candidate_card.fields.phone_additional', { defaultValue: 'Dodatkowy telefon' })}
            value={(extra as { phone_additional?: string | null }).phone_additional || ''}
            onChange={(e) => onExtraChange({ phone_additional: e.target.value } as Partial<CandidateExtra>)}
            readOnly={candidateDataReadOnly}
          />
        </div>

        <div className="space-y-4">
          <div>
            <div className="label flex items-center justify-between">
              <span>{t('app.candidate_card.fields.short_id')}</span>
              {!isNew && !candidate.short_id && (
                <button type="button" className="btn-secondary btn-xs" onClick={onGenerateShortId}>
                  {t('app.candidate_card.actions.generate_short_id')}
                </button>
              )}
            </div>
            <Input
              value={candidate.short_id || ''}
              readOnly
              placeholder="—"
              hint={t('app.candidate_card.fields.short_id_hint')}
            />
          </div>

          {hideProcessControls ? null : (
          <CandidateProcessControls
            candidate={candidate}
            stageOptions={stageOptions}
            profileStageCodes={profileStageCodes}
            meta={meta}
            managers={managers}
            selectTexts={selectTexts}
            stageLabelIntl={stageLabelIntl}
            canEdit={canEdit}
            canCloseRecruitment={canCloseRecruitment}
            candidateProfile={candidateProfile}
            onModelChange={onModelChange}
            onStageChangePersist={onStageChangePersist}
          />
          )}
          <Input
            label={t('app.candidate_card.fields.created_at')}
            value={createdAtDisplay}
            readOnly
            placeholder="—"
            hint={t('app.candidate_card.fields.created_at_hint')}
          />

          {isMetaLead && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
              {t('app.candidate_card.messages.meta_lead')}
            </div>
          )}
        </div>
      </div>
    </Container>
  )
}

export default memo(CandidateBasicSection)
