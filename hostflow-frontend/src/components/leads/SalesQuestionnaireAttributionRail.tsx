import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { getIntakeFormDetail } from '../../api/intakeForms'
import { listLeadQuestionnaireForms } from '../../api/client'
import type { Lead } from '../../api/types'
import { useI18n, type LocaleCode } from '../../i18n'
import {
  entityProfileLabel,
  personalInviteBehaviorLabel,
  publicSubmitBehaviorLabel,
  purposeLabel,
} from '../../utils/intakeFormRoutingSummary'
import {
  readLatestSubmission,
  resolveSubmissionPresentationCode,
  resolveSubmissionEntityProfileCode,
  type LeadSubmissionV1,
} from '../../utils/salesQuestionnaireSubmission'
import {
  readSubmissionPolicyMode,
  readSubmissionPublicationId,
  readSubmissionPublishedVersion,
  readSubmissionPurpose,
  readSubmissionSource,
  shortId,
  submissionEntryLabel,
  submissionPolicyModeLabel,
} from '../../utils/salesQuestionnaireAttribution'

type AttributionContext = {
  formTitle: string
  formId: string | null
  publicationName: string | null
  settingsFormPath: string | null
}

function formatSubmittedAt(iso: string | null | undefined, locale: LocaleCode): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString(locale === 'pl' ? 'pl-PL' : locale === 'ru' ? 'ru-RU' : 'en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

async function resolveAttributionContext(submission: LeadSubmissionV1): Promise<AttributionContext> {
  const formId = text(submission.form_id) || null
  if (!formId) {
    return { formTitle: '—', formId: null, publicationName: null, settingsFormPath: null }
  }

  try {
    const forms = await listLeadQuestionnaireForms()
    const match = forms.find((row) => row.id === formId)
    if (match?.title) {
      return {
        formTitle: match.title,
        formId,
        publicationName: null,
        settingsFormPath: `/app/settings/lead-forms/${formId}`,
      }
    }
  } catch {
    // fall through
  }

  try {
    const detail = await getIntakeFormDetail(formId)
    return {
      formTitle: detail.form?.title || formId,
      formId,
      publicationName: detail.intake_source_profile?.name || null,
      settingsFormPath: `/app/settings/lead-forms/${formId}`,
    }
  } catch {
    return {
      formTitle: formId,
      formId,
      publicationName: null,
      settingsFormPath: `/app/settings/lead-forms/${formId}`,
    }
  }
}

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <li className="flex justify-between gap-3 border-b border-slate-100 pb-2 last:border-0 last:pb-0">
      <span className="text-slate-500">{label}</span>
      <span className="min-w-0 text-right font-medium text-slate-900">{value}</span>
    </li>
  )
}

export default function SalesQuestionnaireAttributionRail({ lead }: { lead: Lead }) {
  const { locale, t } = useI18n()
  const submission = readLatestSubmission(lead)
  const [context, setContext] = useState<AttributionContext | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!submission) {
      setContext(null)
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    void resolveAttributionContext(submission)
      .then((next) => {
        if (!cancelled) setContext(next)
      })
      .catch(() => {
        if (!cancelled) setContext(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [submission?.form_id, submission?.submission_id])

  if (!submission) return null

  const source = readSubmissionSource(submission)
  const entityProfileCode = resolveSubmissionEntityProfileCode(submission, lead)
  const purpose = readSubmissionPurpose(submission)
  const publishedVersion = readSubmissionPublishedVersion(submission)
  const policyMode = readSubmissionPolicyMode(submission)
  const publicationId = readSubmissionPublicationId(submission)
  const presentationCode = resolveSubmissionPresentationCode(submission)
  const entryLabel = submissionEntryLabel(source.entry)
  const policyLabel = submissionPolicyModeLabel(policyMode)
  const intakeBehavior =
    source.entry === 'questionnaire_invite'
      ? personalInviteBehaviorLabel()
      : publicSubmitBehaviorLabel({ purpose, submission_policy: { mode: policyMode } })

  return (
    <section className="space-y-3" data-testid="sales-questionnaire-attribution">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.sales_questionnaire.attribution_title', { defaultValue: 'Submission attribution' })}
        </p>
        <p className="mt-1 text-sm text-slate-600">
          {t('app.sales_questionnaire.attribution_hint', {
            defaultValue: 'Where this response came from and how it was attached.',
          })}
        </p>
      </div>
      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading')}</p>
      ) : (
        <ul className="space-y-2 text-sm text-slate-800">
          <Row
            label={t('app.sales_questionnaire.attribution.form', { defaultValue: 'Form' })}
            value={
              context?.settingsFormPath ? (
                <Link to={context.settingsFormPath} className="text-brand-700 hover:underline">
                  {context?.formTitle || '—'}
                </Link>
              ) : (
                context?.formTitle || '—'
              )
            }
          />
          <Row
            label={t('app.sales_questionnaire.attribution.version', { defaultValue: 'Published version' })}
            value={publishedVersion != null ? String(publishedVersion) : '—'}
          />
          <Row
            label={t('app.sales_questionnaire.attribution.source', { defaultValue: 'Source' })}
            value={entryLabel}
          />
          <Row
            label={t('app.sales_questionnaire.attribution.publication', { defaultValue: 'Publication' })}
            value={context?.publicationName || shortId(publicationId) || '—'}
          />
          <Row
            label={t('app.sales_questionnaire.attribution.submitted_at', { defaultValue: 'Submitted at' })}
            value={formatSubmittedAt(submission.submitted_at, locale)}
          />
          <Row
            label={t('app.sales_questionnaire.attribution.submission', { defaultValue: 'Submission' })}
            value={shortId(submission.submission_id)}
          />
          <Row
            label={t('app.sales_questionnaire.attribution.attach_mode', { defaultValue: 'Attach mode' })}
            value={policyLabel}
          />
          <Row
            label={t('app.sales_questionnaire.attribution.profile', { defaultValue: 'Entity profile' })}
            value={entityProfileLabel(entityProfileCode)}
          />
          {purpose ? (
            <Row
              label={t('app.sales_questionnaire.attribution.purpose', { defaultValue: 'Purpose' })}
              value={purposeLabel(purpose)}
            />
          ) : null}
          {presentationCode ? (
            <Row
              label={t('app.sales_questionnaire.attribution.presentation', { defaultValue: 'Presentation' })}
              value={<span className="font-mono text-xs">{presentationCode}</span>}
            />
          ) : null}
          {source.invite_id ? (
            <Row
              label={t('app.sales_questionnaire.attribution.invite', { defaultValue: 'Invite' })}
              value={<span className="font-mono text-xs">{shortId(source.invite_id)}</span>}
            />
          ) : null}
          <Row
            label={t('app.sales_questionnaire.attribution.behavior', { defaultValue: 'Routing behavior' })}
            value={intakeBehavior}
          />
        </ul>
      )}
    </section>
  )
}
