import { describe, expect, it, vi } from 'vitest'

import {
  findQuestionnaireFormTitleInList,
  normalizeLeadQuestionnaireFormsList,
  questionnaireFormOptionId,
  questionnaireFormOptionTitle,
  readIntakeFormDetailTitle,
  readSubmissionPolicyMode,
  readSubmissionPublishedVersion,
  readSubmissionSource,
  resolveAttributionFormContext,
  submissionEntryLabel,
  submissionPolicyModeLabel,
} from '../salesQuestionnaireAttribution'

const formId = 'c4b4ef25-6ef1-4b51-b1b7-2d5f38c8144c'

function t(key: string, options?: { defaultValue?: string }): string {
  const catalog: Record<string, string> = {
    'app.sales_questionnaire.attribution.entry.questionnaire_invite': 'Personal questionnaire invite',
    'app.sales_questionnaire.attribution.entry.public_form': 'Public form',
    'app.sales_questionnaire.attribution.policy.attach': 'Added to this inquiry',
    'app.sales_questionnaire.attribution.policy.create': 'Created a new inquiry',
    'app.sales_questionnaire.attribution.policy.match_or_create': 'Matched or created inquiry',
    'app.sales_questionnaire.attribution.policy.review': 'Sent to review queue',
    'app.sales_questionnaire.attribution.entry.questionnaire_invite.pl': 'Osobiste zaproszenie do ankiety',
    'app.sales_questionnaire.attribution.policy.attach.pl': 'Dodano do tego zapytania',
    'app.sales_questionnaire.attribution.entry.questionnaire_invite.ru': 'Персональное приглашение к анкете',
    'app.sales_questionnaire.attribution.policy.attach.ru': 'Добавлено к этой заявке',
  }
  return catalog[key] ?? options?.defaultValue ?? key
}

describe('salesQuestionnaireAttribution', () => {
  it('reads source and policy from submission snapshot', () => {
    const submission = {
      source: { entry: 'questionnaire_invite', invite_id: 'invite-123' },
      effective_submission_policy: { submission_policy: { mode: 'attach' } },
      published_version: 1,
    }
    expect(readSubmissionSource(submission)).toEqual({ entry: 'questionnaire_invite', invite_id: 'invite-123' })
    expect(readSubmissionPolicyMode(submission)).toBe('attach')
    expect(readSubmissionPublishedVersion(submission)).toBe(1)
  })

  it('normalizes questionnaire form list shapes and reads id/title fields', () => {
    expect(normalizeLeadQuestionnaireFormsList([{ id: formId, title: 'A' }])).toHaveLength(1)
    expect(normalizeLeadQuestionnaireFormsList({ items: [{ lead_form_id: formId, name: 'B' }] })).toHaveLength(1)
    expect(questionnaireFormOptionId({ lead_form_id: formId })).toBe(formId)
    expect(questionnaireFormOptionTitle({ name: 'B1 Acceptance Form' })).toBe('B1 Acceptance Form')
    expect(questionnaireFormOptionTitle({ form: { title: 'Nested title' } })).toBe('Nested title')
    expect(findQuestionnaireFormTitleInList([{ id: formId, title: 'B1 Acceptance Form' }], formId)).toBe(
      'B1 Acceptance Form',
    )
    expect(readIntakeFormDetailTitle({ form: { title: 'From detail' } })).toBe('From detail')
  })

  it('resolves form title from list, then detail, then uuid fallback', async () => {
    const listForms = vi.fn().mockResolvedValue([{ id: formId, title: 'B1 Acceptance Form' }])
    const getFormDetail = vi.fn()

    await expect(
      resolveAttributionFormContext(formId, { listForms, getFormDetail }),
    ).resolves.toEqual({
      formTitle: 'B1 Acceptance Form',
      formId,
      publicationName: null,
    })
    expect(getFormDetail).not.toHaveBeenCalled()

    listForms.mockResolvedValue([])
    getFormDetail.mockResolvedValue({
      form: { title: 'Detail title' },
      intake_source_profile: { name: 'Meta Ads' },
    })

    await expect(
      resolveAttributionFormContext(formId, { listForms, getFormDetail }),
    ).resolves.toEqual({
      formTitle: 'Detail title',
      formId,
      publicationName: 'Meta Ads',
    })

    listForms.mockRejectedValue(new Error('list failed'))
    getFormDetail.mockRejectedValue(new Error('detail failed'))

    await expect(
      resolveAttributionFormContext(formId, { listForms, getFormDetail }),
    ).resolves.toEqual({
      formTitle: formId,
      formId,
      publicationName: null,
    })
  })

  it('maps entry and policy codes to localized operator labels', () => {
    expect(submissionEntryLabel('questionnaire_invite', t)).toBe('Personal questionnaire invite')
    expect(submissionPolicyModeLabel('attach', t)).toBe('Added to this inquiry')
    expect(submissionEntryLabel('public_form', t)).toBe('Public form')
    expect(submissionPolicyModeLabel('match_or_create', t)).toBe('Matched or created inquiry')
  })

  it('supports PL and RU catalog keys for source and attach mode', () => {
    const tPl = (key: string, options?: { defaultValue?: string }) =>
      ({
        'app.sales_questionnaire.attribution.entry.questionnaire_invite': 'Osobiste zaproszenie do ankiety',
        'app.sales_questionnaire.attribution.policy.attach': 'Dodano do tego zapytania',
      })[key] ?? options?.defaultValue ?? key
    const tRu = (key: string, options?: { defaultValue?: string }) =>
      ({
        'app.sales_questionnaire.attribution.entry.questionnaire_invite': 'Персональное приглашение к анкете',
        'app.sales_questionnaire.attribution.policy.attach': 'Добавлено к этой заявке',
      })[key] ?? options?.defaultValue ?? key

    expect(submissionEntryLabel('questionnaire_invite', tPl)).toBe('Osobiste zaproszenie do ankiety')
    expect(submissionPolicyModeLabel('attach', tPl)).toBe('Dodano do tego zapytania')
    expect(submissionEntryLabel('questionnaire_invite', tRu)).toBe('Персональное приглашение к анкете')
    expect(submissionPolicyModeLabel('attach', tRu)).toBe('Добавлено к этой заявке')
  })
})
