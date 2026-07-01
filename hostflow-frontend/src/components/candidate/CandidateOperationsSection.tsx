import { memo } from 'react'
import type { CandidateExtra } from '../../api/types'
import { useI18n } from '../../i18n'

const OPS_MODE_VALUES = ['in_work', 'later', 'no_reply_needed', 'escalated'] as const
type OpsMode = (typeof OPS_MODE_VALUES)[number]

function isOpsMode(value: string): value is OpsMode {
  return OPS_MODE_VALUES.includes(value as OpsMode)
}

interface CandidateOperationsSectionProps {
  extra: CandidateExtra
  candidateDataReadOnly?: boolean
  onExtraChange: (patch: Partial<CandidateExtra>) => void
}

function CandidateOperationsSection({
  extra,
  candidateDataReadOnly = false,
  onExtraChange,
}: CandidateOperationsSectionProps) {
  const { t } = useI18n()
  const currentOpsModeRaw = String(extra?.candidate_ops?.mode || '').trim().toLowerCase()
  const currentOpsMode = isOpsMode(currentOpsModeRaw) ? currentOpsModeRaw : ''

  return (
    <section className="app-surface p-6">
      <div className="mb-4 flex items-center gap-3">
        <span className="text-2xl">🎯</span>
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            {t('app.candidate_card.sections.operations.title', { defaultValue: 'Operations' })}
          </h2>
          <p className="text-sm text-slate-500">
            {t('app.candidate_card.sections.operations.description', {
              defaultValue: 'Operational manager mode, independent from candidate stage.',
            })}
          </p>
        </div>
      </div>
      <label className="block">
        <div className="label">{t('app.candidate_card.fields.ops_mode')}</div>
        <select
          className="input"
          value={currentOpsMode}
          disabled={candidateDataReadOnly}
          onChange={(e) => {
            const value = String(e.target.value || '').trim().toLowerCase()
            onExtraChange({
              candidate_ops: {
                ...(extra?.candidate_ops || {}),
                mode: isOpsMode(value) ? value : null,
                updated_at: new Date().toISOString(),
              },
            })
          }}
        >
          <option value="">{t('app.candidate_card.ops_mode.none')}</option>
          <option value="in_work">{t('app.candidate_card.ops_mode.in_work')}</option>
          <option value="later">{t('app.candidate_card.ops_mode.later')}</option>
          <option value="no_reply_needed">{t('app.candidate_card.ops_mode.no_reply_needed')}</option>
          <option value="escalated">{t('app.candidate_card.ops_mode.escalated')}</option>
        </select>
        <p className="mt-1 text-xs text-slate-500">{t('app.candidate_card.ops_mode.hint')}</p>
      </label>
    </section>
  )
}

export default memo(CandidateOperationsSection)
