import { useState } from 'react'
import type { Candidate } from '../../../api/types'
import type { CandidateProfile } from '../../../api/candidate_profiles'
import StageTag from '../../StageTag'
import { useI18n } from '../../../i18n'
import { Input, SearchableSelect } from '../shared/FormComponents'
import { translateReasonLabel } from '../../../utils/stageLabels'
import { isRecruitmentTerminalStageCode } from '../../../constants/recruitmentStageBoundary'

type Option = { value: string; label: string; extra?: unknown }

export function CandidateProcessControls({
  candidate,
  stageOptions,
  profileStageCodes,
  meta,
  managers,
  selectTexts,
  stageLabelIntl,
  canEdit = true,
  canCloseRecruitment = true,
  candidateProfile,
  onModelChange,
  onStageChangePersist,
}: {
  candidate: Candidate
  stageOptions: string[]
  profileStageCodes?: string[]
  meta?: {
    reason_choices?: Record<string, { code: string; label: string }[]>
    labels?: Record<string, string>
  }
  managers: Option[]
  selectTexts: { search: string; noResults: string }
  stageLabelIntl: (code: string) => string
  canEdit?: boolean
  canCloseRecruitment?: boolean
  candidateProfile?: CandidateProfile | null
  onModelChange: (updater: (prev: Candidate) => Candidate) => void
  onStageChangePersist?: (stage: string, statusReason: string[]) => void | Promise<void>
}) {
  const { t } = useI18n()
  const [newTagInput, setNewTagInput] = useState('')
  const stageSelectEnabled = canEdit || canCloseRecruitment
  const canPickStage = (code: string) =>
    canEdit || (canCloseRecruitment && isRecruitmentTerminalStageCode(code))

  return (
    <div className="space-y-4">
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
                ? candidate.status_reason.filter((code) => options.some((opt) => opt.code === code))
                : []
              const needsReason = options.length > 0
              onModelChange((current) => ({
                ...current,
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
        {candidateProfile && stageOptions.length > 0 && candidate.stage && (() => {
          const validationStageCodes = new Set(
            Array.isArray(profileStageCodes) && profileStageCodes.length > 0 ? profileStageCodes : stageOptions,
          )
          if (validationStageCodes.has(candidate.stage)) return null
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
                      const current = Array.isArray(candidate.status_reason) ? candidate.status_reason : []
                      const updated = e.target.checked
                        ? Array.from(new Set([...current, option.code]))
                        : current.filter((code) => code !== option.code)
                      onModelChange((currentCandidate) => ({ ...currentCandidate, status_reason: updated }))
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
          onChange={(value) => onModelChange((current) => ({ ...current, manager: value || null, manager_id: value || null }))}
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
            {(Array.isArray(candidate.tags) ? candidate.tags : []).map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 rounded-md bg-blue-100 px-2 py-1 text-sm text-blue-800"
              >
                <span>{tag}</span>
                <button
                  type="button"
                  onClick={() => {
                    onModelChange((current) => {
                      const tags = Array.isArray(current.tags) ? current.tags : []
                      return { ...current, tags: tags.filter((item) => item !== tag) }
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
                if (e.key !== 'Enter') return
                e.preventDefault()
                const trimmed = newTagInput.trim()
                if (!trimmed) return
                onModelChange((current) => {
                  const tags = Array.isArray(current.tags) ? current.tags : []
                  if (tags.includes(trimmed)) return current
                  return { ...current, tags: [...tags, trimmed].sort() }
                })
                setNewTagInput('')
              }}
              containerClassName="flex-1 min-w-0"
              className="w-full"
            />
            <button
              type="button"
              onClick={() => {
                const trimmed = newTagInput.trim()
                if (!trimmed) return
                onModelChange((current) => {
                  const tags = Array.isArray(current.tags) ? current.tags : []
                  if (tags.includes(trimmed)) return current
                  return { ...current, tags: [...tags, trimmed].sort() }
                })
                setNewTagInput('')
              }}
              className="btn-secondary btn-sm"
              disabled={!newTagInput.trim()}
            >
              {t('app.candidate_card.actions.add_tag')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
