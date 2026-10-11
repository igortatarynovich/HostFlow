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
import { InlineFieldRow } from '../ui/InlineFieldRow'
import { translateStageLabel } from '../../utils/stageLabels'
import { validateEmail, validatePhone } from '../../utils/validation'
import { isFieldVisible, isFieldRequired, getFieldLabel } from '../../utils/profileUtils'
import { hasCyrillic } from '../../utils/transliterate'
import { formatDateSafe } from '../../modules/candidates/candidateUtils'

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
  /** Each personal field opens on its own. Override reason stays on the parent save gate. */
  rowEdit?: boolean
  onRequestUnlock?: () => void
  /** Split identity from contact so each section can sit in its own card. */
  part?: 'identity' | 'contact'
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
  rowEdit = false,
  onRequestUnlock,
  part,
}: CandidateBasicSectionProps) {
  const { t } = useI18n()
  const [openField, setOpenField] = useState<string | null>(null)
  const [pendingField, setPendingField] = useState<string | null>(null)
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
  const rowLocked = (key: string) => (rowEdit ? openField !== key || candidateDataReadOnly : candidateDataReadOnly)
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
  const preferredLabel =
    preferredContactOptions.find((opt) => opt.value === (extra.preferred_contact || ''))?.label
    || (extra.preferred_contact as string)
    || ''
  const birthValue = extra.birth_date ? formatDateSafe(String(extra.birth_date), locale) : ''

  if (rowEdit) {
    const showIdentity = part !== 'contact'
    const showContact = part !== 'identity'
    return (
      <Container ref={part === 'contact' ? undefined : basicRef} id={part === 'contact' ? undefined : 'section-basic'} className="scroll-mt-24">
        <div className="grid grid-cols-1 gap-x-8 md:grid-cols-2">
          {showIdentity && (!candidateProfile || fieldVisible('first_name')) ? (
            <InlineFieldRow
              label={fieldLabel('first_name', t('app.candidate_card.fields.first_name'))}
              value={candidate.first_name || ''}
              editing={openField === 'first_name'}
              canEdit={canEdit}
              onEdit={() => beginRow('first_name')}
              onDone={() => setOpenField(null)}
            >
              <Input
                label={fieldLabel('first_name', t('app.candidate_card.fields.first_name'))}
                value={candidate.first_name}
                onChange={(e) => onModelChange((m) => ({ ...m, first_name: e.target.value }))}
                readOnly={rowLocked('first_name')}
                required={fieldRequired('first_name')}
              />
            </InlineFieldRow>
          ) : null}
          {showIdentity && (!candidateProfile || fieldVisible('last_name')) ? (
            <InlineFieldRow
              label={fieldLabel('last_name', t('app.candidate_card.fields.last_name'))}
              value={candidate.last_name || ''}
              editing={openField === 'last_name'}
              canEdit={canEdit}
              onEdit={() => beginRow('last_name')}
              onDone={() => setOpenField(null)}
            >
              <Input
                label={fieldLabel('last_name', t('app.candidate_card.fields.last_name'))}
                value={candidate.last_name}
                onChange={(e) => onModelChange((m) => ({ ...m, last_name: e.target.value }))}
                readOnly={rowLocked('last_name')}
                required={fieldRequired('last_name')}
              />
            </InlineFieldRow>
          ) : null}
          {showIdentity && (!candidateProfile || fieldVisible('birth_date')) && !omitBirthDate ? (
            <InlineFieldRow
              label={fieldLabel('birth_date', t('app.candidate_card.fields.birth_date'))}
              value={birthValue}
              editing={openField === 'birth_date'}
              canEdit={canEdit}
              onEdit={() => beginRow('birth_date')}
              onDone={() => setOpenField(null)}
            >
              <Input
                label={fieldLabel('birth_date', t('app.candidate_card.fields.birth_date'))}
                type="date"
                value={(extra.birth_date as string) || ''}
                onChange={(e) => onExtraChange({ birth_date: e.target.value })}
                readOnly={rowLocked('birth_date')}
                required={fieldRequired('birth_date')}
              />
            </InlineFieldRow>
          ) : null}
          {showContact && (!candidateProfile || fieldVisible('phone')) ? (
            <InlineFieldRow
              label={fieldLabel('phone', t('app.candidate_card.fields.phone'))}
              value={candidate.phone || ''}
              editing={openField === 'phone'}
              canEdit={canEdit}
              onEdit={() => beginRow('phone')}
              onDone={() => setOpenField(null)}
              wide
            >
              <div className="label">{fieldLabel('phone', t('app.candidate_card.fields.phone'))}</div>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start">
                <div className="sm:w-56">
                  <SearchableSelect
                    options={dialCodes}
                    value={(extra as { phone_country?: string }).phone_country || ''}
                    onChange={(cc) => {
                      const prefix = dialCodes.find((x) => x.value === cc)?.extra?.prefix || ''
                      onExtraChange({ phone_country: cc, phone_prefix: prefix })
                    }}
                    disabled={rowLocked('phone')}
                    placeholder={selectTexts.empty}
                    searchPlaceholder={t('app.candidate_card.select.search_country')}
                    noResultsLabel={selectTexts.noResults}
                    className="w-full"
                  />
                </div>
                <div className="min-w-0 flex-1">
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
                    readOnly={rowLocked('phone')}
                  />
                  {phoneError && phoneTouched ? (
                    <p className="mt-1 text-xs text-red-600">{translateValidationError(phoneError)}</p>
                  ) : null}
                </div>
              </div>
            </InlineFieldRow>
          ) : null}
          {showContact ? (
            <InlineFieldRow
              label={t('app.candidate_card.fields.phone_additional', { defaultValue: 'Additional phone' })}
              value={(extra as { phone_additional?: string | null }).phone_additional || ''}
              editing={openField === 'phone_additional'}
              canEdit={canEdit}
              onEdit={() => beginRow('phone_additional')}
              onDone={() => setOpenField(null)}
            >
              <Input
                label={t('app.candidate_card.fields.phone_additional', { defaultValue: 'Additional phone' })}
                value={(extra as { phone_additional?: string | null }).phone_additional || ''}
                onChange={(e) => onExtraChange({ phone_additional: e.target.value } as Partial<CandidateExtra>)}
                readOnly={rowLocked('phone_additional')}
              />
            </InlineFieldRow>
          ) : null}
          {showContact && (!candidateProfile || fieldVisible('email')) ? (
            <InlineFieldRow
              label={fieldLabel('email', t('app.candidate_card.fields.email'))}
              value={candidate.email || ''}
              editing={openField === 'email'}
              canEdit={canEdit}
              onEdit={() => beginRow('email')}
              onDone={() => setOpenField(null)}
            >
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
                readOnly={rowLocked('email')}
                required={fieldRequired('email')}
              />
              {emailError && emailTouched ? (
                <p className="mt-1 text-xs text-red-600">{translateValidationError(emailError)}</p>
              ) : null}
            </InlineFieldRow>
          ) : null}
          {showContact && (!candidateProfile || fieldVisible('preferred_contact')) ? (
            <InlineFieldRow
              label={fieldLabel('preferred_contact', t('app.candidate_card.fields.preferred_contact'))}
              value={preferredLabel}
              editing={openField === 'preferred_contact'}
              canEdit={canEdit}
              onEdit={() => beginRow('preferred_contact')}
              onDone={() => setOpenField(null)}
            >
              <label className="block">
                <div className="label">{fieldLabel('preferred_contact', t('app.candidate_card.fields.preferred_contact'))}</div>
                <select
                  className="input max-w-md"
                  value={(extra.preferred_contact as PreferredContact) || ''}
                  disabled={rowLocked('preferred_contact')}
                  onChange={(e) => onExtraChange({ preferred_contact: e.target.value as PreferredContact })}
                >
                  {preferredContactOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </label>
            </InlineFieldRow>
          ) : null}
        </div>
        {showIdentity && (hasCyrillic(candidate.first_name) || hasCyrillic(candidate.last_name)) ? (
          <p className="mt-2 text-xs text-amber-700">{t('app.candidate_card.hint.cyrillic_translit')}</p>
        ) : null}
      </Container>
    )
  }

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

      <div className={clsx('mt-3 grid grid-cols-1 gap-4', rowEdit ? '' : 'lg:grid-cols-2')}>
        <div className="space-y-4">
          {(!candidateProfile || fieldVisible('first_name')) && (
            rowEdit ? (
              <InlineFieldRow
                label={fieldLabel('first_name', t('app.candidate_card.fields.first_name'))}
                value={candidate.first_name || '—'}
                editing={openField === 'first_name'}
                canEdit={canEdit}
                onEdit={() => beginRow('first_name')}
                onDone={() => setOpenField(null)}
              >
                <Input
                  label={fieldLabel('first_name', t('app.candidate_card.fields.first_name'))}
                  value={candidate.first_name}
                  onChange={(e) => onModelChange((m) => ({ ...m, first_name: e.target.value }))}
                  readOnly={rowLocked('first_name')}
                  required={fieldRequired('first_name')}
                />
              </InlineFieldRow>
            ) : (
            <Input
              label={fieldLabel('first_name', t('app.candidate_card.fields.first_name'))}
              value={candidate.first_name}
              onChange={(e) => onModelChange((m) => ({ ...m, first_name: e.target.value }))}
              readOnly={candidateDataReadOnly}
              required={fieldRequired('first_name')}
            />
            )
          )}
          {(!candidateProfile || fieldVisible('last_name')) && (
            rowEdit ? (
              <InlineFieldRow
                label={fieldLabel('last_name', t('app.candidate_card.fields.last_name'))}
                value={candidate.last_name || '—'}
                editing={openField === 'last_name'}
                canEdit={canEdit}
                onEdit={() => beginRow('last_name')}
                onDone={() => setOpenField(null)}
              >
                <Input
                  label={fieldLabel('last_name', t('app.candidate_card.fields.last_name'))}
                  value={candidate.last_name}
                  onChange={(e) => onModelChange((m) => ({ ...m, last_name: e.target.value }))}
                  readOnly={rowLocked('last_name')}
                  required={fieldRequired('last_name')}
                />
              </InlineFieldRow>
            ) : (
            <Input
              label={fieldLabel('last_name', t('app.candidate_card.fields.last_name'))}
              value={candidate.last_name}
              onChange={(e) => onModelChange((m) => ({ ...m, last_name: e.target.value }))}
              readOnly={candidateDataReadOnly}
              required={fieldRequired('last_name')}
            />
            )
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
            rowEdit ? (
              <InlineFieldRow
                label={fieldLabel('email', t('app.candidate_card.fields.email'))}
                value={candidate.email || '—'}
                editing={openField === 'email'}
                canEdit={canEdit}
                onEdit={() => beginRow('email')}
                onDone={() => setOpenField(null)}
              >
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
                  readOnly={rowLocked('email')}
                  required={fieldRequired('email')}
                />
                {emailError && emailTouched && (
                  <p className="mt-1 text-xs text-red-600">{translateValidationError(emailError)}</p>
                )}
              </InlineFieldRow>
            ) : (
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
            )
          )}

          {(!candidateProfile || fieldVisible('phone')) && (
            rowEdit && openField !== 'phone' ? (
              <InlineFieldRow
                label={fieldLabel('phone', t('app.candidate_card.fields.phone'))}
                value={candidate.phone || '—'}
                editing={false}
                canEdit={canEdit}
                onEdit={() => beginRow('phone')}
                onDone={() => setOpenField(null)}
              >
                {null}
              </InlineFieldRow>
            ) : (
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
                    disabled={rowLocked('phone')}
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
                    readOnly={rowLocked('phone')}
                  />
                  {phoneError && phoneTouched && (
                    <p className="mt-1 text-xs text-red-600">{translateValidationError(phoneError)}</p>
                  )}
                </div>
              </div>
          </div>
            )
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
