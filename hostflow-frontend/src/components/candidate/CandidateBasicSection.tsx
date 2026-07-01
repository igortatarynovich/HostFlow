import { memo, useRef, useState, useEffect } from 'react'
import clsx from 'clsx'
import { IconUserCircle } from '@tabler/icons-react'
import type { Candidate, CandidateExtra } from '../../api/types'
import type { RefObject } from 'react'
import type { CandidateProfile } from '../../api/candidate_profiles'
import type { EffectiveCardLayout } from '../../api/fieldRegistry'
import StageTag from '../StageTag'
import { useI18n } from '../../i18n'
import { Input, SearchableSelect } from './shared/FormComponents'
import { translateReasonLabel, translateStageLabel } from '../../utils/stageLabels'
import { formatDateTime } from '../../utils/dateFormat'
import { validateEmail, validatePhone } from '../../utils/validation'
import { isFieldVisible, isFieldRequired, getFieldLabel } from '../../utils/profileUtils'
import { hasCyrillic } from '../../utils/transliterate'
import { isRecruitmentTerminalStageCode } from '../../constants/recruitmentStageBoundary'

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
}: CandidateBasicSectionProps) {
  const { t } = useI18n()
  const [emailError, setEmailError] = useState<string | null>(null)
  const [phoneError, setPhoneError] = useState<string | null>(null)
  const [emailTouched, setEmailTouched] = useState(false)
  const [phoneTouched, setPhoneTouched] = useState(false)
  const [newTagInput, setNewTagInput] = useState('')

  const stageLabelIntl = stageLabelIntlProp ?? ((code: string) => {
    const fallback = meta?.labels?.[code] || code
    return translateStageLabel(t, code, fallback)
  })
  const fieldVisible = (fieldKey: string) => isFieldVisible(candidateProfile, fieldKey, effectiveLayout)
  const fieldRequired = (fieldKey: string) => isFieldRequired(candidateProfile, fieldKey, effectiveLayout)
  const fieldLabel = (fieldKey: string, defaultLabel: string) =>
    getFieldLabel(candidateProfile, fieldKey, defaultLabel, effectiveLayout)
  const stageSelectEnabled = canEdit || canCloseRecruitment
  const canPickStage = (code: string) =>
    canEdit || (canCloseRecruitment && isRecruitmentTerminalStageCode(code))
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
        embedded ? 'rounded-2xl border border-slate-200 bg-white p-4' : 'group app-surface p-4 transition-shadow hover:shadow-xl',
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <IconUserCircle size={18} className="text-slate-600" />
          <div className="text-sm font-semibold text-slate-900">{t('app.candidate_card.sections.basic.title')}</div>
        </div>
      </div>

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

          <div>
            <div className="label">{t('app.candidate_card.fields.stage')}</div>
            <div className="flex items-center gap-2">
              <select
                className="input"
                value={candidate.stage || ''}
                disabled={!stageSelectEnabled}
                onChange={(e) => {
                  if (!stageSelectEnabled) return
                  const nextStage = e.target.value
                  if (!canPickStage(nextStage)) return
                  const options = meta?.reason_choices?.[nextStage] ?? []
                  const sanitized = Array.isArray(candidate.status_reason)
                    ? candidate.status_reason.filter((code) => options.some((opt: { code: string }) => opt.code === code))
                    : []
                  const needsReason = options.length > 0
                  onModelChange((m) => ({
                    ...m,
                    stage: nextStage,
                    status_reason: options.length ? sanitized : [],
                  }))
                  if (!needsReason || sanitized.length > 0) {
                    onStageChangePersist?.(nextStage, options.length ? sanitized : [])
                  }
                }}
              >
                {stageOptions.map((code) => (
                  <option key={code} value={code} disabled={!canPickStage(code)}>
                    {stageLabelIntl(code)}
                  </option>
                ))}
              </select>
              <StageTag code={candidate.stage || 'new'} />
            </div>
            {/* Предупреждение, если текущий этап не соответствует профилю */}
            {candidateProfile && stageOptions.length > 0 && candidate.stage && (() => {
              const validationStageCodes = new Set(
                Array.isArray(profileStageCodes) && profileStageCodes.length > 0 ? profileStageCodes : stageOptions
              )
              const currentStageInProfile = validationStageCodes.has(candidate.stage)
              if (!currentStageInProfile) {
                return (
                  <div className="mt-2 rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-700">
                    {t('app.candidate_card.validation.stage_not_in_profile', {
                      values: {
                        stage: stageLabelIntl(candidate.stage),
                        profile: candidateProfile.name,
                      },
                    })}
                  </div>
                )
              }
              return null
            })()}
          </div>
          {(meta?.reason_choices?.[candidate.stage || '']?.length ?? 0) > 0 && (
            <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
              <div className="label mb-1">{t('app.candidate_card.fields.status_reasons')}</div>
              <div className="space-y-1 text-sm">
                {(meta?.reason_choices?.[candidate.stage || ''] ?? []).map((option) => {
                  const checked = Array.isArray(candidate.status_reason) && candidate.status_reason.includes(option.code)
                  const label = translateReasonLabel(t, option.code, option.label || option.code)
                  return (
                    <label key={option.code} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={!canEdit}
                        onChange={(e) => {
                          if (!canEdit) return
                          const nextChecked = e.target.checked
                          const current = Array.isArray(candidate.status_reason) ? candidate.status_reason : []
                          const updated = nextChecked
                            ? Array.from(new Set([...current, option.code]))
                            : current.filter((code) => code !== option.code)
                          onModelChange((m) => ({ ...m, status_reason: updated }))
                          if (updated.length > 0) {
                            onStageChangePersist?.(candidate.stage || '', updated)
                          }
                        }}
                      />
                      <span>{label}</span>
                    </label>
                  )
                })}
              </div>
              {(!Array.isArray(candidate.status_reason) || candidate.status_reason.length === 0) && (
                <div className="text-xs text-red-600">{t('app.candidate_card.messages.stage_reason_required')}</div>
              )}
            </div>
          )}

          <label className="block">
            <div className="label">{t('app.candidate_card.fields.manager')}</div>
            <SearchableSelect
              options={managers}
              value={candidate.manager || ''}
              onChange={(v) => onModelChange((m) => ({ ...m, manager: v || null, manager_id: v || null }))}
              placeholder={t('app.candidate_card.fields.manager_not_assigned', {
                defaultValue: t('app.candidates.table.manager_not_assigned', { defaultValue: 'Not assigned' }),
              })}
              searchPlaceholder={selectTexts.search}
              noResultsLabel={selectTexts.noResults}
            />
          </label>

          <div>
            <div className="label">{t('app.candidate_card.fields.tags')}</div>
            <div className="space-y-2">
              <div className="flex flex-wrap gap-2">
                {(Array.isArray(candidate.tags) ? candidate.tags : []).map((tag, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center gap-1 rounded-md bg-blue-100 px-2 py-1 text-sm text-blue-800"
                  >
                    <span>{tag}</span>
                    <button
                      type="button"
                      onClick={() => {
                        onModelChange((m) => {
                          const current = Array.isArray(m.tags) ? m.tags : []
                          return { ...m, tags: current.filter((t) => t !== tag) }
                        })
                      }}
                      className="ml-1 text-blue-600 hover:text-blue-800"
                      aria-label={t('app.candidate_card.actions.remove_tag', { tag })}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  placeholder={t('app.candidate_card.placeholders.tag')}
                  value={newTagInput}
                  onChange={(e) => setNewTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      const trimmed = newTagInput.trim()
                      if (trimmed) {
                        onModelChange((m) => {
                          const current = Array.isArray(m.tags) ? m.tags : []
                          if (!current.includes(trimmed)) {
                            return { ...m, tags: [...current, trimmed].sort() }
                          }
                          return m
                        })
                        setNewTagInput('')
                      }
                    }
                  }}
                  containerClassName="flex-1 min-w-0"
                  className="w-full"
                />
                <button
                  type="button"
                  onClick={() => {
                    const trimmed = newTagInput.trim()
                    if (trimmed) {
                      onModelChange((m) => {
                        const current = Array.isArray(m.tags) ? m.tags : []
                        if (!current.includes(trimmed)) {
                          return { ...m, tags: [...current, trimmed].sort() }
                        }
                        return m
                      })
                      setNewTagInput('')
                    }
                  }}
                  className="btn-secondary btn-sm"
                  disabled={!newTagInput.trim()}
                >
                  {t('app.candidate_card.actions.add_tag')}
                </button>
              </div>
            </div>
          </div>

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
